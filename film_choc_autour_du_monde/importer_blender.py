"""Importe dans Blender le mouvement calculé par simuler_chaine.py.

À exécuter depuis Blender (onglet Scripting > Ouvrir > Exécuter le script),
le fichier .blend étant enregistré à côté du dossier « donnees_choc », ou :

    blender scene.blend --python importer_blender.py -- --donnees chemin/donnees_choc

Ce script ne calcule aucune physique. Il se contente de :
  - placer les données sur la ligne de temps (temps réel pour les
    balancements, ralenti extrême pour la traversée de la chaîne) ;
  - amplifier les déplacements, réellement microscopiques, d'un facteur
    unique pour toutes les billes ;
  - piloter la lueur de chaque bille par sa compression calculée.

La lueur est une couche séparée : elle sort dans la passe « Emit » et dans
l'AOV « lueur », et peut être dosée ou retirée au compositing sans toucher
au mouvement. Le facteur de ralenti et l'amplification sont enregistrés
dans les propriétés de la scène pour être cités au générique.

Objets créés dans la collection « Choc_Billes » (vidée à chaque exécution) :
  - Pivot.000… : point d'attache de chaque fil ; il porte le balancement ;
  - Bille.000… : enfant de son pivot ; il porte le déplacement dans la chaîne ;
  - Front_onde : suit le centre de l'onde, pour y contraindre la caméra.
"""

import argparse
import json
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

# --- Réglages de mise en scène : aucun ne modifie la physique ---------------
DOSSIER_DONNEES = "//donnees_choc"  # « // » = à côté du fichier .blend
IMAGE_DEBUT = 1
DUREE_ATTENTE_S = 0.5  # bille tenue en arrière avant le lâcher
RALENTI_BALANCEMENT = 1.0  # 1 = temps réel pour la chute et le départ
DUREE_CHOC_S = 3.0  # durée à l'écran de la traversée de la chaîne
FRACTION_RAYON = 0.10  # déplacement typique affiché, en fraction du rayon
INTENSITE_LUEUR = 8.0  # émission au pic de compression
COULEUR_LUEUR = (0.25, 0.55, 1.0, 1.0)

NOM_COLLECTION = "Choc_Billes"
NOM_MAILLAGE = "Bille_choc"
NOM_MATERIAU = "Acier_choc"
NOM_AOV = "lueur"


def lire_arguments():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="importer_blender.py")
    p.add_argument("--donnees", default=DOSSIER_DONNEES, help="dossier écrit par simuler_chaine.py")
    return p.parse_args(argv)


def dossier_donnees(chemin):
    if chemin.startswith("//") and not bpy.data.filepath:
        raise RuntimeError("Enregistrez le fichier .blend ou passez --donnees avec un chemin absolu.")
    dossier = Path(bpy.path.abspath(chemin))
    if not (dossier / "meta.json").exists():
        raise FileNotFoundError(f"Données introuvables dans {dossier} : lancez d'abord simuler_chaine.py.")
    return dossier


def lire_tableau(chemin, n_billes, n_colonnes):
    """CSV « un instant × une bille par ligne » → tableau [instant, bille, colonne]."""
    return np.loadtxt(chemin, delimiter=",", skiprows=1, ndmin=2).reshape(-1, n_billes, n_colonnes)


def preparer_collection():
    collection = bpy.data.collections.get(NOM_COLLECTION)
    if collection is None:
        collection = bpy.data.collections.new(NOM_COLLECTION)
        bpy.context.scene.collection.children.link(collection)
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    ancien = bpy.data.meshes.get(NOM_MAILLAGE)
    if ancien is not None and ancien.users == 0:
        bpy.data.meshes.remove(ancien)
    return collection


