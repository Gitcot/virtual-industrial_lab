"""
Moteur de simulation d'un moteur électrique asynchrone triphasé.

Ce module est volontairement indépendant de FastAPI/DB (principe
d'architecture : le SimulationEngine doit pouvoir tourner seul, être testé
seul, avant d'être branché à l'API).

Modèle physique simplifié (Phase 4) :
- Démarrage direct : appel de courant ~5-8x In pendant le régime transitoire
  (quelques centaines de ms simulées), puis retour au courant nominal.
- Démarrage étoile-triangle : réduit l'appel de courant à ~1/3 par rapport
  au direct pendant la phase étoile, avant bascule triangle.
- Modèle thermique : accumulation type "premier ordre" - la température
  monte vers une asymptote liée au carré du courant (pertes Joule ~ I²R),
  et redescend vers l'ambiante à l'arrêt. Le déclenchement thermique
  intervient si la température simulée dépasse un seuil.

⚠️ Hypothèse (à valider expérimentalement, cf. master prompt §"ne jamais
présenter une simulation comme une représentation physique exacte") :
les constantes de temps thermiques et les ratios de courant utilisés ici
sont des ordres de grandeur pédagogiques typiques, PAS des valeurs
constructeur mesurées. À calibrer en Phase 12-13 (Digital Twin) avec de
vraies données d'essai.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class MotorState(str, enum.Enum):
    STOPPED = "stopped"
    STARTING_DIRECT = "starting_direct"
    STARTING_STAR = "starting_star"          # phase étoile du démarrage Y/D
    STARTING_DELTA = "starting_delta"        # bascule triangle
    RUNNING = "running"
    FAULT_THERMAL = "fault_thermal"          # déclenchement thermique
    FAULT_ELECTRICAL = "fault_electrical"    # défaut électrique (ex: phase manquante)
    TRIPPED = "tripped"                      # arrêté sur défaut, attend réarmement


class StartMode(str, enum.Enum):
    DIRECT = "direct"
    STAR_DELTA = "star_delta"


class FaultType(str, enum.Enum):
    THERMAL_OVERLOAD = "thermal_overload"
    PHASE_LOSS = "phase_loss"


class InvalidTransitionError(Exception):
    """Levée quand une action est demandée dans un état qui ne l'autorise pas."""


@dataclass
class MotorParameters:
    """Plaque signalétique simplifiée (Phase 4). Étendu en Digital Twin plus tard."""
    rated_voltage_v: float = 400.0
    rated_current_a: float = 3.2
    rated_power_kw: float = 1.5
    starting_current_ratio: float = 6.5       # Id/In typique démarrage direct
    star_current_ratio_factor: float = 1 / 3  # réduction en étoile vs direct
    thermal_time_constant_s: float = 300.0    # constante de temps thermique simplifiée (~5 min, ordre de grandeur réaliste pour un petit moteur - à calibrer en Phase 12-13)
    thermal_trip_ratio: float = 1.35          # trip si T° simulée > 1.35x le régime nominal
    ambient_temp_c: float = 25.0


