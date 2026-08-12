"""
Corrélation puissance nominale -> taille de carcasse (frame size), basée
sur la série de carcasses normalisée IEC 60072.

⚠️ STATUT ÉPISTÉMIQUE : cette table donne des ordres de grandeur TYPIQUES
pour un moteur 4 pôles standard, tels que publiés dans la norme IEC 60072
(référentiel public). Elle ne remplace PAS les cotes exactes d'un
constructeur précis, qui peuvent varier de quelques % autour de ces
valeurs selon la conception. Si une vraie plaque signalétique ou fiche
technique constructeur donne des dimensions (hauteur d'axe, longueur), ces
valeurs réelles doivent être utilisées à la place — ce module ne sert que
de repli quand seule la puissance est connue.

Colonnes : puissance nominale MAX pour cette carcasse (kW, moteur 4 pôles),
hauteur d'axe H (mm), diamètre approximatif du corps (mm), longueur
approximative hors tout (mm). Valeurs arrondies à l'ordre de grandeur
publié par la norme, pas mesurées sur un moteur réel.
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


# Table simplifiée, ordres de grandeur IEC 60072 pour moteur 4 pôles standard.
# Source : ordres de grandeur publiés dans la norme IEC 60072-1, arrondis.
_IEC_FRAME_TABLE: list[tuple[float, FrameDimensions]] = [
    (0.37, FrameDimensions("71", 71, 120, 180, 14, 30)),
    (0.75, FrameDimensions("80", 80, 140, 210, 19, 40)),
    (1.5, FrameDimensions("90S", 90, 150, 230, 24, 50)),
    (2.2, FrameDimensions("100L", 100, 165, 260, 28, 60)),
    (4.0, FrameDimensions("112M", 112, 190, 290, 28, 60)),
    (7.5, FrameDimensions("132S", 132, 216, 330, 38, 80)),
    (11.0, FrameDimensions("160M", 160, 254, 400, 42, 110)),
    (15.0, FrameDimensions("160L", 160, 254, 430, 42, 110)),
    (22.0, FrameDimensions("180M", 180, 279, 470, 48, 110)),
    (30.0, FrameDimensions("200L", 200, 318, 530, 55, 110)),
    (45.0, FrameDimensions("225M", 225, 356, 580, 60, 140)),
    (55.0, FrameDimensions("250M", 250, 406, 620, 65, 140)),
    (75.0, FrameDimensions("280S", 280, 457, 700, 75, 140)),
    (110.0, FrameDimensions("315S", 315, 508, 800, 80, 170)),
]


def frame_for_power(rated_power_kw: float) -> FrameDimensions:
    """
    Retourne les dimensions de carcasse typiques pour une puissance donnée
    (moteur 4 pôles standard). Prend la première carcasse de la table dont
    la puissance maximale couvre rated_power_kw ; au-delà de la plus
    grande entrée, extrapole grossièrement (documenté comme tel).
    """
    if rated_power_kw <= 0:
        raise ValueError("rated_power_kw doit être positif")

    for max_power, dims in _IEC_FRAME_TABLE:
        if rated_power_kw <= max_power:
            return dims

    # Au-delà de la table : extrapolation grossière (hors norme couverte),
    # signalée explicitement plutôt que silencieusement approximée.
    largest_power, largest_dims = _IEC_FRAME_TABLE[-1]
    scale = (rated_power_kw / largest_power) ** (1 / 3)  # approx volumique grossière
    return FrameDimensions(
        frame_designation=f"extrapolé au-delà de {largest_dims.frame_designation}",
        shaft_height_mm=largest_dims.shaft_height_mm * scale,
        body_diameter_mm=largest_dims.body_diameter_mm * scale,
        body_length_mm=largest_dims.body_length_mm * scale,
        shaft_diameter_mm=largest_dims.shaft_diameter_mm * scale,
        shaft_length_mm=largest_dims.shaft_length_mm * scale,
    )
