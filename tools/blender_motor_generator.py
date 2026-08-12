"""
Générateur de modèle 3D paramétrique d'un moteur asynchrone, via l'API
Python de Blender (bpy). Doit être exécuté par Blender lui-même en mode
headless, PAS par un interpréteur Python classique (bpy n'existe que dans
le processus Blender) :

    blender --background --python tools/blender_motor_generator.py -- \\
        --shaft-height 90 --body-diameter 150 --body-length 230 \\
        --shaft-diameter 24 --shaft-length 50 \\
        --output /chemin/vers/moteur.glb

Les dimensions viennent typiquement de simulation/frame_dimensions.py
(dérivées de la puissance nominale) ou de vraies cotes constructeur si
disponibles (plus précis — à privilégier quand la donnée existe).

⚠️ Ce générateur produit une géométrie PÉDAGOGIQUE représentative (corps
cylindrique, ailettes de refroidissement, boîte à bornes, arbre, pattes de
fixation) — PAS la reproduction exacte d'un modèle commercial. Un vrai
moteur a des détails internes (bobinage, roulements, ventilateur interne)
non modélisés ici, qui n'affectent pas la pédagogie (aspect extérieur et
comportement simulé) mais ne doivent pas être confondus avec un plan de
fabrication.
"""

import argparse
import math
import sys

import bpy


def parse_args():
    # Blender passe ses propres arguments avant "--" ; on ne récupère que
    # ce qui suit, sinon argparse échoue sur les arguments de Blender.
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser(description="Génère un modèle 3D paramétrique de moteur asynchrone")
    parser.add_argument("--shaft-height", type=float, required=True, help="Hauteur d'axe (mm)")
    parser.add_argument("--body-diameter", type=float, required=True, help="Diamètre du corps (mm)")
    parser.add_argument("--body-length", type=float, required=True, help="Longueur du corps (mm)")
    parser.add_argument("--shaft-diameter", type=float, required=True, help="Diamètre de l'arbre (mm)")
    parser.add_argument("--shaft-length", type=float, required=True, help="Longueur de l'arbre sortant (mm)")
    parser.add_argument("--output", type=str, required=True, help="Chemin de sortie .glb")
    parser.add_argument("--n-fins", type=int, default=12, help="Nombre d'ailettes de refroidissement")
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block_collection in (bpy.data.meshes, bpy.data.materials):
        for block in list(block_collection):
            if block.users == 0:
                block_collection.remove(block)


def mm_to_m(value_mm: float) -> float:
    """Blender travaille en mètres par convention (unité par défaut glTF)."""
    return value_mm / 1000.0


def create_motor_body(diameter_mm: float, length_mm: float):
    """Corps cylindrique principal du moteur (stator)."""
    radius = mm_to_m(diameter_mm) / 2
    depth = mm_to_m(length_mm)
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=(0, 0, 0))
    body = bpy.context.active_object
    body.name = "MotorBody"
    body.rotation_euler = (math.pi / 2, 0, 0)  # axe horizontal (convention moteur électrique)
    return body


def create_cooling_fins(diameter_mm: float, length_mm: float, n_fins: int):
    """Ailettes de refroidissement longitudinales autour du corps (aspect visuel typique)."""
    radius = mm_to_m(diameter_mm) / 2
    depth = mm_to_m(length_mm) * 0.85
    fin_height = radius * 0.15
    fin_thickness = mm_to_m(3)

    fins = []
    for i in range(n_fins):
        angle = 2 * math.pi * i / n_fins
        x = (radius + fin_height / 2) * math.cos(angle)
        y = (radius + fin_height / 2) * math.sin(angle)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, 0))
        fin = bpy.context.active_object
        fin.scale = (fin_thickness, fin_height, depth)
        fin.rotation_euler = (0, 0, angle)
        fin.name = f"Fin_{i:02d}"
        fins.append(fin)
    return fins


def create_shaft(shaft_diameter_mm: float, shaft_length_mm: float, body_length_mm: float):
    """Arbre sortant du moteur (là où se fixe la charge mécanique)."""
    radius = mm_to_m(shaft_diameter_mm) / 2
    depth = mm_to_m(shaft_length_mm)
    body_half_length = mm_to_m(body_length_mm) / 2
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth,
        location=(body_half_length + depth / 2, 0, 0),
    )
    shaft = bpy.context.active_object
    shaft.rotation_euler = (0, math.pi / 2, 0)
    shaft.name = "Shaft"
    return shaft


def create_terminal_box(diameter_mm: float, length_mm: float):
    """Boîte à bornes (raccordement électrique), sur le dessus du corps."""
    radius = mm_to_m(diameter_mm) / 2
    box_size = mm_to_m(diameter_mm) * 0.35
    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=(0, 0, radius + box_size / 2),
    )
    box = bpy.context.active_object
    box.scale = (box_size * 0.8, box_size, box_size)
    box.name = "TerminalBox"
    return box


def create_feet(diameter_mm: float, length_mm: float):
    """Pattes de fixation sous le moteur."""
    radius = mm_to_m(diameter_mm) / 2
    depth = mm_to_m(length_mm)
    foot_height = radius * 0.25
    foot_width = mm_to_m(20)

    feet = []
    for sign, x_frac in [(-1, -0.3), (1, 0.3)]:
        x = depth * x_frac
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0, -(radius + foot_height / 2)))
        foot = bpy.context.active_object
        foot.scale = (foot_width, radius * 1.6, foot_height)
        foot.name = f"Foot_{'L' if sign < 0 else 'R'}"
        feet.append(foot)
    return feet


def assign_material(objects, name, color_rgba):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color_rgba
    for obj in objects:
        obj.data.materials.append(mat)


def build_motor(args):
    clear_scene()

    body = create_motor_body(args.body_diameter, args.body_length)
    fins = create_cooling_fins(args.body_diameter, args.body_length, args.n_fins)
    shaft = create_shaft(args.shaft_diameter, args.shaft_length, args.body_length)
    terminal_box = create_terminal_box(args.body_diameter, args.body_length)
    feet = create_feet(args.body_diameter, args.body_length)

    assign_material([body], "MotorBodyMaterial", (0.55, 0.55, 0.58, 1.0))  # gris métal
    assign_material(fins, "FinsMaterial", (0.5, 0.5, 0.53, 1.0))
    assign_material([shaft], "ShaftMaterial", (0.75, 0.75, 0.78, 1.0))  # acier plus clair
    assign_material([terminal_box], "TerminalBoxMaterial", (0.15, 0.15, 0.15, 1.0))  # noir
    assign_material(feet, "FeetMaterial", (0.4, 0.4, 0.42, 1.0))

    # Fusionner tout sous un objet racine nommé, pour un export GLB propre
    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active = body
    all_objects = list(bpy.context.selected_objects)
    return all_objects


def export_glb(output_path: str):
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format="GLB",
        use_selection=False,
    )


def main():
    args = parse_args()
    build_motor(args)
    export_glb(args.output)
    print(f"OK: moteur exporté vers {args.output}")


if __name__ == "__main__":
    main()
