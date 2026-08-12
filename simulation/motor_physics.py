"""
Modèle électromagnétique du moteur asynchrone triphasé, basé sur la théorie
classique du circuit équivalent et la formule de Kloss pour la courbe
couple-vitesse.

⚠️ STATUT ÉPISTÉMIQUE (à lire avant d'utiliser ce module) :
Ce module implémente une THÉORIE SCIENTIFIQUE ÉTABLIE (équations du moteur
asynchrone, enseignées dans tout cursus de génie électrique), pas les
courbes d'essai propriétaires d'un constructeur précis. Deux moteurs de
même puissance nominale de deux constructeurs différents auront des
courbes couple-vitesse légèrement différentes selon leur conception interne
(matériaux, géométrie du bobinage, tolérances de fabrication). Ce modèle
donne un comportement PHYSIQUEMENT COHÉRENT et CALIBRABLE sur les
grandeurs nominales d'une plaque signalétique réelle, pas une reproduction
pixel-perfect d'un modèle commercial. C'est explicitement ce que demande le
master prompt : "ne jamais présenter une simulation comme une
représentation physique exacte sans validation expérimentale".

Théorie utilisée (référence : tout manuel de machines électriques,
ex. Fitzgerald "Electric Machinery") :

1. Vitesse de synchronisme : Ns = 120*f / p  (tr/min)
   f = fréquence réseau (Hz), p = nombre de pôles

2. Glissement : s = (Ns - N) / Ns
   N = vitesse réelle du rotor (tr/min)

3. Formule de Kloss (approximation classique du couple en fonction du
   glissement, valable autour du point de fonctionnement nominal) :
   T(s) / T_max = 2 / (s/s_max + s_max/s)
   où T_max = couple maximal (de décrochage), s_max = glissement au
   couple maximal

4. Le couple nominal et le glissement nominal sont dérivés des valeurs de
   plaque signalétique (puissance, vitesse nominale si connue, sinon
   estimée depuis le nombre de pôles et un glissement nominal typique).
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class NameplateData:
    """
    Données directement lisibles sur une plaque signalétique réelle.
    Tous les champs sauf rated_power_kw et poles sont optionnels : le
    modèle applique des valeurs typiques documentées quand elles manquent
    (voir DEFAULT_* ci-dessous), mais le résultat est alors marqué comme
    une ESTIMATION, pas une donnée mesurée (cf. principe de traçabilité du
    master prompt : DONNÉE FOURNIE / ESTIMATION / HYPOTHÈSE).
    """

    rated_power_kw: float
    poles: int  # nombre de pôles (2, 4, 6, 8...)
    frequency_hz: float = 50.0
    rated_voltage_v: float | None = None
    rated_current_a: float | None = None
    rated_speed_rpm: float | None = None  # si connue (plaque), sinon estimée
    power_factor: float | None = None  # cos(phi) nominal
    efficiency: float | None = None  # rendement nominal (0-1)


# Valeurs typiques documentées (ordres de grandeur usuels pour un moteur
# asynchrone triphasé standard basse tension, PAS une donnée constructeur) :
DEFAULT_RATED_SLIP = 0.04           # 4% : typique pour un petit/moyen moteur standard
DEFAULT_BREAKDOWN_SLIP_RATIO = 5.0  # s_max ≈ 5x le glissement nominal (ordre de grandeur usuel)
DEFAULT_BREAKDOWN_TORQUE_RATIO = 2.5  # T_max ≈ 2.0-3.0x le couple nominal selon la classe de conception (NEMA A/B/C ou IEC N/H) ; 2.5 pris comme valeur médiane


class InductionMotorModel:
    """
    Modèle couple-vitesse d'un moteur asynchrone, calibré sur une plaque
    signalétique réelle (NameplateData). Fournit le couple disponible pour
    n'importe quel glissement/vitesse, et peut être branché sur le moteur
    de simulation (simulation/motor_engine.py) pour remplacer le modèle
    "courant constant en régime" actuel par un modèle électromécanique.
    """

    def __init__(self, nameplate: NameplateData):
        if nameplate.rated_power_kw <= 0:
            raise ValueError("rated_power_kw doit être positif")
        if nameplate.poles <= 0 or nameplate.poles % 2 != 0:
            raise ValueError("poles doit être un entier pair positif (2, 4, 6, 8...)")

        self.nameplate = nameplate
        self.synchronous_speed_rpm = self._compute_synchronous_speed()
        self.rated_slip = self._compute_rated_slip()
        self.rated_speed_rpm = self.synchronous_speed_rpm * (1 - self.rated_slip)
        self.rated_torque_nm = self._compute_rated_torque()
        self.breakdown_slip = self.rated_slip * DEFAULT_BREAKDOWN_SLIP_RATIO
        self.breakdown_torque_nm = self.rated_torque_nm * DEFAULT_BREAKDOWN_TORQUE_RATIO

    def _compute_synchronous_speed(self) -> float:
        """Ns = 120*f/p — théorie exacte, aucune approximation ici."""
        return 120.0 * self.nameplate.frequency_hz / self.nameplate.poles

    def _compute_rated_slip(self) -> float:
        """
        Si la vitesse nominale est connue (lue sur la plaque), le
        glissement nominal en est déduit EXACTEMENT. Sinon, valeur typique
        appliquée (ESTIMATION, pas une mesure).
        """
        if self.nameplate.rated_speed_rpm is not None:
            return (self.synchronous_speed_rpm - self.nameplate.rated_speed_rpm) / self.synchronous_speed_rpm
        return DEFAULT_RATED_SLIP

    def _compute_rated_torque(self) -> float:
        """T = P / omega, avec omega en rad/s. Théorie exacte (P mécanique / vitesse angulaire)."""
        omega_rated = self.rated_speed_rpm * 2 * math.pi / 60.0
        if omega_rated <= 0:
            raise ValueError("Vitesse nominale calculée non positive — vérifier les paramètres")
        return (self.nameplate.rated_power_kw * 1000.0) / omega_rated

    def torque_at_slip(self, slip: float) -> float:
        """
        Formule de Kloss : T(s) = T_max * 2 / (s/s_max + s_max/s)

        Valable pour s > 0 (moteur en train de tourner ou à l'arrêt,
        s=1). Retourne 0 si s == 0 (vitesse de synchronisme, aucun couple
        - cohérent avec la théorie : un moteur asynchrone ne peut
        physiquement pas tourner exactement à la vitesse de synchronisme).
        """
        if slip == 0:
            return 0.0
        if not (-0.001 <= slip <= 1.5):
            # au-delà de s=1 (rotor bloqué) le modèle de Kloss perd sa
            # validité physique habituelle ; on borne par sécurité plutôt
            # que d'extrapoler silencieusement une valeur non fiable
            raise ValueError(f"slip={slip} hors de la plage valide du modèle (~0 à 1.5)")

        denominator = (slip / self.breakdown_slip) + (self.breakdown_slip / slip)
        return self.breakdown_torque_nm * 2.0 / denominator

    def torque_at_speed(self, speed_rpm: float) -> float:
        """Couple disponible à une vitesse de rotor donnée (tr/min)."""
        slip = (self.synchronous_speed_rpm - speed_rpm) / self.synchronous_speed_rpm
        return self.torque_at_slip(slip)

    def starting_torque_nm(self) -> float:
        """Couple au démarrage (rotor bloqué, s=1)."""
        return self.torque_at_slip(1.0)

    def starting_torque_ratio(self) -> float:
        """Rapport couple de démarrage / couple nominal (grandeur pédagogique classique)."""
        return self.starting_torque_nm() / self.rated_torque_nm

    def describe(self) -> dict:
        """Résumé des grandeurs calculées, avec traçabilité de leur origine."""
        return {
            "synchronous_speed_rpm": round(self.synchronous_speed_rpm, 1),
            "rated_speed_rpm": round(self.rated_speed_rpm, 1),
            "rated_slip": round(self.rated_slip, 4),
            "rated_slip_source": "mesurée (vitesse plaque)" if self.nameplate.rated_speed_rpm else "estimée (valeur typique)",
            "rated_torque_nm": round(self.rated_torque_nm, 3),
            "breakdown_torque_nm": round(self.breakdown_torque_nm, 3),
            "breakdown_torque_ratio": DEFAULT_BREAKDOWN_TORQUE_RATIO,
            "starting_torque_nm": round(self.starting_torque_nm(), 3),
            "starting_torque_ratio": round(self.starting_torque_ratio(), 3),
        }
