"""Plans terrestres (5 à 11) de « Le choc autour du monde », pour Blender.

À exécuter depuis Blender (onglet Scripting > Ouvrir > Exécuter le script),
le fichier .blend étant enregistré à côté des dossiers « donnees_choc » et
« textures », ou :

    blender scene.blend --python plans_terre_blender.py -- \
        --donnees chemin/donnees_choc --textures chemin/textures

Crée (ou recrée) la scène « Choc_Terre » : la Terre, une chaîne de billes
le long du méridien de Paris, l'impulsion qui en fait le tour, la caméra de
chaque plan et les compteurs.

Le seul chiffre physique utilisé est la vitesse de l'onde calculée par
simuler_chaine.py. Tout le reste est de la mise en scène, et les compteurs
le disent :
  - la distance parcourue est animée en accéléré (de plus en plus vite) ;
  - le temps réel affiché vaut toujours distance / vitesse calculée ;
  - le facteur d'accélération affiché est celui de l'image en cours ;
  - les billes sont agrandies et la lueur ne fait que repérer l'impulsion
    (sa largeur réelle, quelques billes, serait invisible à cette échelle).

Textures attendues dans le dossier « textures » (équirectangulaires) :
terre_jour.jpg et terre_nuit.jpg. Sans elles, la Terre est d'un bleu uni.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

# --- Réglages de mise en scène : aucun ne modifie la physique ---------------
DOSSIER_DONNEES = "//donnees_choc"
DOSSIER_TEXTURES = "//textures"
IMAGE_DEBUT = 1
FPS = 24

# Distance parcourue (km) à différents instants du film (s), d'après la
# planche : lâcher à Paris, 2 000 km à la fin du plan 7, sortie de l'Afrique
# (Cotonou) à la fin du plan 8, presque un tour à la fin du plan 9.
CLES_DISTANCE = [(3.5, 0.0), (6.0, 2_000.0), (7.0, 4_722.0), (8.0, 39_000.0), (8.4, 40_008.0)]
INSTANT_LACHER_S = 3.5

# Plans : (nom, début s, fin s)
PLANS = [("5", 0.0, 2.0), ("6", 2.0, 4.0), ("7", 4.0, 6.0), ("8", 6.0, 7.0), ("9", 7.0, 8.0), ("11", 8.0, 10.0)]

RAYON_ANNEAU = 1.05  # en rayons terrestres
BILLES_VISIBLES = 600
INTENSITE_LUEUR = 12.0
INTENSITE_HALO = 2.5  # halo qui repère l'impulsion dans les plans larges
TAILLE_HALO = 0.02  # rayon du halo par unité de distance à la caméra
COULEUR_LUEUR = (0.15, 0.45, 1.0, 1.0)
LARGEUR_LUEUR = 0.004  # fraction du tour (≈ 160 km)
DIRECTION_SOLEIL = (10.0, 50.0)  # point subsolaire (latitude, longitude)

NOM_SCENE = "Choc_Terre"
NOM_AOV = "lueur"

TOUR_MERIDIEN_KM = 40_008.0
PARIS = (48.8566, 2.3522)

CODE_COMPTEUR = '''import bpy


def _milliers(x):
    return f"{x:,.0f}".replace(",", " ")


def maj_compteur_choc(scene, *args):
    distances = scene.get("terre_distance_km")
    compteur = bpy.data.objects.get("Compteur")
    if distances is None or compteur is None:
        return
    i = min(max(scene.frame_current - scene["terre_image_debut"], 0), len(distances) - 1)
    km = distances[i]
    minutes = round(km * 1000 / scene["vitesse_onde_m_s"] / 60)
    h, m = divmod(minutes, 60)
    compteur.data.body = (
        f"Distance : {_milliers(km)} km\\n"
        f"Temps réel : {h} h {m:02d} min\\n"
        f"Accéléré ×{_milliers(scene['terre_acceleration'][i])}"
    )


for _h in [h for h in bpy.app.handlers.frame_change_pre if h.__name__ == "maj_compteur_choc"]:
    bpy.app.handlers.frame_change_pre.remove(_h)
bpy.app.handlers.frame_change_pre.append(maj_compteur_choc)
'''


def lire_arguments():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="plans_terre_blender.py")
    p.add_argument("--donnees", default=DOSSIER_DONNEES, help="dossier écrit par simuler_chaine.py")
    p.add_argument("--textures", default=DOSSIER_TEXTURES, help="dossier des textures de la Terre")
    return p.parse_args(argv)


def chemin(texte):
    if texte.startswith("//") and not bpy.data.filepath:
        raise RuntimeError("Enregistrez le fichier .blend ou passez des chemins absolus.")
    return Path(bpy.path.abspath(texte))


def sph(lat, lon, rayon=1.0):
    lat, lon = math.radians(lat), math.radians(lon)
    return Vector((math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat))) * rayon


def point_anneau(km, rayon=RAYON_ANNEAU):
    """Point de l'anneau à `km` de Paris, en descendant le méridien de Paris."""
    theta = math.radians(PARIS[0]) - km / TOUR_MERIDIEN_KM * 2 * math.pi
    lon = math.radians(PARIS[1])
    return Vector((math.cos(theta) * math.cos(lon), math.cos(theta) * math.sin(lon), math.sin(theta))) * rayon


