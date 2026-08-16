"""
Modèle électromagnétique ET mécanique du moteur asynchrone triphasé.
Intègre la théorie de Kloss pour le moteur, et des profils de charge 
industriels (Pompes, Ventilateurs, Convoyeurs) pour simuler un vrai 
groupe motopropulseur.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

LoadType = Literal["no_load", "pump_fan", "conveyor", "crusher"]

@dataclass
class NameplateData:
    rated_power_kw: float
    poles: int
    frequency_hz: float = 50.0
    rated_voltage_v: float | None = None
    rated_current_a: float | None = None
    rated_speed_rpm: float | None = None
    power_factor: float | None = None
    efficiency: float | None = None


DEFAULT_RATED_SLIP = 0.04
DEFAULT_BREAKDOWN_SLIP_RATIO = 5.0
DEFAULT_BREAKDOWN_TORQUE_RATIO = 2.5


class MechanicalLoad:
    """Modèle du couple résistant de la machine entraînée."""
    
    def __init__(self, load_type: LoadType, rated_torque_nm: float):
        self.load_type = load_type
        self.rated_torque_nm = rated_torque_nm
        # On suppose que la charge absorbe 90% du couple nominal du moteur à pleine vitesse
        self.nominal_load_torque = rated_torque_nm * 0.90

    def resisting_torque_at_speed(self, current_rpm: float, rated_rpm: float) -> float:
        """Calcule le couple résistant selon le type de charge."""
        if current_rpm < 0:
            current_rpm = 0
            
        speed_ratio = current_rpm / rated_rpm if rated_rpm > 0 else 0

        if self.load_type == "no_load":
            # Juste les frottements mécaniques de base (5% du couple)
            return self.rated_torque_nm * 0.05
            
        elif self.load_type == "pump_fan":
            # Couple quadratique : augmente avec le carré de la vitesse
            # Frottement statique au démarrage + courbe parabolique
            static_friction = self.rated_torque_nm * 0.10
            return static_friction + (self.nominal_load_torque * (speed_ratio ** 2))
            
        elif self.load_type == "conveyor":
            # Couple constant : ex: lever un poids, ou frottement sec d'un tapis
            return self.nominal_load_torque
            
        elif self.load_type == "crusher":
            # Broyeur : Couple quasi constant mais énorme inertie (gérée ailleurs dans la simu)
            # Demande un fort couple même à basse vitesse
            return self.nominal_load_torque * 1.1 
            
        return 0.0


class InductionMotorModel:
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
        return 120.0 * self.nameplate.frequency_hz / self.nameplate.poles

    def _compute_rated_slip(self) -> float:
        if self.nameplate.rated_speed_rpm is not None:
            return (self.synchronous_speed_rpm - self.nameplate.rated_speed_rpm) / self.synchronous_speed_rpm
        return DEFAULT_RATED_SLIP

    def _compute_rated_torque(self) -> float:
        omega_rated = self.rated_speed_rpm * 2 * math.pi / 60.0
        if omega_rated <= 0:
            raise ValueError("Vitesse nominale calculée non positive")
        return (self.nameplate.rated_power_kw * 1000.0) / omega_rated

    def torque_at_slip(self, slip: float) -> float:
        """Formule de Kloss"""
        if slip == 0:
            return 0.0
        if not (-0.001 <= slip <= 1.5):
            raise ValueError(f"slip={slip} hors de la plage valide")

        denominator = (slip / self.breakdown_slip) + (self.breakdown_slip / slip)
        return self.breakdown_torque_nm * 2.0 / denominator

    def torque_at_speed(self, speed_rpm: float) -> float:
        slip = (self.synchronous_speed_rpm - speed_rpm) / self.synchronous_speed_rpm
        return self.torque_at_slip(slip)

    def starting_torque_nm(self) -> float:
        return self.torque_at_slip(1.0)

    def describe(self) -> dict:
        return {
            "synchronous_speed_rpm": round(self.synchronous_speed_rpm, 1),
            "rated_speed_rpm": round(self.rated_speed_rpm, 1),
            "rated_slip": round(self.rated_slip, 4),
            "rated_slip_source": "mesurée" if self.nameplate.rated_speed_rpm else "estimée",
            "rated_torque_nm": round(self.rated_torque_nm, 3),
            "breakdown_torque_nm": round(self.breakdown_torque_nm, 3),
            "starting_torque_nm": round(self.starting_torque_nm(), 3),
        }