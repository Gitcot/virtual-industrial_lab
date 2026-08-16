"""
Générateur 3D - LABORATOIRE D'ÉLECTROTECHNIQUE
Mise à jour : Restauration complète du Rotor, de l'Hélice et de l'Accouplement.
"""
import argparse, math, sys, bpy

def parse_args():
    argv = sys.argv
    if "--" in argv: argv = argv[argv.index("--") + 1:]
    else: argv = []
    parser = argparse.ArgumentParser()
    parser.add_argument("--shaft-height", type=float, required=True)
    parser.add_argument("--body-diameter", type=float, required=True)
    parser.add_argument("--body-length", type=float, required=True)
    parser.add_argument("--shaft-diameter", type=float, required=True)
    parser.add_argument("--shaft-length", type=float, required=True)
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--n-fins", type=int, default=16)
    return parser.parse_args(argv)

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

def mm_to_m(v): return v / 1000.0

def setup_part(obj, name, ui_label, color_rgba, metallic=0.5, roughness=0.5):
    obj.name = name
    obj["partName"] = ui_label 
    mat = bpy.data.materials.new(name=f"Mat_{name}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color_rgba
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
    obj.data.materials.append(mat)

def setup_transparent_part(obj, name, ui_label):
    obj.name = name; obj["partName"] = ui_label 
    mat = bpy.data.materials.new(name=f"Mat_{name}"); mat.use_nodes = True; mat.blend_method = 'BLEND' 
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf: bsdf.inputs["Base Color"].default_value = (0.8, 0.9, 0.9, 0.2); bsdf.inputs["Alpha"].default_value = 0.35
    obj.data.materials.append(mat)

def set_parent_keep_transform(child, parent):
    bpy.ops.object.select_all(action='DESELECT')
    child.select_set(True); parent.select_set(True)
    bpy.context.view_layer.objects.active = parent
    bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)

