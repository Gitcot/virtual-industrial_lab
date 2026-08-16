"""
Catalogue des dimensions industrielles IEC 60072 pour Jumeau Numérique.
Génère les dimensions exactes pour contraindre le modèle 3D (Blender).
"""

from __future__ import annotations
from dataclasses import dataclass

@dataclass
class FrameDimensions:
    frame_designation: str
    shaft_height_mm: float
    body_diameter_mm: float
    body_length_mm: float
    shaft_diameter_mm: float
    shaft_length_mm: float


# Table IEC 60072 affinée pour un rendu 3D ultra-réaliste (basée sur moteurs 4 pôles en fonte)
_IEC_FRAME_TABLE: list[tuple[float, FrameDimensions]] = [
    (0.37, FrameDimensions("71", 71, 140, 220, 14, 30)),
    (0.75, FrameDimensions("80", 80, 155, 240, 19, 40)),
    (1.5, FrameDimensions("90S", 90, 175, 270, 24, 50)),
    (2.2, FrameDimensions("100L", 100, 195, 310, 28, 60)),
    (4.0, FrameDimensions("112M", 112, 220, 330, 28, 60)),
    (7.5, FrameDimensions("132S", 132, 260, 390, 38, 80)),
    (11.0, FrameDimensions("160M", 160, 315, 490, 42, 110)),
    (15.0, FrameDimensions("160L", 160, 315, 530, 42, 110)),
    (22.0, FrameDimensions("180M", 180, 350, 590, 48, 110)),
    (30.0, FrameDimensions("200L", 200, 395, 660, 55, 110)),
    (45.0, FrameDimensions("225M", 225, 445, 710, 60, 140)),
    (55.0, FrameDimensions("250M", 250, 490, 780, 65, 140)),
    (75.0, FrameDimensions("280S", 280, 550, 850, 75, 140)),
    (110.0, FrameDimensions("315S", 315, 620, 990, 80, 170)),
    (160.0, FrameDimensions("315L", 315, 620, 1100, 80, 170)),
    (200.0, FrameDimensions("355M", 355, 700, 1250, 100, 210)),
    (250.0, FrameDimensions("355L", 355, 700, 1350, 100, 210)),
]


def frame_for_power(rated_power_kw: float, poles: int = 4) -> FrameDimensions:
    """
    Retourne les dimensions IEC de carcasse.
    Intègre l'expertise métier : un moteur lent (beaucoup de pôles) a besoin 
    de plus de couple, donc d'une carcasse plus grosse pour la même puissance.
    """
    if rated_power_kw <= 0:
        raise ValueError("rated_power_kw doit être positif")

    # Puissance équivalente 4 pôles pour la recherche dans la table
    # Règle industrielle : + de pôles = carcasse supérieure
    equivalent_power = rated_power_kw
    if poles >= 6:
        equivalent_power = rated_power_kw * 1.5
    elif poles == 2:
        equivalent_power = rated_power_kw * 0.85

    for max_power, dims in _IEC_FRAME_TABLE:
        if equivalent_power <= max_power:
            return dims

    # Si le moteur est un monstre hors norme (> 250 kW)
    largest_power, largest_dims = _IEC_FRAME_TABLE[-1]
    scale = (equivalent_power / largest_power) ** (1 / 3)
    return FrameDimensions(
        frame_designation=f">355 (Extrapolé)",
        shaft_height_mm=largest_dims.shaft_height_mm * scale,
        body_diameter_mm=largest_dims.body_diameter_mm * scale,
        body_length_mm=largest_dims.body_length_mm * scale,
        shaft_diameter_mm=largest_dims.shaft_diameter_mm * scale,
        shaft_length_mm=largest_dims.shaft_length_mm * scale,
    )