def materiau_acier():
    """Acier + émission pilotée par la couleur d'objet (= compression normalisée).

    Le matériau n'est créé que s'il n'existe pas : les retouches faites à la
    main dans l'éditeur de nœuds sont conservées d'une exécution à l'autre."""
    materiau = bpy.data.materials.get(NOM_MATERIAU)
    if materiau is not None:
        return materiau
    materiau = bpy.data.materials.new(NOM_MATERIAU)
    if bpy.app.version < (5, 0, 0):
        materiau.use_nodes = True
    arbre = materiau.node_tree
    noeuds, liens = arbre.nodes, arbre.links
    noeuds.clear()

    sortie = noeuds.new("ShaderNodeOutputMaterial")
    sortie.location = (600, 0)
    acier = noeuds.new("ShaderNodeBsdfPrincipled")
    acier.location = (0, 250)
    acier.inputs["Base Color"].default_value = (0.80, 0.80, 0.82, 1.0)
    acier.inputs["Metallic"].default_value = 1.0
    acier.inputs["Roughness"].default_value = 0.12

    info = noeuds.new("ShaderNodeObjectInfo")
    info.location = (-450, -200)
    gain = noeuds.new("ShaderNodeMath")
    gain.location = (-200, -200)
    gain.operation = "MULTIPLY"
    gain.inputs[1].default_value = INTENSITE_LUEUR
    emission = noeuds.new("ShaderNodeEmission")
    emission.location = (0, -200)
    emission.inputs["Color"].default_value = COULEUR_LUEUR
    somme = noeuds.new("ShaderNodeAddShader")
    somme.location = (350, 0)
    aov = noeuds.new("ShaderNodeOutputAOV")
    aov.location = (350, -300)
    aov.aov_name = NOM_AOV

    liens.new(info.outputs["Color"], gain.inputs[0])
    liens.new(gain.outputs["Value"], emission.inputs["Strength"])
    liens.new(acier.outputs["BSDF"], somme.inputs[0])
    liens.new(emission.outputs["Emission"], somme.inputs[1])
    liens.new(somme.outputs["Shader"], sortie.inputs["Surface"])
    liens.new(info.outputs["Color"], aov.inputs["Value"])
    return materiau


def creer_maillage(rayon, materiau):
    maillage = bpy.data.meshes.new(NOM_MAILLAGE)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=rayon)
    bm.to_mesh(maillage)
    bm.free()
    maillage.polygons.foreach_set("use_smooth", [True] * len(maillage.polygons))
    maillage.update()
    maillage.materials.append(materiau)
    return maillage


def preparer_passes(view_layer):
    view_layer.use_pass_emit = True
    if NOM_AOV not in view_layer.aovs:
        aov = view_layer.aovs.add()
        aov.name = NOM_AOV
        aov.type = "VALUE"


def cle(obj, chemin, image, index=-1):
    obj.keyframe_insert(data_path=chemin, index=index, frame=image)


