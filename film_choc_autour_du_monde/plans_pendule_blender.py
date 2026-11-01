"""Plans du pendule de « Le choc autour du monde », pour Blender.

À exécuter depuis Blender, le fichier .blend étant enregistré à côté du
dossier « donnees_choc », ou :

    blender scene.blend --python plans_pendule_blender.py -- --donnees chemin/donnees_choc

Importe le mouvement calculé (importer_blender.py), puis construit autour
le décor (fils, sol, lumières) et la caméra de chaque plan :
  1. la bille tenue en arrière puis lâchée, en contre-plongée (temps réel ×2) ;
  2. le choc, puis l'impulsion suivie le long de la chaîne (ralenti calculé) ;
  3. le départ de la dernière bille (plan 10 de la planche).
La caméra des plans 2 et 3 est calée sur le front d'onde calculé.
L'échelle de temps de chaque plan (ralenti) est incrustée au montage
(rendre_film.py), d'après les repères que renvoie main().
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importer_blender  # noqa: E402

DUREE_ATTENTE_S = 1.2
RALENTI_BALANCEMENT = 2.0
DUREE_CHOC_S = 3.0
TENUE_FINALE_S = 0.6  # plan 10 : la dernière bille reste un instant en haut de sa course
COULEUR_LUEUR = (0.10, 0.35, 1.0, 1.0)
INTENSITE_LUEUR = 3.0


def lisser(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def regarder(position, cible):
    avant = (cible - position).normalized()
    droite = avant.cross(Vector((0, 0, 1))).normalized()
    dessus = droite.cross(avant)
    return Matrix((droite, dessus, -avant)).transposed().to_euler()


def decor(scene, pivots, longueur, rayon):
    """Fils, sol sombre et brillant, studio éclairé."""
    fil = bpy.data.meshes.new("Fil_choc")
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=8, radius1=0.0004, radius2=0.0004, depth=longueur)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, -longueur / 2))
    bm.to_mesh(fil)
    bm.free()
    mat_fil = bpy.data.materials.get("Fil_choc") or bpy.data.materials.new("Fil_choc")
    mat_fil.diffuse_color = (0.55, 0.55, 0.58, 1.0)
    fil.materials.append(mat_fil)
    for pivot in pivots:
        obj = bpy.data.objects.new(f"Fil.{pivot.name[-3:]}", fil)
        obj.parent = pivot
        scene.collection.objects.link(obj)

    sol = bpy.data.meshes.new("Sol_choc")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=6)
    bm.to_mesh(sol)
    bm.free()
    mat_sol = bpy.data.materials.get("Sol_choc") or bpy.data.materials.new("Sol_choc")
    if bpy.app.version < (5, 0, 0):
        mat_sol.use_nodes = True
    bsdf = mat_sol.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.008, 0.010, 0.016, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.32
    sol.materials.append(mat_sol)
    obj = bpy.data.objects.new("Sol", sol)
    obj.location = (1.0, 0.0, -rayon)
    scene.collection.objects.link(obj)

    monde = bpy.data.worlds.get("Studio_choc") or bpy.data.worlds.new("Studio_choc")
    if bpy.app.version < (5, 0, 0):
        monde.use_nodes = True
    fond = monde.node_tree.nodes.get("Background")
    fond.inputs["Color"].default_value = (0.004, 0.006, 0.012, 1.0)
    scene.world = monde

    for nom, position, energie, taille, couleur in (
        ("Lumiere_principale", (0.6, -0.9, 0.9), 90, 1.4, (1.0, 0.97, 0.92)),
        ("Lumiere_contre", (0.8, 1.0, 0.5), 45, 1.2, (0.55, 0.7, 1.0)),
        ("Lumiere_bout", (2.2, -0.4, 0.4), 25, 0.8, (1.0, 1.0, 1.0)),
    ):
        lumiere = bpy.data.objects.new(nom, bpy.data.lights.new(nom, "AREA"))
        lumiere.data.energy = energie
        lumiere.data.size = taille
        lumiere.data.color = couleur
        lumiere.location = position
        lumiere.rotation_euler = regarder(Vector(position), Vector((0.7, 0.0, 0.0)))
        scene.collection.objects.link(lumiere)


def main():
    importer_blender.DUREE_ATTENTE_S = DUREE_ATTENTE_S
    importer_blender.RALENTI_BALANCEMENT = RALENTI_BALANCEMENT
    importer_blender.DUREE_CHOC_S = DUREE_CHOC_S
    importer_blender.COULEUR_LUEUR = COULEUR_LUEUR
    importer_blender.INTENSITE_LUEUR = INTENSITE_LUEUR
    scene = bpy.context.scene
    scene.name = "Choc_Pendule"
    scene.render.fps = 24
    reperes = importer_blender.main()
    rayon, longueur, n = reperes["rayon"], reperes["longueur"], reperes["billes"]
    impact, fin_choc, fin = reperes["image_impact"], reperes["image_fin_choc"], reperes["image_fin"]
    fps = scene.render.fps
    derniere = fin + round(TENUE_FINALE_S * fps)
    scene.frame_end = derniere

    pivots = [o for o in bpy.data.objects if o.name.startswith("Pivot.")]
    decor(scene, sorted(pivots, key=lambda o: o.name), longueur, rayon)

    # Caméra : position, cible et focale clés par image
    donnees = bpy.data.cameras.new("Camera_pendule")
    donnees.dof.use_dof = True
    donnees.dof.aperture_fstop = 2.8
    donnees.clip_start = 0.005
    camera = bpy.data.objects.new("Camera_pendule", donnees)
    scene.collection.objects.link(camera)
    scene.camera = camera
    mise_au_point = bpy.data.objects.new("Mise_au_point", None)
    scene.collection.objects.link(mise_au_point)
    donnees.dof.focus_object = mise_au_point
    front = bpy.data.objects["Front_onde"]
    bille0 = bpy.data.objects["Bille.000"]
    x_fin = 2 * rayon * (n - 1)

    for image in range(scene.frame_start, derniere + 1):
        scene.frame_set(image)
        if image < impact:
            # Plan 1 : contre-plongée sur la bille tenue, lent travelling avant
            k = lisser((image - scene.frame_start) / (impact - scene.frame_start))
            position = Vector((-0.07, -0.30, -0.006)).lerp(Vector((-0.03, -0.20, -0.004)), k)
            cible = Vector((-0.075, 0.0, 0.03)).lerp(Vector((-0.01, 0.0, 0.012)), k)
            focus = bille0.matrix_world.translation.copy()
            focale = 40
        elif image <= fin_choc:
            # Plan 2 : l'impulsion suivie à hauteur des billes, puis la
            # perspective s'élargit sur la fin de la chaîne
            x = front.location.x
            k = lisser((image - (fin_choc - 30)) / 30)
            position = Vector((x - 0.07, -0.11, 0.008)).lerp(Vector((x - 0.55, -0.22, 0.10)), k)
            cible = Vector((x + 0.03, 0.0, 0.0)).lerp(Vector((x + 0.25, 0.0, 0.0)), k)
            focus = Vector((x, 0.0, 0.0))
            focale = 40 + 25 * k
        else:
            # Plan 10 : le bout de la chaîne, la dernière bille s'envole
            position = Vector((x_fin - 0.01, -0.26, 0.02))
            cible = Vector((x_fin + 0.09, 0.0, 0.035))
            focus = Vector((x_fin, 0.0, 0.0))
            focale = 40
        camera.location = position
        camera.rotation_euler = regarder(position, cible)
        donnees.lens = focale
        mise_au_point.location = focus
        camera.keyframe_insert("location", frame=image)
        camera.keyframe_insert("rotation_euler", frame=image)
        donnees.keyframe_insert("lens", frame=image)
        mise_au_point.keyframe_insert("location", frame=image)
    scene.frame_set(scene.frame_start)

    reperes["image_derniere"] = derniere
    reperes["ralenti_balancement"] = RALENTI_BALANCEMENT
    scene["reperes_pendule"] = reperes
    print(f"Scène « Choc_Pendule » : plans 1-4 = images 1 à {fin_choc}, plan 10 = {fin_choc + 1} à {derniere}")
    return reperes


if __name__ == "__main__":
    main()