@dataclass
class MotorSimulator:
    """
    Machine à états d'un moteur asynchrone. Le temps est avancé explicitement
    via tick(dt_seconds) — pas de thread/timer réel, pour rester testable de
    façon déterministe.
    """

    params: MotorParameters = field(default_factory=MotorParameters)
    state: MotorState = MotorState.STOPPED
    elapsed_in_state_s: float = 0.0
    simulated_temp_c: float = field(init=False)
    current_a: float = 0.0
    voltage_v: float = 0.0
    fault_active: FaultType | None = None

    # Durées pédagogiques du régime transitoire (secondes simulées)
    DIRECT_STARTUP_DURATION_S: float = 3.0
    STAR_PHASE_DURATION_S: float = 4.0

    def __post_init__(self) -> None:
        self.simulated_temp_c = self.params.ambient_temp_c

    # ---------- Actions ----------

    def start(self, mode: StartMode) -> None:
        if self.state not in (MotorState.STOPPED,):
            raise InvalidTransitionError(
                f"Impossible de démarrer depuis l'état '{self.state.value}'. "
                "Le moteur doit être à l'arrêt (STOPPED)."
            )
        self.elapsed_in_state_s = 0.0
        if mode == StartMode.DIRECT:
            self.state = MotorState.STARTING_DIRECT
        else:
            self.state = MotorState.STARTING_STAR

    def stop(self) -> None:
        if self.state in (MotorState.FAULT_THERMAL, MotorState.FAULT_ELECTRICAL, MotorState.TRIPPED):
            raise InvalidTransitionError(
                f"Impossible d'arrêter normalement depuis '{self.state.value}': "
                "un réarmement (reset) est requis après un défaut."
            )
        self.state = MotorState.STOPPED
        self.elapsed_in_state_s = 0.0
        self.current_a = 0.0
        self.voltage_v = 0.0

    def inject_fault(self, fault: FaultType) -> None:
        """Provoque un défaut pédagogique (Phase 4: TP diagnostic)."""
        if self.state in (MotorState.STOPPED, MotorState.TRIPPED):
            raise InvalidTransitionError(
                f"Impossible d'injecter un défaut depuis l'état '{self.state.value}'."
            )
        self.fault_active = fault
        if fault == FaultType.THERMAL_OVERLOAD:
            self.state = MotorState.FAULT_THERMAL
        else:
            self.state = MotorState.FAULT_ELECTRICAL
        self.current_a = 0.0
        self.voltage_v = 0.0

    def reset(self) -> None:
        """
        Réarmement après défaut. N'est autorisé que si la température
        simulée est redescendue sous le seuil nominal (règle pédagogique :
        on ne réarme pas un moteur encore chaud, comme en réalité).
        """
        if self.state not in (MotorState.FAULT_THERMAL, MotorState.FAULT_ELECTRICAL):
            raise InvalidTransitionError(
                f"Rien à réarmer depuis l'état '{self.state.value}'."
            )
        if self.fault_active == FaultType.THERMAL_OVERLOAD and self._is_still_hot():
            raise InvalidTransitionError(
                "Réarmement refusé : température simulée encore trop élevée "
                f"({self.simulated_temp_c:.1f}°C). Attendez le refroidissement."
            )
        self.state = MotorState.TRIPPED
        self.fault_active = None

    def acknowledge_and_stop(self) -> None:
        """Depuis TRIPPED (réarmé), remet proprement à STOPPED."""
        if self.state != MotorState.TRIPPED:
            raise InvalidTransitionError(
                f"acknowledge_and_stop() nécessite l'état TRIPPED, actuel: '{self.state.value}'."
            )
        self.state = MotorState.STOPPED
        self.elapsed_in_state_s = 0.0

    # ---------- Simulation temporelle ----------

    def tick(self, dt_seconds: float) -> None:
        """
        Avance la simulation de dt_seconds. Met à jour courant, tension,
        thermique.

        Ordre important : on détermine d'abord si une transition d'état est
        due (fin de démarrage direct, bascule étoile→triangle, etc.), PUIS
        seulement on calcule courant/tension pour l'état réellement actif à
        la fin du pas. Sinon, une mesure prise juste après une transition
        refléterait encore l'ancien état ("valeur périmée").

        Limite connue (documentée, pas cachée) : pour un dt très grand qui
        couvre à la fois la fin d'un régime et le début du suivant, ce
        modèle attribue tout le pas de temps au nouvel état - donc le calcul
        thermique sous-estime légèrement l'échauffement réel du sous-segment
        encore en ancien régime. Pour un usage réaliste, appeler tick() avec
        des pas courts (0.1 à 1s), comme le ferait un client UI qui rafraîchit
        les instruments virtuels régulièrement.
        """
        if dt_seconds <= 0:
            raise ValueError("dt_seconds doit être positif")

        self.elapsed_in_state_s += dt_seconds
        self._process_state_transition()
        self._update_current_and_voltage()
        self._update_thermal(dt_seconds)
        self._check_thermal_trip()

    def _process_state_transition(self) -> None:
        if self.state == MotorState.STARTING_DIRECT:
            if self.elapsed_in_state_s >= self.DIRECT_STARTUP_DURATION_S:
                self.state = MotorState.RUNNING
                self.elapsed_in_state_s = 0.0
        elif self.state == MotorState.STARTING_STAR:
            if self.elapsed_in_state_s >= self.STAR_PHASE_DURATION_S:
                self.state = MotorState.STARTING_DELTA
                self.elapsed_in_state_s = 0.0
        elif self.state == MotorState.STARTING_DELTA:
            if self.elapsed_in_state_s >= self.DIRECT_STARTUP_DURATION_S:
                self.state = MotorState.RUNNING
                self.elapsed_in_state_s = 0.0

    def _update_current_and_voltage(self) -> None:
        if self.state in (MotorState.STARTING_DIRECT, MotorState.STARTING_DELTA):
            self.voltage_v = self.params.rated_voltage_v
            self.current_a = self.params.rated_current_a * self.params.starting_current_ratio
        elif self.state == MotorState.STARTING_STAR:
            self.voltage_v = self.params.rated_voltage_v
            self.current_a = (
                self.params.rated_current_a
                * self.params.starting_current_ratio
                * self.params.star_current_ratio_factor
            )
        elif self.state == MotorState.RUNNING:
            self.voltage_v = self.params.rated_voltage_v
            self.current_a = self.params.rated_current_a
        else:
            # STOPPED, FAULT_*, TRIPPED: pas de courant/tension
            self.current_a = 0.0
            self.voltage_v = 0.0

    def _update_thermal(self, dt_seconds: float) -> None:
        """
        Modèle thermique premier ordre : dT/dt = (T_target - T) / tau
        T_target dépend du courant au carré (pertes Joule), normalisé
        pour que le régime nominal (In) donne un T_target modéré.
        """
        current_ratio = self.current_a / self.params.rated_current_a if self.current_a else 0.0
        target_rise = 40.0 * (current_ratio ** 2)  # échauffement cible pédagogique en °C au-dessus ambiant
        target_temp = self.params.ambient_temp_c + target_rise

        tau = self.params.thermal_time_constant_s
        self.simulated_temp_c += (target_temp - self.simulated_temp_c) * (dt_seconds / tau)

    def _check_thermal_trip(self) -> None:
        if self.state in (MotorState.FAULT_THERMAL, MotorState.FAULT_ELECTRICAL, MotorState.TRIPPED, MotorState.STOPPED):
            return
        nominal_target = self.params.ambient_temp_c + 40.0  # T_target à In
        trip_threshold = self.params.ambient_temp_c + 40.0 * self.params.thermal_trip_ratio
        if self.simulated_temp_c >= trip_threshold:
            self.inject_fault(FaultType.THERMAL_OVERLOAD)

    def _is_still_hot(self) -> bool:
        nominal_target = self.params.ambient_temp_c + 40.0
        cooldown_threshold = self.params.ambient_temp_c + 40.0 * 1.05  # marge de sécurité pédagogique
        return self.simulated_temp_c > cooldown_threshold

    # ---------- Lecture (instruments virtuels) ----------

    def read_measurements(self) -> dict:
        return {
            "state": self.state.value,
            "voltage_v": round(self.voltage_v, 1),
            "current_a": round(self.current_a, 2),
            "simulated_temp_c": round(self.simulated_temp_c, 1),
            "fault_active": self.fault_active.value if self.fault_active else None,
        }