def pchip(x, y, xi):
    """Interpolation cubique monotone (Fritsch-Carlson) : la distance ne recule
    jamais et l'impulsion ne marque pas d'arrêt aux points de passage."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    h = np.diff(x)
    pente = np.diff(y) / h
    d = np.zeros_like(y)
    for k in range(1, len(x) - 1):
        if pente[k - 1] * pente[k] > 0:
            w1, w2 = 2 * h[k] + h[k - 1], h[k] + 2 * h[k - 1]
            d[k] = (w1 + w2) / (w1 / pente[k - 1] + w2 / pente[k])
    d[0], d[-1] = pente[0], pente[-1]
    xi = np.clip(xi, x[0], x[-1])
    k = np.clip(np.searchsorted(x, xi) - 1, 0, len(h) - 1)
    s = (xi - x[k]) / h[k]
    h00, h10 = 2 * s**3 - 3 * s**2 + 1, s**3 - 2 * s**2 + s
    h01, h11 = -2 * s**3 + 3 * s**2, s**3 - s**2
    return h00 * y[k] + h10 * h[k] * d[k] + h01 * y[k + 1] + h11 * h[k] * d[k + 1]


# --- Nœuds -------------------------------------------------------------------

def math_noeud(arbre, operation, a, b=None):
    noeud = arbre.nodes.new("ShaderNodeMath")
    noeud.operation = operation
    for i, valeur in enumerate((a, b)):
        if valeur is None:
            continue
        if isinstance(valeur, (int, float)):
            noeud.inputs[i].default_value = valeur
        else:
            arbre.links.new(valeur, noeud.inputs[i])
    return noeud.outputs[0]


def nouveau_materiau(nom):
    ancien = bpy.data.materials.get(nom)
    if ancien is not None:
        bpy.data.materials.remove(ancien)
    materiau = bpy.data.materials.new(nom)
    if bpy.app.version < (5, 0, 0):
        materiau.use_nodes = True
    materiau.node_tree.nodes.clear()
    return materiau, materiau.node_tree


def charger_image(dossier, nom, non_couleur=False):
    fichier = dossier / nom
    if not fichier.exists():
        print(f"Texture absente : {fichier}")
        return None
    image = bpy.data.images.load(str(fichier), check_existing=True)
    if non_couleur:
        image.colorspace_settings.name = "Non-Color"
    return image


def materiau_terre(dossier_textures, direction_soleil):
    materiau, arbre = nouveau_materiau("Terre_choc")
    n, l = arbre.nodes, arbre.links
    sortie = n.new("ShaderNodeOutputMaterial")
    sol = n.new("ShaderNodeBsdfPrincipled")
    sol.inputs["Roughness"].default_value = 0.65
    somme = n.new("ShaderNodeAddShader")
    l.new(sol.outputs["BSDF"], somme.inputs[0])
    l.new(somme.outputs["Shader"], sortie.inputs["Surface"])
    uv = n.new("ShaderNodeTexCoord")

    jour = charger_image(dossier_textures, "terre_jour.jpg")
    if jour is not None:
        tex = n.new("ShaderNodeTexImage")
        tex.image = jour
        l.new(uv.outputs["UV"], tex.inputs["Vector"])
        l.new(tex.outputs["Color"], sol.inputs["Base Color"])
    else:
        sol.inputs["Base Color"].default_value = (0.02, 0.08, 0.25, 1.0)

    # Lumières des villes, seulement du côté nuit
    nuit = charger_image(dossier_textures, "terre_nuit.jpg")
    if nuit is not None:
        tex = n.new("ShaderNodeTexImage")
        tex.image = nuit
        l.new(uv.outputs["UV"], tex.inputs["Vector"])
        geometrie = n.new("ShaderNodeNewGeometry")
        produit = n.new("ShaderNodeVectorMath")
        produit.operation = "DOT_PRODUCT"
        produit.inputs[1].default_value = direction_soleil
        l.new(geometrie.outputs["Normal"], produit.inputs[0])
        masque = n.new("ShaderNodeMapRange")
        masque.inputs["From Min"].default_value = -0.05
        masque.inputs["From Max"].default_value = 0.2
        masque.inputs["To Min"].default_value = 1.0
        masque.inputs["To Max"].default_value = 0.0
        l.new(produit.outputs["Value"], masque.inputs["Value"])
        villes = n.new("ShaderNodeEmission")
        l.new(tex.outputs["Color"], villes.inputs["Color"])
        l.new(math_noeud(arbre, "MULTIPLY", masque.outputs["Result"], 2.0), villes.inputs["Strength"])
        l.new(villes.outputs["Emission"], somme.inputs[1])
    return materiau


def materiau_atmosphere():
    materiau, arbre = nouveau_materiau("Atmosphere_choc")
    n, l = arbre.nodes, arbre.links
    sortie = n.new("ShaderNodeOutputMaterial")
    poids = n.new("ShaderNodeLayerWeight")
    poids.inputs["Blend"].default_value = 0.2
    transparent = n.new("ShaderNodeBsdfTransparent")
    halo = n.new("ShaderNodeEmission")
    halo.inputs["Color"].default_value = (0.25, 0.5, 1.0, 1.0)
    halo.inputs["Strength"].default_value = 2.0
    melange = n.new("ShaderNodeMixShader")
    l.new(math_noeud(arbre, "POWER", poids.outputs["Facing"], 5.0), melange.inputs["Fac"])
    l.new(transparent.outputs["BSDF"], melange.inputs[1])
    l.new(halo.outputs["Emission"], melange.inputs[2])
    l.new(melange.outputs["Shader"], sortie.inputs["Surface"])
    return materiau


def materiau_anneau():
    """Acier + lueur calculée dans le shader à partir de la position de la
    bille sur l'anneau et du front d'onde (couleur d'objet : R = fraction du
    tour parcourue, G = 1 une fois la première bille lâchée)."""
    materiau, arbre = nouveau_materiau("Anneau_choc")
    n, l = arbre.nodes, arbre.links
    sortie = n.new("ShaderNodeOutputMaterial")
    acier = n.new("ShaderNodeBsdfPrincipled")
    acier.inputs["Base Color"].default_value = (0.8, 0.8, 0.82, 1.0)
    acier.inputs["Metallic"].default_value = 1.0
    acier.inputs["Roughness"].default_value = 0.2

    # Position de chaque point de l'anneau, en fraction de tour depuis Paris
    coord = n.new("ShaderNodeTexCoord")
    xyz = n.new("ShaderNodeSeparateXYZ")
    l.new(coord.outputs["Object"], xyz.inputs[0])
    lon = math.radians(PARIS[1])
    r = math_noeud(arbre, "ADD",
                   math_noeud(arbre, "MULTIPLY", xyz.outputs["X"], math.cos(lon)),
                   math_noeud(arbre, "MULTIPLY", xyz.outputs["Y"], math.sin(lon)))
    theta = math_noeud(arbre, "ARCTAN2", xyz.outputs["Z"], r)
    position = math_noeud(arbre, "FRACT", math_noeud(
        arbre, "MULTIPLY", math_noeud(arbre, "SUBTRACT", math.radians(PARIS[0]), theta), 1 / (2 * math.pi)))

    info = n.new("ShaderNodeObjectInfo")
    canaux = n.new("ShaderNodeSeparateColor")
    l.new(info.outputs["Color"], canaux.inputs["Color"])
    front, actif = canaux.outputs[0], canaux.outputs[1]

    # Écart au front, ramené entre -0,5 et 0,5 tour (positif = déjà traversé)
    ecart = math_noeud(arbre, "SUBTRACT", math_noeud(
        arbre, "FRACT", math_noeud(arbre, "ADD", math_noeud(arbre, "SUBTRACT", front, position), 0.5)), 0.5)
    reduit = math_noeud(arbre, "DIVIDE", ecart, LARGEUR_LUEUR)
    tete = math_noeud(arbre, "EXPONENT", math_noeud(
        arbre, "MULTIPLY", math_noeud(arbre, "MULTIPLY", reduit, reduit), -1.0))
    derriere = math_noeud(arbre, "MULTIPLY",
                          math_noeud(arbre, "GREATER_THAN", ecart, 0.0),
                          math_noeud(arbre, "LESS_THAN", ecart, front))
    trainee = math_noeud(arbre, "MULTIPLY", derriere, math_noeud(
        arbre, "MULTIPLY", math_noeud(arbre, "EXPONENT", math_noeud(arbre, "MULTIPLY", ecart, -1 / 0.03)), 0.3))
    lueur = math_noeud(arbre, "MULTIPLY", math_noeud(arbre, "ADD", tete, trainee), actif)

    emission = n.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = COULEUR_LUEUR
    l.new(math_noeud(arbre, "MULTIPLY", lueur, INTENSITE_LUEUR), emission.inputs["Strength"])
    somme = n.new("ShaderNodeAddShader")
    l.new(acier.outputs["BSDF"], somme.inputs[0])
    l.new(emission.outputs["Emission"], somme.inputs[1])
    l.new(somme.outputs["Shader"], sortie.inputs["Surface"])
    aov = n.new("ShaderNodeOutputAOV")
    aov.aov_name = NOM_AOV
    l.new(lueur, aov.inputs["Value"])
    return materiau


def materiau_halo():
    """Boule lumineuse floue : intense au centre, transparente sur les bords."""
    materiau, arbre = nouveau_materiau("Halo_choc")
    n, l = arbre.nodes, arbre.links
    sortie = n.new("ShaderNodeOutputMaterial")
    poids = n.new("ShaderNodeLayerWeight")
    poids.inputs["Blend"].default_value = 0.5
    coeur = math_noeud(arbre, "POWER", math_noeud(arbre, "SUBTRACT", 1.0, poids.outputs["Facing"]), 6.0)
    transparent = n.new("ShaderNodeBsdfTransparent")
    emission = n.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = COULEUR_LUEUR
    emission.inputs["Strength"].default_value = INTENSITE_HALO
    melange = n.new("ShaderNodeMixShader")
    l.new(coeur, melange.inputs["Fac"])
    l.new(transparent.outputs["BSDF"], melange.inputs[1])
    l.new(emission.outputs["Emission"], melange.inputs[2])
    l.new(melange.outputs["Shader"], sortie.inputs["Surface"])
    aov = n.new("ShaderNodeOutputAOV")
    aov.aov_name = NOM_AOV
    l.new(coeur, aov.inputs["Value"])
    return materiau


def materiau_texte():
    materiau, arbre = nouveau_materiau("Texte_choc")
    emission = arbre.nodes.new("ShaderNodeEmission")
    emission.inputs["Strength"].default_value = 1.5
    sortie = arbre.nodes.new("ShaderNodeOutputMaterial")
    arbre.links.new(emission.outputs["Emission"], sortie.inputs["Surface"])
    return materiau


def monde_etoile(scene):
    monde = bpy.data.worlds.get("Ciel_choc") or bpy.data.worlds.new("Ciel_choc")
    if bpy.app.version < (5, 0, 0):
        monde.use_nodes = True
    arbre = monde.node_tree
    arbre.nodes.clear()
    coord = arbre.nodes.new("ShaderNodeTexCoord")
    voronoi = arbre.nodes.new("ShaderNodeTexVoronoi")
    voronoi.inputs["Scale"].default_value = 350.0
    arbre.links.new(coord.outputs["Generated"], voronoi.inputs["Vector"])
    etoiles = math_noeud(arbre, "MULTIPLY", math_noeud(arbre, "LESS_THAN", voronoi.outputs["Distance"], 0.05), 0.6)
    fond = arbre.nodes.new("ShaderNodeBackground")
    fond.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    arbre.links.new(math_noeud(arbre, "ADD", etoiles, 0.002), fond.inputs["Strength"])
    sortie = arbre.nodes.new("ShaderNodeOutputWorld")
    arbre.links.new(fond.outputs["Background"], sortie.inputs["Surface"])
    scene.world = monde


# --- Géométrie ---------------------------------------------------------------

def maillage_terre(nom, rayon, n_lon=256, n_lat=128):
    """Sphère dont les UV suivent exactement longitude et latitude."""
    lon = np.linspace(-math.pi, math.pi, n_lon + 1)
    lat = np.linspace(-math.pi / 2, math.pi / 2, n_lat + 1)
    lo, la = np.meshgrid(lon, lat)
    sommets = np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], axis=-1) * rayon
    indice = np.arange((n_lat + 1) * (n_lon + 1)).reshape(n_lat + 1, n_lon + 1)
    faces = np.stack([indice[:-1, :-1], indice[:-1, 1:], indice[1:, 1:], indice[1:, :-1]], axis=-1).reshape(-1, 4)
    maillage = bpy.data.meshes.new(nom)
    maillage.from_pydata(sommets.reshape(-1, 3).tolist(), [], faces.tolist())
    uv_sommets = np.stack([(lo + math.pi) / (2 * math.pi), (la + math.pi / 2) / math.pi], axis=-1).reshape(-1, 2)
    couche = maillage.uv_layers.new(name="UVMap")
    boucles = np.zeros(len(maillage.loops), dtype=np.int32)
    maillage.loops.foreach_get("vertex_index", boucles)
    couche.data.foreach_set("uv", uv_sommets[boucles].ravel())
    maillage.polygons.foreach_set("use_smooth", [True] * len(maillage.polygons))
    maillage.update()
    return maillage


def maillage_anneau(nom, n_billes, rayon_anneau):
    """Toutes les billes de l'anneau dans un seul maillage, au contact."""
    rayon_bille = math.pi * rayon_anneau / n_billes
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=rayon_bille)
    modele_sommets = np.array([v.co[:] for v in bm.verts])
    modele_faces = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()
    sommets, faces = [], []
    for k in range(n_billes):
        centre = np.array(point_anneau(k / n_billes * TOUR_MERIDIEN_KM, rayon_anneau))
        decalage = k * len(modele_sommets)
        sommets.extend((modele_sommets + centre).tolist())
        faces.extend([[i + decalage for i in f] for f in modele_faces])
    maillage = bpy.data.meshes.new(nom)
    maillage.from_pydata(sommets, [], faces)
    maillage.polygons.foreach_set("use_smooth", [True] * len(maillage.polygons))
    maillage.update()
    return maillage


