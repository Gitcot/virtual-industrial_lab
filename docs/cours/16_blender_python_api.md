# 16. L'API Python de Blender (bpy) — génération 3D procédurale

## Ce qu'est `bpy` et où il tourne

`bpy` (Blender Python) n'est PAS un paquet pip installable séparément —
c'est le module Python intégré à l'exécutable Blender lui-même. Un script
qui `import bpy` doit être exécuté PAR Blender, pas par un interpréteur
Python classique :
```bash
blender --background --python mon_script.py -- --mon-argument valeur
```
- `--background` : mode headless, sans interface graphique (essentiel sur
  un serveur ou dans une CI/CD)
- `--python mon_script.py` : le script à exécuter
- `--` : tout ce qui suit est destiné AU SCRIPT, pas à Blender lui-même
  (sinon Blender tenterait d'interpréter `--mon-argument` comme sa propre
  option, ce qui échouerait)

## Récupérer les arguments après `--` (piège fréquent)

```python
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []
parser.parse_args(argv)
```
`sys.argv` contient TOUS les arguments, y compris ceux de Blender lui-même
(`blender`, `--background`, `--python`, le chemin du script...). Sans ce
filtrage, `argparse` planterait en essayant d'interpréter des arguments
qui ne lui sont pas destinés.

## Primitives géométriques de base

```python
bpy.ops.mesh.primitive_cylinder_add(radius=0.075, depth=0.23, location=(0, 0, 0))
body = bpy.context.active_object
```
`bpy.ops.mesh.primitive_*_add()` crée une forme de base (cylindre, cube,
sphère...) directement dans la scène. `bpy.context.active_object` récupère
l'objet qui vient d'être créé — un piège classique est d'oublier que
`primitive_*_add()` ne RETOURNE pas l'objet, il faut le récupérer via le
contexte juste après.

## Unités : Blender travaille en mètres

```python
def mm_to_m(value_mm: float) -> float:
    return value_mm / 1000.0
```
Les plaques signalétiques et dimensions mécaniques sont naturellement en
millimètres, mais le format glTF/GLB (cible d'export) utilise le mètre
comme unité standard. **Conversion systématique nécessaire** avant de
créer la géométrie — un oubli produirait un modèle 1000× trop grand ou
trop petit.

## Rotation et repères

```python
body.rotation_euler = (math.pi / 2, 0, 0)  # axe horizontal
```
Un cylindre Blender par défaut a son axe le long de Z (vertical). Pour
représenter un moteur électrique horizontal (convention habituelle), il
faut le faire pivoter de 90° (π/2 radians) autour de l'axe X.
**Erreur rencontrée en le testant** : après cette rotation, l'axe Y du
repère local devient la "longueur" du moteur et l'axe X reste le
"diamètre" — facile de confondre les deux lors d'une vérification
dimensionnelle après coup (voir cours suivant sur les tests).

## Matériaux (nodes Principled BSDF)

```python
mat = bpy.data.materials.new(name="MotorBodyMaterial")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.55, 0.55, 0.58, 1.0)  # RGBA
```
Blender utilise un système de "nodes" pour les matériaux modernes (moteur
de rendu Cycles/Eevee). `Principled BSDF` est le node standard "tout en
un" pour un matériau physiquement plausible — `Base Color` en est
l'entrée la plus simple (couleur de base, format RGBA normalisé 0-1).

## Export GLB

```python
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format="GLB",
    use_selection=False,
)
```
`export_format="GLB"` produit un fichier binaire unique (texture +
géométrie empaquetées ensemble) — plus simple à servir via une API qu'un
`.gltf` (JSON + fichiers séparés). `use_selection=False` exporte toute la
scène, pas seulement les objets actuellement sélectionnés.

## Nettoyer la scène avant de générer (état propre)

```python
def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
```
Blender démarre en mode `--background` avec une scène par défaut (souvent
un cube). Sans ce nettoyage, le modèle généré contiendrait des objets
parasites indésirables dans l'export final.

## Comment ce script a été réellement testé (pas juste écrit)

`tools/tests/test_blender_generator.py` lance Blender en sous-processus
depuis pytest (`subprocess.run(["blender", "--background", ...])`), puis
charge le GLB produit avec la bibliothèque Python `pygltflib` pour
vérifier :
- que le fichier est structurellement valide (meshes, nodes, matériaux présents)
- que les pièces attendues existent (corps, arbre, ailettes, boîte à
  bornes, pattes) en cherchant leurs noms
- que les dimensions du GLB correspondent **exactement** (au mm près) aux
  paramètres passés en argument, en inspectant la bounding box de chaque
  node

C'est ce dernier point qui a révélé une confusion d'axe pendant le
développement (voir plus haut) — sans ce test dimensionnel précis, une
géométrie "à peu près de la bonne taille mais avec les mauvais axes"
serait passée inaperçue.

## Pour aller plus loin
- Documentation API Blender : https://docs.blender.org/api/current/
- glTF 2.0 (format de sortie) : https://www.khronos.org/gltf/