def main():
    args = lire_arguments()
    dossier = dossier_donnees(args.donnees)
    meta = json.loads((dossier / "meta.json").read_text(encoding="utf-8"))
    n = meta["parametres"]["billes"]
    rayon = meta["parametres"]["rayon_m"]
    longueur = meta["parametres"]["longueur_fil_m"]

    chaine = lire_tableau(dossier / "chaine.csv", n, 6)
    temps = chaine[:, 0, 0]
    deplacement = chaine[:, :, 2]
    compression = chaine[:, :, 4]
    force = chaine[:, :, 5]
    entree = np.loadtxt(dossier / "pendule_entree.csv", delimiter=",", skiprows=1, ndmin=2)
    sortie = lire_tableau(dossier / "pendule_sortie.csv", n, 3)
    t_sortie = sortie[:, 0, 0]

    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base

    # Un seul facteur pour toutes les billes, réglé sur le déplacement typique
    # d'une bille du milieu au passage de l'onde.
    milieu = slice(n // 4, 3 * n // 4)
    amplification = FRACTION_RAYON * rayon / np.median(np.abs(deplacement[:, milieu]).max(axis=0))

    t_chute = entree[-1, 0]
    t_choc = temps[-1]
    image_lacher = IMAGE_DEBUT + round(DUREE_ATTENTE_S * fps)
    image_impact = image_lacher + max(1, round(t_chute * RALENTI_BALANCEMENT * fps))
    n_images_choc = max(2, round(DUREE_CHOC_S * fps))
    image_fin_choc = image_impact + n_images_choc
    image_fin = image_fin_choc + max(1, round(t_sortie[-1] * RALENTI_BALANCEMENT * fps))
    ralenti_choc = DUREE_CHOC_S / t_choc

    collection = preparer_collection()
    maillage = creer_maillage(rayon, materiau_acier())
    pivots, billes = [], []
    for i in range(n):
        pivot = bpy.data.objects.new(f"Pivot.{i:03d}", None)
        pivot.empty_display_type = "PLAIN_AXES"
        pivot.empty_display_size = rayon / 2
        pivot.location = (2 * rayon * i, 0.0, longueur)
        pivot.rotation_mode = "XYZ"
        bille = bpy.data.objects.new(f"Bille.{i:03d}", maillage)
        bille.parent = pivot
        bille.location = (0.0, 0.0, -longueur)
        bille.color = (0.0, 0.0, 0.0, 1.0)
        collection.objects.link(pivot)
        collection.objects.link(bille)
        pivots.append(pivot)
        billes.append(bille)
    front = bpy.data.objects.new("Front_onde", None)
    front.empty_display_type = "SPHERE"
    front.empty_display_size = rayon
    collection.objects.link(front)

    # Angle compté positif vers la chaîne (+X) ; une rotation +Y envoie la
    # bille vers -X, d'où le signe moins.
    def balancement(pivot, angle, image):
        pivot.rotation_euler[1] = -angle
        cle(pivot, "rotation_euler", image, 1)

    # 1. Bille tenue en arrière, puis lâchée (temps réel × RALENTI_BALANCEMENT)
    balancement(pivots[0], entree[0, 1], IMAGE_DEBUT)
    for image in range(image_lacher, image_impact + 1):
        t = (image - image_lacher) / (image_impact - image_lacher) * t_chute
        balancement(pivots[0], np.interp(t, entree[:, 0], entree[:, 1]), image)

    # 2. Traversée de la chaîne, au ralenti. Lueur éteinte juste avant
    # l'impact : sinon la première clé, déjà allumée, vaudrait dès le début.
    for bille in billes:
        cle(bille, "color", image_impact - 1)
    position_repos = 2 * rayon * np.arange(n)
    compression_ref = compression.max()
    demi_image = t_choc / n_images_choc / 2
    x_front = 0.0
    for j, t in enumerate(np.linspace(0.0, t_choc, n_images_choc + 1)):
        image = image_impact + j
        # Pic sur la durée de l'image : une onde plus brève qu'une image ne
        # doit pas clignoter ni disparaître entre deux images.
        debut, fin = np.searchsorted(temps, [t - demi_image, t + demi_image])
        if fin > debut:
            c, f = compression[debut:fin].max(axis=0), force[debut:fin].max(axis=0)
        else:
            c = np.array([np.interp(t, temps, compression[:, i]) for i in range(n)])
            f = np.array([np.interp(t, temps, force[:, i]) for i in range(n)])
        for i, bille in enumerate(billes):
            bille.location.x = amplification * np.interp(t, temps, deplacement[:, i])
            cle(bille, "location", image, 0)
            lueur = min(1.0, c[i] / compression_ref)
            bille.color = (lueur, lueur, lueur, 1.0)
            cle(bille, "color", image)
        if f.sum() > 0:
            x_front = float((f * position_repos).sum() / f.sum())
        front.location = (x_front, 0.0, 0.0)
        cle(front, "location", image, 0)

    # 3. Balancement libre après le choc (temps réel × RALENTI_BALANCEMENT)
    for image in range(image_fin_choc, image_fin + 1):
        t = (image - image_fin_choc) / (image_fin - image_fin_choc) * t_sortie[-1]
        for i, pivot in enumerate(pivots):
            balancement(pivot, np.interp(t, t_sortie, sortie[:, i, 2]), image)

    preparer_passes(bpy.context.view_layer)
    scene.frame_start = IMAGE_DEBUT
    scene.frame_end = image_fin
    scene["ralenti_choc"] = ralenti_choc
    scene["amplification_deplacements"] = amplification
    scene["vitesse_onde_m_s"] = meta["chaine"]["vitesse_onde_m_s"]

    print(f"Lâcher : image {image_lacher}, impact : image {image_impact}, "
          f"fin du choc : image {image_fin_choc}, fin : image {image_fin}")
    print(f"Ralenti de la traversée : ×{ralenti_choc:,.0f}")
    print(f"Amplification des déplacements : ×{amplification:,.0f}")


if __name__ == "__main__":
    main()