def build_digital_twin(args):
    clear_scene()
    BLUE, STEEL, CAST, BLACK, WHITE, BRASS, COPPER, GREEN, SCHNEIDER_GREY, DARK_GREY, RED, DUCT_GREY = (0.02, 0.15, 0.35, 1.0), (0.8, 0.8, 0.85, 1.0), (0.15, 0.17, 0.20, 1.0), (0.05, 0.05, 0.05, 1.0), (0.8, 0.8, 0.8, 1.0), (0.8, 0.6, 0.1, 1.0), (0.9, 0.3, 0.1, 1.0), (0.1, 0.8, 0.2, 1.0), (0.75, 0.76, 0.75, 1.0), (0.2, 0.2, 0.2, 1.0), (0.8, 0.1, 0.1, 1.0), (0.4, 0.4, 0.4, 1.0)
    
    R_body = mm_to_m(args.body_diameter) / 2
    L_tot = mm_to_m(args.body_length)
    L_st, L_fl, L_fan, H_shaft = L_tot*0.55, L_tot*0.10, L_tot*0.25, mm_to_m(args.shaft_height)

    # =========================================================
    # 1. LE MOTEUR & STATOR
    # =========================================================
    bpy.ops.mesh.primitive_cylinder_add(radius=R_body, depth=L_st); stator = bpy.context.active_object; stator.rotation_euler=(0,math.pi/2,0); setup_part(stator, "Stator", "Stator", BLUE)
    for i in range(args.n_fins):
        angle = 2 * math.pi * i / args.n_fins; deg = math.degrees(angle)
        if (60 < deg < 120) or (240 < deg < 300): continue 
        y, z = (R_body + R_body*0.09) * math.cos(angle), (R_body + R_body*0.09) * math.sin(angle)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, y, z)); fin = bpy.context.active_object; fin.scale = (L_st, mm_to_m(5), R_body*0.18); fin.rotation_euler=(angle-math.pi/2,0,0); setup_part(fin, f"Fin_{i}", "Ailette", BLUE)
    for sign in [1, -1]:
        bpy.ops.mesh.primitive_cylinder_add(radius=R_body, depth=L_fl*0.5, location=(sign*(L_st/2 + L_fl/4),0,0)); b=bpy.context.active_object; b.rotation_euler=(0,math.pi/2,0); setup_part(b, f"Fl_b_{sign}", "Flasque", CAST)
        bpy.ops.mesh.primitive_cylinder_add(radius=R_body*0.5, depth=L_fl*0.5, location=(sign*(L_st/2 + L_fl*0.75),0,0)); n=bpy.context.active_object; n.rotation_euler=(0,math.pi/2,0); setup_part(n, f"Fl_n_{sign}", "Roulement", CAST)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(sign*L_st*0.3, 0, -H_shaft + mm_to_m(7.5))); f=bpy.context.active_object; f.scale=(L_st*0.25, R_body*1.2, mm_to_m(15)); setup_part(f, f"Foot_{sign}", "Patte", BLUE)
    
    # Capot et grille du ventilateur
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=R_body*1.18, depth=L_fan+L_fl*0.5, end_fill_type='NOTHING', location=(-(L_st/2 + L_fl*0.75 + L_fan*0.5),0,0)); c=bpy.context.active_object; c.rotation_euler=(0,math.pi/2,0); setup_part(c, "FanCover", "Capot", BLUE)
    for i in range(4): 
        bpy.ops.mesh.primitive_cube_add(size=1, location=(-(L_st/2 + L_fl*0.75 + L_fan), 0, 0))
        bar = bpy.context.active_object; bar.scale = (mm_to_m(3), R_body*2.36, mm_to_m(3)); bar.rotation_euler = (math.pi*i/4, 0, 0)
        setup_part(bar, f"Gr_{i}", "Grille", BLUE)
    
    # =========================================================
    # 2. LE ROTOR & SES ÉQUIPEMENTS (La partie qui manquait !)
    # =========================================================
    bpy.ops.object.empty_add(type='PLAIN_AXES'); rotor = bpy.context.active_object; rotor.name = "RotorAssembly"
    R_shaft = mm_to_m(args.shaft_diameter)/2; f_end = L_st/2 + L_fl + mm_to_m(args.shaft_length); r_end = -(L_st/2 + L_fl + L_fan*0.8)
    
    # L'Arbre principal
    bpy.ops.mesh.primitive_cylinder_add(radius=R_shaft, depth=f_end-r_end, location=((f_end+r_end)/2,0,0))
    s=bpy.context.active_object; s.rotation_euler=(0,math.pi/2,0); setup_part(s, "RotorShaft", "Arbre Rotor", STEEL); s.parent=rotor

    # Le Demi-Accouplement (À l'avant)
    coup_x = L_st/2 + L_fl + mm_to_m(args.shaft_length)*0.5
    bpy.ops.mesh.primitive_cylinder_add(radius=R_shaft*2.2, depth=mm_to_m(args.shaft_length)*0.6, location=(coup_x, 0, 0))
    coupling = bpy.context.active_object; coupling.rotation_euler=(0,math.pi/2,0)
    setup_part(coupling, "Coupling", "Demi-accouplement", CAST); coupling.parent = rotor

    # La Vis de fixation (Permet de voir l'accouplement tourner !)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(coup_x, 0, R_shaft*2.2))
    bolt = bpy.context.active_object; bolt.scale=(0.015, 0.015, 0.02)
    setup_part(bolt, "Bolt", "Vis de fixation", BLACK); bolt.parent = rotor

    # Le Moyeu du Ventilateur (À l'arrière)
    fan_x = -(L_st/2 + L_fl + L_fan*0.5)
    bpy.ops.mesh.primitive_cylinder_add(radius=R_shaft*1.8, depth=L_fan*0.2, location=(fan_x, 0, 0))
    hub = bpy.context.active_object; hub.rotation_euler=(0,math.pi/2,0)
    setup_part(hub, "FanHub", "Moyeu", WHITE); hub.parent = rotor

    # Les 3 Pales de l'hélice (Visibles à travers la grille)
    for i in range(3): 
        bpy.ops.mesh.primitive_cube_add(size=1, location=(fan_x, 0, 0))
        blade = bpy.context.active_object
        blade.scale = (L_fan*0.15, R_body*1.6, mm_to_m(3))
        blade.rotation_euler = (math.pi*i/3, math.radians(30), 0) 
        setup_part(blade, f"Bl_{i}", "Pale Ventilateur", WHITE)
        blade.parent = rotor

    # =========================================================
    # 3. BOITE A BORNES
    # =========================================================
    box_s = R_body * 0.7; z_b, z_p = R_body + box_s*0.15, R_body + box_s*0.3
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,z_b)); b=bpy.context.active_object; b.scale=(box_s,box_s,box_s*0.3); setup_part(b, "BoxBase", "Boîte à bornes", BLUE)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,z_p)); t=bpy.context.active_object; t.scale=(box_s*0.6,box_s*0.4,0.02); setup_part(t, "TBlock", "Plaque isolante", BLACK)
    for n, x, y in [("W2",-0.2,0.1),("U2",0,0.1),("V2",0.2,0.1),("U1",-0.2,-0.1),("V1",0,-0.1),("W1",0.2,-0.1)]:
        bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=0.04, location=(x*box_s,y*box_s,z_p+0.02)); setup_part(bpy.context.active_object, f"Term_{n}", f"Borne {n}", BRASS)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=0.04, location=(0.4*box_s,-0.3*box_s,z_p)); setup_part(bpy.context.active_object, "Term_PE", "Borne Terre PE", GREEN)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0.1*box_s,z_p+0.035)); ls=bpy.context.active_object; ls.scale=(box_s*0.5,0.015,0.005); setup_part(ls, "Link_Star", "Barrette Étoile", COPPER)
    for i, x_off in enumerate([-0.2,0,0.2]):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x_off*box_s,0,z_p+0.035)); ld=bpy.context.active_object; ld.scale=(0.015,box_s*0.3,0.005); setup_part(ld, f"Link_Delta_{i}", "Barrette Triangle", COPPER)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,R_body+box_s*0.4)); cv=bpy.context.active_object; cv.scale=(box_s,box_s,box_s*0.1); setup_transparent_part(cv, "TerminalCover", "Couvercle Transparent")

    # =========================================================
    # 4. ARMOIRE TGBT (AVEC CÂBLAGE PORTE ET TERRE)
    # =========================================================
    W_p, D_p, H_p = 0.5, 0.25, 0.7; p_z, p_y = -H_shaft + 0.6, R_body * 3.5 
    for loc, scale, name, label in [((0,p_y+D_p/2,p_z),(W_p,0.02,H_p),"PBack","Fond"), ((0,p_y,p_z+H_p/2),(W_p,D_p,0.02),"PTop","Toit"), ((0,p_y,p_z-H_p/2),(W_p,D_p,0.02),"PBot","Plancher"), ((-W_p/2,p_y,p_z),(0.02,D_p,H_p),"PLeft","Paroi G"), ((W_p/2,p_y,p_z),(0.02,D_p,H_p),"PRight","Paroi D")]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc); p=bpy.context.active_object; p.scale=scale; setup_part(p, name, label, SCHNEIDER_GREY)
    
    # Porte pivotante
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0,p_y-D_p/2,p_z)); door=bpy.context.active_object; door.scale=(W_p,0.02,H_p)
    bpy.ops.object.select_all(action='DESELECT'); door.select_set(True); bpy.context.view_layer.objects.active = door; saved = bpy.context.scene.cursor.location.copy(); bpy.context.scene.cursor.location = (-W_p/2,p_y-D_p/2,p_z); bpy.ops.object.origin_set(type='ORIGIN_CURSOR'); bpy.context.scene.cursor.location = saved 
    setup_part(door, "PanelDoor", "Porte TGBT (Ouvrir)", SCHNEIDER_GREY)

    # Barrette de Terre (PE)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, p_y+D_p/2-0.02, p_z-H_p/2+0.05))
    pe_bar = bpy.context.active_object; pe_bar.scale = (W_p*0.8, 0.01, 0.03)
    setup_part(pe_bar, "PE_Bar", "Collecteur Principal de Terre (PE)", COPPER)

    # Faisceau de Câblage Porte (Toron Noir)
    curve = bpy.data.curves.new('Toron', 'CURVE'); curve.dimensions, curve.bevel_depth = '3D', mm_to_m(10)
    spline = curve.splines.new('POLY'); spline.points.add(2)
    spline.points[0].co = (-W_p/2 + 0.08, p_y-D_p/2 + 0.02, p_z + 0.15, 1) 
    spline.points[1].co = (-W_p/2 + 0.08, p_y+D_p/2 - 0.1, p_z + 0.15, 1) 
    spline.points[2].co = (-W_p/4, p_y+D_p/2 - 0.05, p_z + 0.15, 1) 
    toron = bpy.data.objects.new('WireHarness', curve); bpy.context.collection.objects.link(toron)
    bpy.ops.object.select_all(action='DESELECT'); toron.select_set(True); bpy.context.view_layer.objects.active = toron; bpy.ops.object.convert(target='MESH')
    setup_part(toron, "WireHarness", "Faisceau Commandes", BLACK); set_parent_keep_transform(toron, door)

    # LEDs & Poignée LOTO
    led_z = p_z + H_p*0.35 
    for n, z, l, c in [("LED_Run",0.06,"Marche",(0.05,0.3,0.05,1)), ("LED_Fault",0,"Défaut",(0.3,0.05,0.05,1)), ("LED_Reset",-0.06,"Alarme Sécu",(0.3,0.3,0.05,1))]:
        bpy.ops.mesh.primitive_cylinder_add(radius=0.015, depth=0.04, location=(-W_p/3, p_y-D_p/2-0.03, led_z+z)); led=bpy.context.active_object; led.rotation_euler=(math.pi/2,0,0); setup_part(led, n, l, c, 0.1, 0.2); set_parent_keep_transform(led, door)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.1, p_y-D_p/2-0.04, p_z+0.15)); handle=bpy.context.active_object; handle.scale=(0.02,0.05,0.06); setup_part(handle, "SwitchHandle", "Consignation", RED); set_parent_keep_transform(handle, door)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.015, minor_radius=0.003, location=(-0.1, p_y-D_p/2-0.06, p_z+0.11)); pad=bpy.context.active_object; setup_part(pad, "Padlock", "Cadenas", STEEL); set_parent_keep_transform(pad, door)

    # Composants internes 
    for loc, scale in [((-W_p/2+0.06, p_y+D_p/2-0.03, p_z), (0.04, 0.04, H_p-0.1)), ((W_p/2-0.06, p_y+D_p/2-0.03, p_z), (0.04, 0.04, H_p-0.1)), ((0, p_y+D_p/2-0.03, p_z), (W_p-0.15, 0.04, 0.04))]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc); d=bpy.context.active_object; d.scale=scale; setup_part(d, "Duct", "Goulotte", DUCT_GREY)
    for z in [p_z+0.15, p_z-0.1]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, p_y+D_p/2-0.01, z)); r=bpy.context.active_object; r.scale=(W_p*0.6, 0.01, 0.035); setup_part(r, "DINRail", "Rail DIN", STEEL)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.15, p_y+D_p/2-0.05, p_z+0.15)); sw=bpy.context.active_object; sw.scale=(0.08,0.08,0.08); setup_part(sw, "SwitchInternal", "Sectionneur", DARK_GREY)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.0, p_y+D_p/2-0.05, p_z+0.15)); br=bpy.context.active_object; br.scale=(0.06,0.07,0.09); setup_part(br, "Breaker", "Disjoncteur Q1", BLACK)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.1, p_y+D_p/2-0.06, p_z-0.05)); km1=bpy.context.active_object; km1.scale=(0.07,0.08,0.1); setup_part(km1, "Contactor_KM1", "Contacteur Ligne (KM1)", SCHNEIDER_GREY)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.1, p_y+D_p/2-0.06, p_z-0.16)); rel=bpy.context.active_object; rel.scale=(0.07,0.07,0.08); setup_part(rel, "Relais", "Relais Thermique (F1)", WHITE)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.005, depth=0.01, location=(-0.13, p_y+D_p/2-0.1, p_z-0.19)); setup_part(bpy.context.active_object, "Term_95", "Borne 95", BRASS)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.005, depth=0.01, location=(-0.07, p_y+D_p/2-0.1, p_z-0.19)); setup_part(bpy.context.active_object, "Term_96", "Borne 96", BRASS)

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.0, p_y+D_p/2-0.06, p_z-0.05)); km2=bpy.context.active_object; km2.scale=(0.07,0.08,0.1); setup_part(km2, "Contactor_KM2", "Contacteur Triangle (KM2)", SCHNEIDER_GREY)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.1, p_y+D_p/2-0.06, p_z-0.05)); km3=bpy.context.active_object; km3.scale=(0.07,0.08,0.1); setup_part(km3, "Contactor_KM3", "Contacteur Étoile (KM3)", SCHNEIDER_GREY)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.18, p_y+D_p/2-0.06, p_z-0.05)); tm=bpy.context.active_object; tm.scale=(0.03,0.08,0.08); setup_part(tm, "Timer_Relay", "Temporisateur (KT1)", BLACK)

    # Câble Puissance
    curve = bpy.data.curves.new('C', 'CURVE'); curve.dimensions, curve.bevel_depth = '3D', mm_to_m(12)
    spline = curve.splines.new('POLY'); spline.points.add(3)
    spline.points[0].co = (0,p_y,p_z-H_p/2,1); spline.points[1].co = (0,p_y,-H_shaft,1); spline.points[2].co = (0,0,-H_shaft,1); spline.points[3].co = (0,0,z_b,1)
    c_obj = bpy.data.objects.new('PowerCable', curve); bpy.context.collection.objects.link(c_obj)
    bpy.ops.object.select_all(action='DESELECT'); c_obj.select_set(True); bpy.context.view_layer.objects.active = c_obj; bpy.ops.object.convert(target='MESH')
    setup_part(c_obj, "PowerCable", "Câbles de Puissance", BLACK)

def export_glb(path):
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=False, export_extras=True)

if __name__ == "__main__":
    build_digital_twin(parse_args())
    export_glb(parse_args().output)