def preparer_scene():
    ancienne = bpy.data.scenes.get(NOM_SCENE)
    if ancienne is not None:
        for obj in list(ancienne.collection.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.scenes.remove(ancienne)
    scene = bpy.data.scenes.new(NOM_SCENE)
    if bpy.context.window is not None:
        bpy.context.window.scene = scene
    return scene


def objet(scene, nom, donnees, materiau=None):
    obj = bpy.data.objects.new(nom, donnees)
    if materiau is not None:
        donnees.materials.append(materiau)
    scene.collection.objects.link(obj)
    return obj


def texte(scene, nom, contenu, camera, position, taille, alignement, materiau):
    courbe = bpy.data.curves.new(nom, "FONT")
    courbe.body = contenu
    courbe.size = taille
    courbe.align_x = alignement
    obj = objet(scene, nom, courbe, materiau)
    obj.parent = camera
    obj.location = position
    obj.visible_shadow = False
    return obj


def visible_pendant(obj, debut_s, fin_s, image_fin):
    """Affiche l'objet entre deux instants du film seulement."""
    for image, cache in ((IMAGE_DEBUT, True), (IMAGE_DEBUT + round(debut_s * FPS), False),
                         (IMAGE_DEBUT + round(fin_s * FPS), True)):
        if image > image_fin:
            continue
        obj.hide_render = obj.hide_viewport = cache
        obj.keyframe_insert("hide_render", frame=image)
        obj.keyframe_insert("hide_viewport", frame=image)


def cle_pose(camera, cible, image, position_camera, position_cible):
    camera.location = position_camera
    cible.location = position_cible
    camera.keyframe_insert("location", frame=image)
    cible.keyframe_insert("location", frame=image)


def main():
    args = lire_arguments()
    dossier = chemin(args.donnees)
    meta = json.loads((dossier / "meta.json").read_text(encoding="utf-8"))
    vitesse = meta["chaine"]["vitesse_onde_m_s"]
    rayon_bille_reel = meta["parametres"]["rayon_m"]

    scene = preparer_scene()
    scene.render.fps = FPS
    duree = PLANS[-1][2]
    image_fin = IMAGE_DEBUT + round(duree * FPS)
    scene.frame_start, scene.frame_end = IMAGE_DEBUT, image_fin
    monde_etoile(scene)

    soleil_dir = sph(*DIRECTION_SOLEIL)
    soleil = objet(scene, "Soleil", bpy.data.lights.new("Soleil", "SUN"))
    soleil.data.energy = 4.0
    soleil.rotation_euler = (-soleil_dir).to_track_quat("-Z", "Y").to_euler()

    objet(scene, "Terre", maillage_terre("Terre", 1.0), materiau_terre(chemin(args.textures), soleil_dir))
    atmosphere = objet(scene, "Atmosphere", maillage_terre("Atmosphere", 1.025, 128, 64), materiau_atmosphere())
    atmosphere.visible_shadow = False
    anneau = objet(scene, "Chaine_terrestre", maillage_anneau("Chaine_terrestre", BILLES_VISIBLES, RAYON_ANNEAU),
                   materiau_anneau())

    # Distance parcourue à chaque image, et accélération correspondante
    temps = np.arange(image_fin - IMAGE_DEBUT + 1) / FPS
    t_cles, km_cles = zip(*CLES_DISTANCE)
    distance = np.where(temps < t_cles[0], 0.0, pchip(t_cles, km_cles, temps))
    km_par_s_film = np.gradient(distance, temps)
    acceleration = km_par_s_film * 1000 / vitesse  # secondes réelles par seconde de film

    halo = objet(scene, "Halo_front", maillage_terre("Halo_front", 1.0, 32, 16), materiau_halo())
    halo.visible_shadow = False
    for i, km in enumerate(distance):
        actif = 1.0 if temps[i] >= INSTANT_LACHER_S else 0.0
        anneau.color = (km / TOUR_MERIDIEN_KM, actif, 0.0, 1.0)
        anneau.keyframe_insert("color", frame=IMAGE_DEBUT + i)
        halo.location = point_anneau(km)
        halo.keyframe_insert("location", frame=IMAGE_DEBUT + i)
    visible_pendant(halo, INSTANT_LACHER_S, PLANS[-1][2] + 1, image_fin)

    # Caméra visant une cible ; une pose de début et de fin par plan
    donnees_camera = bpy.data.cameras.new("Camera_terre")
    donnees_camera.lens = 35
    donnees_camera.clip_start = 0.01
    camera = objet(scene, "Camera_terre", donnees_camera)
    scene.camera = camera
    cible = objet(scene, "Cible_camera", None)
    suivi = camera.constraints.new("TRACK_TO")
    suivi.target = cible
    suivi.track_axis, suivi.up_axis = "TRACK_NEGATIVE_Z", "UP_Y"

    paris = sph(*PARIS)
    centre = Vector((0.0, 0.0, 0.0))
    poses = {
        "5": ((sph(18, 40, 6.0), centre), (sph(18, 32, 4.3), centre)),
        "6": ((sph(35, 25, 3.0), paris), (sph(40, 14, 1.75), paris)),
        "7": ((sph(40, 14, 1.75), paris), (sph(24, 16, 1.7), point_anneau(2_000))),
        "8": ((sph(22, 16, 2.0), point_anneau(2_000)), (sph(8, 22, 2.6), point_anneau(4_722))),
        "9": ((sph(25, 160, 5.2), centre), (sph(32, 150, 4.9), centre)),
        "11": ((sph(22, 30, 5.6), Vector((0, 0, -0.55))), (sph(22, 26, 5.3), Vector((0, 0, -0.55)))),
    }
    for nom, debut, fin in PLANS:
        (cam0, cib0), (cam1, cib1) = poses[nom]
        cle_pose(camera, cible, IMAGE_DEBUT + round(debut * FPS), cam0, cib0)
        cle_pose(camera, cible, IMAGE_DEBUT + round(fin * FPS) - 1, cam1, cib1)

    # Halo de taille apparente constante, du gros plan au plan large
    for image in range(IMAGE_DEBUT, image_fin + 1):
        scene.frame_set(image)
        halo.scale = [TAILLE_HALO * (camera.location - halo.location).length] * 3
        halo.keyframe_insert("scale", frame=image)
    scene.frame_set(IMAGE_DEBUT)

    # Textes dans le champ de la caméra (à 0,1 unité devant l'objectif)
    mat_texte = materiau_texte()
    depart = texte(scene, "Depart", "Point de départ : Paris\n48,8566° N · 2,3522° E",
                   camera, (0.048, 0.025, -0.1), 0.0026, "RIGHT", mat_texte)
    visible_pendant(depart, 2.5, 4.0, image_fin)
    compteur = texte(scene, "Compteur", "", camera, (0.048, 0.025, -0.1), 0.0026, "RIGHT", mat_texte)
    visible_pendant(compteur, 4.0, 8.0, image_fin)
    n_reel = TOUR_MERIDIEN_KM * 1e3 / (2 * rayon_bille_reel)
    note = texte(scene, "Note", f"Billes agrandies : il en faudrait {n_reel / 1e9:.1f} milliards de "
                 f"{2 * rayon_bille_reel * 1e3:.0f} mm.\nVitesse calculée de l'onde : {vitesse:.0f} m/s.",
                 camera, (-0.049, -0.024, -0.1), 0.0016, "LEFT", mat_texte)
    visible_pendant(note, 4.0, 8.0, image_fin)
    titre = texte(scene, "Titre", "Le choc autour du monde", camera, (0.0, -0.015, -0.1), 0.0055, "CENTER",
                  mat_texte)
    sous_titre = texte(scene, "Sous_titre", "UNE EXPÉRIENCE DE PENSÉE SUR LA PROPAGATION DES ONDES",
                       camera, (0.0, -0.0215, -0.1), 0.0018, "CENTER", mat_texte)
    for obj in (titre, sous_titre):
        visible_pendant(obj, 8.4, duree + 1, image_fin)

    # Compteur mis à jour à chaque image ; le code est rangé dans le .blend
    # (module enregistré) pour fonctionner aussi après réouverture du fichier.
    scene["terre_image_debut"] = IMAGE_DEBUT
    scene["terre_distance_km"] = distance.tolist()
    scene["terre_acceleration"] = acceleration.tolist()
    scene["vitesse_onde_m_s"] = vitesse
    code = bpy.data.texts.get("compteur_choc.py") or bpy.data.texts.new("compteur_choc.py")
    code.from_string(CODE_COMPTEUR)
    code.use_module = True
    exec(compile(CODE_COMPTEUR, "compteur_choc.py", "exec"), {"__name__": "compteur_choc"})

    couche = scene.view_layers[0]
    couche.use_pass_emit = True
    if NOM_AOV not in couche.aovs:
        aov = couche.aovs.add()
        aov.name = NOM_AOV
        aov.type = "VALUE"

    print(f"Scène « {NOM_SCENE} » : images {IMAGE_DEBUT} à {image_fin} ({FPS} i/s)")
    print(f"Vitesse de l'onde : {vitesse:.0f} m/s ; tour complet en "
          f"{TOUR_MERIDIEN_KM * 1e3 / vitesse / 3600:.1f} h réelles")
    en_mouvement = acceleration[acceleration > 0]
    print(f"Accéléré : ×{en_mouvement.min():,.0f} à ×{en_mouvement.max():,.0f}")


if __name__ == "__main__":
    main()
