"""
Tests d'intégration du générateur 3D Blender. Contrairement aux autres
tests du projet, ceux-ci lancent réellement Blender en sous-processus
(lent : quelques secondes par test) et valident le fichier GLB produit
avec pygltflib. Nécessitent que `blender` soit installé et dans le PATH.

Ces tests sont marqués séparément (voir pytest.ini / marker "blender")
pour pouvoir être exclus des cycles de test rapides si Blender n'est pas
disponible dans un environnement donné.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pygltflib = pytest.importorskip("pygltflib")
from pygltflib import GLTF2  # noqa: E402

BLENDER_AVAILABLE = shutil.which("blender") is not None
pytestmark = pytest.mark.skipif(
    not BLENDER_AVAILABLE, reason="Blender n'est pas installé sur cette machine"
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR_SCRIPT = REPO_ROOT / "tools" / "blender_motor_generator.py"


def run_generator(tmp_path, **dims):
    tmp_path.mkdir(parents=True, exist_ok=True)
    output_path = tmp_path / "motor.glb"
    cmd = [
        "blender", "--background", "--python", str(GENERATOR_SCRIPT), "--",
        "--shaft-height", str(dims["shaft_height"]),
        "--body-diameter", str(dims["body_diameter"]),
        "--body-length", str(dims["body_length"]),
        "--shaft-diameter", str(dims["shaft_diameter"]),
        "--shaft-length", str(dims["shaft_length"]),
        "--output", str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, f"Blender a échoué:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    assert output_path.exists(), "Le fichier GLB n'a pas été créé"
    return output_path


def get_node_bbox(gltf, node_name):
    for node in gltf.nodes:
        if node.name == node_name:
            acc = gltf.accessors[gltf.meshes[node.mesh].primitives[0].attributes.POSITION]
            return acc.min, acc.max
    raise AssertionError(f"Node '{node_name}' introuvable dans le GLB")


def test_generator_produces_valid_glb(tmp_path):
    output_path = run_generator(
        tmp_path, shaft_height=90, body_diameter=150, body_length=230,
        shaft_diameter=24, shaft_length=50,
    )
    gltf = GLTF2().load(str(output_path))
    assert len(gltf.meshes) > 0
    assert len(gltf.nodes) > 0
    assert len(gltf.materials) > 0


def test_generator_creates_expected_named_parts(tmp_path):
    output_path = run_generator(
        tmp_path, shaft_height=90, body_diameter=150, body_length=230,
        shaft_diameter=24, shaft_length=50,
    )
    gltf = GLTF2().load(str(output_path))
    node_names = {n.name for n in gltf.nodes}
    assert "MotorBody" in node_names
    assert "Shaft" in node_names
    assert "TerminalBox" in node_names
    assert "Foot_L" in node_names
    assert "Foot_R" in node_names
    fin_names = [n for n in node_names if n.startswith("Fin_")]
    assert len(fin_names) == 12  # valeur par défaut --n-fins


def test_generator_body_diameter_matches_input(tmp_path):
    output_path = run_generator(
        tmp_path, shaft_height=90, body_diameter=150, body_length=230,
        shaft_diameter=24, shaft_length=50,
    )
    gltf = GLTF2().load(str(output_path))
    bmin, bmax = get_node_bbox(gltf, "MotorBody")
    diameter_m = bmax[0] - bmin[0]
    assert diameter_m == pytest.approx(0.150, abs=0.001)  # 150mm


def test_generator_body_length_matches_input(tmp_path):
    output_path = run_generator(
        tmp_path, shaft_height=90, body_diameter=150, body_length=230,
        shaft_diameter=24, shaft_length=50,
    )
    gltf = GLTF2().load(str(output_path))
    bmin, bmax = get_node_bbox(gltf, "MotorBody")
    length_m = bmax[1] - bmin[1]
    assert length_m == pytest.approx(0.230, abs=0.001)  # 230mm


def test_larger_nameplate_produces_larger_geometry(tmp_path):
    small = run_generator(
        tmp_path / "small", shaft_height=90, body_diameter=150, body_length=230,
        shaft_diameter=24, shaft_length=50,
    )
    big = run_generator(
        tmp_path / "big", shaft_height=200, body_diameter=318, body_length=530,
        shaft_diameter=55, shaft_length=110,
    )
    gltf_small = GLTF2().load(str(small))
    gltf_big = GLTF2().load(str(big))

    dmin_s, dmax_s = get_node_bbox(gltf_small, "MotorBody")
    dmin_b, dmax_b = get_node_bbox(gltf_big, "MotorBody")

    diameter_small = dmax_s[0] - dmin_s[0]
    diameter_big = dmax_b[0] - dmin_b[0]
    assert diameter_big > diameter_small

    ratio_observed = diameter_big / diameter_small
    ratio_expected = 318 / 150
    assert ratio_observed == pytest.approx(ratio_expected, rel=0.01)
