"""
Pont entre un Asset persisté (plaque signalétique réelle chargée par
l'utilisateur) et : (1) le modèle physique du moteur (simulation/motor_physics.py),
(2) la génération du modèle 3D paramétrique via Blender
(tools/blender_motor_generator.py).
"""
import subprocess
import sys
import uuid
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from simulation.frame_dimensions import FrameDimensions, frame_for_power  # noqa: E402
from simulation.motor_physics import InductionMotorModel, NameplateData  # noqa: E402

from app.models.asset import Asset  # noqa: E402

GENERATOR_SCRIPT = _REPO_ROOT / "tools" / "blender_motor_generator.py"
GENERATED_MODELS_DIR = Path(__file__).resolve().parents[2] / "generated_models"


class MissingNameplateDataError(Exception):
    """Levée quand un Asset n'a pas les données minimales pour ce calcul."""


def nameplate_from_asset(asset: Asset) -> NameplateData:
    """
    Extrait les données de plaque signalétique depuis les champs JSON
    libres de l'Asset (electrical_properties / mechanical_properties).
    Ne fabrique aucune valeur non fournie sauf celles explicitement
    documentées comme "typiques" dans motor_physics.py (ex: glissement
    nominal si la vitesse n'est pas connue).
    """
    elec = asset.electrical_properties or {}
    mech = asset.mechanical_properties or {}

    rated_power_kw = elec.get("rated_power_kw")
    poles = mech.get("poles")
    if rated_power_kw is None or poles is None:
        raise MissingNameplateDataError(
            "L'Asset doit fournir au minimum electrical_properties.rated_power_kw "
            "et mechanical_properties.poles pour calculer le modèle physique."
        )

    return NameplateData(
        rated_power_kw=float(rated_power_kw),
        poles=int(poles),
        frequency_hz=float(elec.get("frequency_hz", 50.0)),
        rated_voltage_v=elec.get("rated_voltage_v"),
        rated_current_a=elec.get("rated_current_a"),
        rated_speed_rpm=mech.get("rated_speed_rpm"),
        power_factor=elec.get("power_factor"),
        efficiency=elec.get("efficiency"),
    )


def motor_physics_for_asset(asset: Asset) -> dict:
    """Calcule les grandeurs électromécaniques (couple, glissement...) pour un Asset."""
    nameplate = nameplate_from_asset(asset)
    model = InductionMotorModel(nameplate)
    return model.describe()


def frame_dimensions_for_asset(asset: Asset) -> FrameDimensions:
    """
    Utilise les cotes réelles si présentes dans asset.geometry (données
    constructeur, à privilégier), sinon dérive une estimation IEC 60072
    depuis la puissance nominale (voir frame_dimensions.py pour le statut
    épistémique de cette estimation).
    """
    geometry = asset.geometry or {}
    required_keys = {"shaft_height_mm", "body_diameter_mm", "body_length_mm", "shaft_diameter_mm", "shaft_length_mm"}
    if required_keys.issubset(geometry.keys()):
        return FrameDimensions(
            frame_designation=geometry.get("frame_designation", "fourni par l'utilisateur"),
            shaft_height_mm=float(geometry["shaft_height_mm"]),
            body_diameter_mm=float(geometry["body_diameter_mm"]),
            body_length_mm=float(geometry["body_length_mm"]),
            shaft_diameter_mm=float(geometry["shaft_diameter_mm"]),
            shaft_length_mm=float(geometry["shaft_length_mm"]),
        )

    nameplate = nameplate_from_asset(asset)
    return frame_for_power(nameplate.rated_power_kw)


def generate_glb_for_asset(asset: Asset, timeout_s: int = 60) -> Path:
    """
    Lance Blender en sous-processus pour générer le modèle 3D de cet
    Asset. Retourne le chemin du fichier GLB produit.
    """
    dims = frame_dimensions_for_asset(asset)
    GENERATED_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = GENERATED_MODELS_DIR / f"{asset.id}.glb"

    cmd = [
        "blender", "--background", "--python", str(GENERATOR_SCRIPT), "--",
        "--shaft-height", str(dims.shaft_height_mm),
        "--body-diameter", str(dims.body_diameter_mm),
        "--body-length", str(dims.body_length_mm),
        "--shaft-diameter", str(dims.shaft_diameter_mm),
        "--shaft-length", str(dims.shaft_length_mm),
        "--output", str(output_path),
    ]
    
    # On capture ce que fait Blender
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    
    # ---- DÉBUT DE NOTRE PIÈGE À BUGS ----
    print(f"\n" + "="*40, flush=True)
    print(f"🔍 COMMANDE BLENDER :\n{' '.join(cmd)}", flush=True)
    print(f"🗣️ CE QUE BLENDER A DIT (STDOUT) :\n{result.stdout}", flush=True)
    print(f"🚨 ERREURS DE BLENDER (STDERR) :\n{result.stderr}", flush=True)
    print("="*40 + "\n", flush=True)
    # ---- FIN DU PIÈGE ----

    if result.returncode != 0:
        raise RuntimeError(f"Échec de la génération Blender: {result.stderr[-2000:]}")
    if not output_path.exists():
        raise RuntimeError("Blender s'est terminé sans erreur mais aucun fichier GLB n'a été produit.")
    
    return output_path