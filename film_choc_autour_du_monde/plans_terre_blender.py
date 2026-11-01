"""Le tour du monde de « Le choc autour du monde », pour Blender.

À exécuter depuis Blender (onglet Scripting > Ouvrir > Exécuter le script),
le fichier .blend étant enregistré à côté des dossiers « donnees_choc » et
« textures », ou :

    blender scene.blend --python plans_terre_blender.py -- \
        --donnees chemin/donnees_choc --textures chemin/textures

Crée (ou recrée) la scène « Choc_Terre » : la Terre (jour, nuit, nuages,
relief, frontières), une chaîne de billes le long du méridien de Paris,
l'impulsion qui en fait le tour, et une caméra qui la suit d'un seul
mouvement en zoomant sur chaque pays traversé.

Ce qui vient des calculs :
  - la vitesse de l'onde (simuler_chaine.py → meta.json) ;
  - les pays et les mers traversés, avec leurs distances
    (preparer_pays.py → textures/pays_meridien.json et contours_pays.json) ;
  - la course du Soleil : il tourne de 15° par heure de temps réel.
Ce qui est de la mise en scène, et que les textes affichés disent :
  - la distance avance en accéléré ; le temps réel affiché vaut toujours
    distance / vitesse calculée, et « Accéléré » est le facteur de l'image ;
  - les billes sont agrandies, la lueur et le halo repèrent l'impulsion.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

# --- Réglages de mise en scène : aucun ne modifie la physique ---------------
DOSSIER_DONNEES = "//donnees_choc"
DOSSIER_TEXTURES = "//textures"
IMAGE_DEBUT = 1
FPS = 24
DUREE_S = 24.0  # dont 4 s de plan final, avec le titre
FIN_VOYAGE_S = 20.0
INSTANT_LACHER_S = 3.0

# Distance parcourue (km) à différents instants (s). Les distances sont celles
# des frontières (pays_meridien.json) : la caméra arrive sur chaque pays au
# moment où l'impulsion y entre. Le Burkina Faso (15 km) est ralenti pour
# rester lisible.
CLES_DISTANCE = [
    (3.0, 0), (4.5, 718), (5.4, 1_358), (7.4, 3_193), (8.3, 3_728),
    (8.7, 4_090), (9.2, 4_130), (10.0, 4_726), (11.8, 13_313), (13.0, 16_053),
    (14.8, 32_102), (15.6, 32_707), (16.3, 33_028), (18.0, 39_764), (19.0, 40_008),
]

# Caméra : altitude (rayons terrestres), inclinaison (° depuis la verticale)
# et roulis (tours) à différents instants. Le roulis retourne l'image au-dessus
# des pôles pour que le nord reste en haut sur les pays.
CLES_ALTITUDE = [
    (0.0, 3.4), (2.4, 0.30), (3.0, 0.24), (4.5, 0.20), (5.4, 0.30), (7.4, 0.36),
    (8.7, 0.24), (9.6, 0.26), (10.4, 1.1), (11.2, 1.7), (12.2, 0.75), (13.2, 1.0),
    (14.0, 2.3), (14.9, 0.55), (15.7, 0.32), (16.4, 0.8), (17.2, 1.3), (18.1, 0.30),
    (19.0, 0.24), (20.0, 0.21), (21.0, 0.5), (24.0, 3.0),
]
CLES_INCLINAISON = [(0.0, 0), (2.4, 30), (10.0, 35), (11.0, 10), (14.0, 5), (15.2, 35),
                    (16.6, 15), (17.6, 20), (18.4, 32), (20.0, 34), (21.5, 15), (24.0, 0)]
CLES_ROULIS = [(0.0, 0.0), (13.4, 0.0), (14.6, 0.5), (16.8, 0.5), (17.8, 1.0)]

RAYON_ANNEAU = 1.025  # en rayons terrestres
BILLES_VISIBLES = 600
INTENSITE_LUEUR = 12.0
INTENSITE_HALO = 2.5
TAILLE_HALO = 0.02  # rayon du halo par unité de distance à la caméra
COULEUR_LUEUR = (0.15, 0.45, 1.0, 1.0)
COULEUR_PAYS = (1.0, 0.72, 0.30, 1.0)
LARGEUR_LUEUR = 0.003  # fraction du tour (≈ 120 km)
SOLEIL_LONGITUDE_DEPART = 20.0  # point subsolaire au départ (équinoxe)

NOM_SCENE = "Choc_Terre"
NOM_AOV = "lueur"

TOUR_MERIDIEN_KM = 40_008.0
PARIS = (48.8566, 2.3522)

CODE_TEXTES = '''import json

import bpy


def _milliers(x):
    return f"{x:,.0f}".replace(",", " ")


def _heure(km, vitesse):
    minutes = round(km * 1000 / vitesse / 60)
    return f"{minutes // 60} h {minutes % 60:02d}"


def maj_textes_choc(scene, *args):
    distances = scene.get("terre_distance_km")
    if distances is None:
        return
    i = min(max(scene.frame_current - scene["terre_image_debut"], 0), len(distances) - 1)
    km = distances[i]
    vitesse = scene["vitesse_onde_m_s"]
    tour = scene["tour_km"]
    objets = bpy.data.objects
    if "Compteur" in objets:
        acceleration = scene["terre_acceleration"][i]
        objets["Compteur"].data.body = (
            f"{_milliers(km)} km\\n{_heure(km, vitesse)} de temps réel\\n"
            + (f"accéléré ×{_milliers(acceleration)}" if acceleration >= 1 else "arrivée")
        )
    if "Cartouche_nom" not in objets:
        return
    if i < scene["terre_image_lacher"]:
        nom, info = "PARIS", "48,8566° N · 2,3522° E · point de départ"
    elif km >= tour - 0.5:
        nom, info = "RETOUR À PARIS", f"{_milliers(tour)} km · {_heure(tour, vitesse)} après le départ"
    else:
        etape = next(t for t in json.loads(scene["traversees_json"]) if t["km_entree"] <= km < t["km_sortie"])
        nom = etape["nom"].upper()
        info = (f"{_milliers(etape['duree_km'])} km traversés · "
                f"entrée {_heure(etape['km_entree'], vitesse)} après le départ")
    objets["Cartouche_nom"].data.body = nom
    objets["Cartouche_info"].data.body = info


for _h in [h for h in bpy.app.handlers.frame_change_pre if h.__name__ == "maj_textes_choc"]:
    bpy.app.handlers.frame_change_pre.remove(_h)
bpy.app.handlers.frame_change_pre.append(maj_textes_choc)
'''


def lire_arguments():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="plans_terre_blender.py")
    p.add_argument("--donnees", default=DOSSIER_DONNEES, help="dossier écrit par simuler_chaine.py")
    p.add_argument("--textures", default=DOSSIER_TEXTURES, help="dossier des textures et des pays")
    args, _ = p.parse_known_args(argv)
    return args


def chemin(texte):
    if texte.startswith("//") and not bpy.data.filepath:
        raise RuntimeError("Enregistrez le fichier .blend ou passez des chemins absolus.")
    return Path(bpy.path.abspath(texte))


def sph(lat, lon, rayon=1.0):
    lat, lon = math.radians(lat), math.radians(lon)
    return Vector((math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat))) * rayon


def point_anneau(km, rayon=RAYON_ANNEAU):
    """Point du tour à `km` de Paris, en descendant le méridien de Paris."""
    theta = math.radians(PARIS[0]) - km / TOUR_MERIDIEN_KM * 2 * math.pi
    lon = math.radians(PARIS[1])
    return Vector((math.cos(theta) * math.cos(lon), math.cos(theta) * math.sin(lon), math.sin(theta))) * rayon


def tangente_anneau(km):
    """Direction de marche de l'impulsion à `km` de Paris."""
    return (point_anneau(km + 1.0, 1.0) - point_anneau(km - 1.0, 1.0)).normalized()


def pchip(x, y, xi):
    """Interpolation cubique monotone (Fritsch-Carlson) : pas de recul, pas
    d'arrêt aux points de passage, pas de dépassement entre deux clés."""
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


def courbe(cles, temps):
    t, v = zip(*cles)
    return pchip(t, v, temps)


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


def melange(arbre, facteur, a, b):
    """a·(1 - facteur) + b·facteur, sur des valeurs."""
    return math_noeud(arbre, "ADD", a if not isinstance(a, (int, float)) else math_noeud(arbre, "ADD", a, 0.0),
                      math_noeud(arbre, "MULTIPLY", facteur, math_noeud(arbre, "SUBTRACT", b, a)))


def prise(noeud, identifiant, sortie=False):
    """Prise d'un nœud Mix par identifiant (« A_Color »…) : plusieurs prises
    portent le même nom selon le type de données."""
    prises = noeud.outputs if sortie else noeud.inputs
    return next(p for p in prises if p.identifier == identifiant)


def nouveau_materiau(nom):
    ancien = bpy.data.materials.get(nom)
    if ancien is not None:
        bpy.data.materials.remove(ancien)
    materiau = bpy.data.materials.new(nom)
    if bpy.app.version < (5, 0, 0):
        materiau.use_nodes = True
    materiau.node_tree.nodes.clear()
    return materiau, materiau.node_tree


def texture(arbre, dossier, nom, vecteur, non_couleur=False, interpolation="Linear"):
    fichier = dossier / nom
    if not fichier.exists():
        print(f"Texture absente : {fichier}")
        return None
    noeud = arbre.nodes.new("ShaderNodeTexImage")
    noeud.image = bpy.data.images.load(str(fichier), check_existing=True)
    if non_couleur:
        noeud.image.colorspace_settings.name = "Non-Color"
    noeud.interpolation = interpolation
    arbre.links.new(vecteur, noeud.inputs["Vector"])
    return noeud


def materiau_terre(dossier, repere_soleil):
    """Jour, nuit, eau brillante, relief, frontières et pays traversé en cours.

    Couleur d'objet : R = identifiant du pays en cours (pays_id.png),
    G = intensité de sa mise en valeur."""
    materiau, arbre = nouveau_materiau("Terre_choc")
    n, l = arbre.nodes, arbre.links
    sortie = n.new("ShaderNodeOutputMaterial")
    sol = n.new("ShaderNodeBsdfPrincipled")
    somme = n.new("ShaderNodeAddShader")
    l.new(sol.outputs["BSDF"], somme.inputs[0])
    l.new(somme.outputs["Shader"], sortie.inputs["Surface"])
    uv = n.new("ShaderNodeTexCoord").outputs["UV"]

    jour = texture(arbre, dossier, "terre_jour.jpg", uv)
    if jour is not None:
        l.new(jour.outputs["Color"], sol.inputs["Base Color"])
    else:
        sol.inputs["Base Color"].default_value = (0.02, 0.08, 0.25, 1.0)

    eau = texture(arbre, dossier, "eau.png", uv, non_couleur=True)
    if eau is not None:
        l.new(melange(arbre, eau.outputs["Color"], 0.75, 0.22), sol.inputs["Roughness"])
    else:
        sol.inputs["Roughness"].default_value = 0.65

    relief = texture(arbre, dossier, "relief.png", uv, non_couleur=True)
    if relief is not None:
        bosse = n.new("ShaderNodeBump")
        bosse.inputs["Strength"].default_value = 0.25
        bosse.inputs["Distance"].default_value = 0.002
        l.new(relief.outputs["Color"], bosse.inputs["Height"])
        l.new(bosse.outputs["Normal"], sol.inputs["Normal"])

    # Côté nuit : coordonnée Z dans le repère du Soleil (= cosinus de l'angle
    # au point subsolaire, pour une sphère de rayon 1 centrée sur l'origine)
    repere = n.new("ShaderNodeTexCoord")
    repere.object = repere_soleil
    z_soleil = n.new("ShaderNodeSeparateXYZ")
    l.new(repere.outputs["Object"], z_soleil.inputs[0])
    nuit = n.new("ShaderNodeMapRange")
    nuit.inputs["From Min"].default_value = -0.08
    nuit.inputs["From Max"].default_value = 0.12
    nuit.inputs["To Min"].default_value = 1.0
    nuit.inputs["To Max"].default_value = 0.0
    l.new(z_soleil.outputs["Z"], nuit.inputs["Value"])
    masque_nuit = nuit.outputs["Result"]

    emission = n.new("ShaderNodeEmission")
    l.new(emission.outputs["Emission"], somme.inputs[1])
    couleur = n.new("ShaderNodeMix")
    couleur.data_type = "RGBA"
    villes = texture(arbre, dossier, "terre_nuit.jpg", uv)

    # Pays traversé en cours, et frontières de tous les pays
    info = n.new("ShaderNodeObjectInfo")
    canaux = n.new("ShaderNodeSeparateColor")
    l.new(info.outputs["Color"], canaux.inputs["Color"])
    ident = texture(arbre, dossier, "pays_id.png", uv, non_couleur=True, interpolation="Closest")
    if ident is not None:
        ecart = math_noeud(arbre, "ABSOLUTE", math_noeud(arbre, "SUBTRACT", ident.outputs["Color"], canaux.outputs[0]))
        dans_pays = math_noeud(arbre, "MULTIPLY", math_noeud(arbre, "LESS_THAN", ecart, 0.002),
                               math_noeud(arbre, "GREATER_THAN", ident.outputs["Color"], 0.001))
        pays_actif = math_noeud(arbre, "MULTIPLY", dans_pays, canaux.outputs[1])
    else:
        pays_actif = math_noeud(arbre, "MULTIPLY", 0.0, 0.0)
    frontieres = texture(arbre, dossier, "frontieres.png", uv, non_couleur=True)
    trait = frontieres.outputs["Alpha"] if frontieres is not None else math_noeud(arbre, "MULTIPLY", 0.0, 0.0)

    # Émission = villes la nuit + voile doré du pays en cours + frontières
    voile = math_noeud(arbre, "MULTIPLY", pays_actif, 0.06)
    lignes = math_noeud(arbre, "MULTIPLY", trait, 0.10)
    l.new(math_noeud(arbre, "ADD", voile, lignes), prise(couleur, "Factor_Float"))
    if villes is not None:
        lumieres = n.new("ShaderNodeMix")
        lumieres.data_type = "RGBA"
        lumieres.blend_type = "MULTIPLY"
        prise(lumieres, "Factor_Float").default_value = 1.0
        l.new(villes.outputs["Color"], prise(lumieres, "A_Color"))
        l.new(masque_nuit, prise(lumieres, "B_Color"))
        l.new(prise(lumieres, "Result_Color", sortie=True), prise(couleur, "A_Color"))
    else:
        prise(couleur, "A_Color").default_value = (0.0, 0.0, 0.0, 1.0)
    prise(couleur, "B_Color").default_value = COULEUR_PAYS
    l.new(prise(couleur, "Result_Color", sortie=True), emission.inputs["Color"])
    l.new(math_noeud(arbre, "ADD", math_noeud(arbre, "MULTIPLY", masque_nuit, 1.5),
                     math_noeud(arbre, "MULTIPLY", math_noeud(arbre, "ADD", voile, lignes), 6.0)),
          emission.inputs["Strength"])
    return materiau


def materiau_nuages(dossier):
    materiau, arbre = nouveau_materiau("Nuages_choc")
    n, l = arbre.nodes, arbre.links
    sortie = n.new("ShaderNodeOutputMaterial")
    blanc = n.new("ShaderNodeBsdfDiffuse")
    blanc.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    transparent = n.new("ShaderNodeBsdfTransparent")
    mix = n.new("ShaderNodeMixShader")
    nuages = texture(arbre, dossier, "nuages.jpg", n.new("ShaderNodeTexCoord").outputs["UV"], non_couleur=True)
    if nuages is not None:
        l.new(math_noeud(arbre, "MULTIPLY", nuages.outputs["Color"], 0.6), mix.inputs["Fac"])
    else:
        mix.inputs["Fac"].default_value = 0.0
    l.new(transparent.outputs["BSDF"], mix.inputs[1])
    l.new(blanc.outputs["BSDF"], mix.inputs[2])
    l.new(mix.outputs["Shader"], sortie.inputs["Surface"])
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
    mix = n.new("ShaderNodeMixShader")
    l.new(math_noeud(arbre, "POWER", poids.outputs["Facing"], 5.0), mix.inputs["Fac"])
    l.new(transparent.outputs["BSDF"], mix.inputs[1])
    l.new(halo.outputs["Emission"], mix.inputs[2])
    l.new(mix.outputs["Shader"], sortie.inputs["Surface"])
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
    mix = n.new("ShaderNodeMixShader")
    l.new(coeur, mix.inputs["Fac"])
    l.new(transparent.outputs["BSDF"], mix.inputs[1])
    l.new(emission.outputs["Emission"], mix.inputs[2])
    l.new(mix.outputs["Shader"], sortie.inputs["Surface"])
    aov = n.new("ShaderNodeOutputAOV")
    aov.aov_name = NOM_AOV
    l.new(coeur, aov.inputs["Value"])
    return materiau


def materiau_emission(nom, couleur, force):
    """Émission dont la force est multipliée par le canal R de la couleur d'objet."""
    materiau, arbre = nouveau_materiau(nom)
    emission = arbre.nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = couleur
    info = arbre.nodes.new("ShaderNodeObjectInfo")
    canaux = arbre.nodes.new("ShaderNodeSeparateColor")
    arbre.links.new(info.outputs["Color"], canaux.inputs["Color"])
    arbre.links.new(math_noeud(arbre, "MULTIPLY", canaux.outputs[0], force), emission.inputs["Strength"])
    sortie = arbre.nodes.new("ShaderNodeOutputMaterial")
    arbre.links.new(emission.outputs["Emission"], sortie.inputs["Surface"])
    return materiau


def materiau_contour():
    """Trait doré dont l'éclat suit le canal R de la couleur d'objet ;
    transparent quand il est éteint."""
    materiau, arbre = nouveau_materiau("Contour_choc")
    n, l = arbre.nodes, arbre.links
    info = n.new("ShaderNodeObjectInfo")
    canaux = n.new("ShaderNodeSeparateColor")
    l.new(info.outputs["Color"], canaux.inputs["Color"])
    emission = n.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = COULEUR_PAYS
    emission.inputs["Strength"].default_value = 4.0
    transparent = n.new("ShaderNodeBsdfTransparent")
    mix = n.new("ShaderNodeMixShader")
    l.new(canaux.outputs[0], mix.inputs["Fac"])
    l.new(transparent.outputs["BSDF"], mix.inputs[1])
    l.new(emission.outputs["Emission"], mix.inputs[2])
    sortie = n.new("ShaderNodeOutputMaterial")
    l.new(mix.outputs["Shader"], sortie.inputs["Surface"])
    return materiau


def monde_etoile(scene):
    monde = bpy.data.worlds.get("Ciel_choc") or bpy.data.worlds.new("Ciel_choc")
    if bpy.app.version < (5, 0, 0):
        monde.use_nodes = True
    arbre = monde.node_tree
    arbre.nodes.clear()
    coord = arbre.nodes.new("ShaderNodeTexCoord")
    voronoi = arbre.nodes.new("ShaderNodeTexVoronoi")
    voronoi.inputs["Scale"].default_value = 250.0
    arbre.links.new(coord.outputs["Generated"], voronoi.inputs["Vector"])
    etoiles = math_noeud(arbre, "MULTIPLY", math_noeud(arbre, "LESS_THAN", voronoi.outputs["Distance"], 0.04), 0.5)
    fond = arbre.nodes.new("ShaderNodeBackground")
    fond.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    arbre.links.new(math_noeud(arbre, "ADD", etoiles, 0.002), fond.inputs["Strength"])
    sortie = arbre.nodes.new("ShaderNodeOutputWorld")
    arbre.links.new(fond.outputs["Background"], sortie.inputs["Surface"])
    scene.world = monde


# --- Géométrie ---------------------------------------------------------------

def maillage_sphere(nom, rayon, n_lon=256, n_lat=128):
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


def courbe_contour(nom, anneaux, rayon=1.0015):
    """Contour d'un pays posé sur le globe, tracé progressivement à l'animation."""
    donnees = bpy.data.curves.new(nom, "CURVE")
    donnees.dimensions = "3D"
    donnees.bevel_depth = 0.0006
    donnees.bevel_resolution = 0
    donnees.bevel_factor_mapping_end = "SPLINE"
    for anneau in anneaux:
        # Spline ouverte refermée par son premier point : le facteur de biseau,
        # qui fait apparaître le tracé, n'agit pas sur une spline cyclique.
        anneau = list(anneau) + [anneau[0]]
        spline = donnees.splines.new("POLY")
        spline.points.add(len(anneau) - 1)
        coords = []
        for lon, lat in anneau:
            coords.extend((*sph(lat, lon, rayon), 1.0))
        spline.points.foreach_set("co", coords)
    return donnees


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
    courbe_texte = bpy.data.curves.new(nom, "FONT")
    courbe_texte.body = contenu
    courbe_texte.size = taille
    courbe_texte.align_x = alignement
    obj = objet(scene, nom, courbe_texte, materiau)
    obj.parent = camera
    obj.location = position
    obj.visible_shadow = False
    return obj


def visible_entre(obj, debut, fin, image_fin):
    """Affiche l'objet entre deux images seulement."""
    for image, cache in ((IMAGE_DEBUT, True), (debut, False), (fin, True)):
        if IMAGE_DEBUT <= image <= image_fin:
            obj.hide_render = obj.hide_viewport = cache
            obj.keyframe_insert("hide_render", frame=image)
            obj.keyframe_insert("hide_viewport", frame=image)


def regarder(position, cible, haut):
    """Quaternion d'une caméra en `position` qui vise `cible`, `haut` vers le haut de l'image."""
    avant = (cible - position).normalized()
    droite = avant.cross(haut).normalized()
    dessus = droite.cross(avant)
    return Matrix((droite, dessus, -avant)).transposed().to_quaternion()


def main():
    args = lire_arguments()
    dossier = chemin(args.donnees)
    dossier_textures = chemin(args.textures)
    meta = json.loads((dossier / "meta.json").read_text(encoding="utf-8"))
    vitesse = meta["chaine"]["vitesse_onde_m_s"]
    rayon_bille_reel = meta["parametres"]["rayon_m"]
    pays = json.loads((dossier_textures / "pays_meridien.json").read_text(encoding="utf-8"))
    contours = json.loads((dossier_textures / "contours_pays.json").read_text(encoding="utf-8"))
    traversees = pays["traversees"]

    scene = preparer_scene()
    scene.render.fps = FPS
    image_fin = IMAGE_DEBUT + round(DUREE_S * FPS) - 1
    scene.frame_start, scene.frame_end = IMAGE_DEBUT, image_fin
    monde_etoile(scene)

    temps = np.arange(image_fin - IMAGE_DEBUT + 1) / FPS
    t_cles, km_cles = zip(*CLES_DISTANCE)
    distance = np.where(temps < t_cles[0], 0.0, pchip(t_cles, km_cles, temps))
    acceleration = np.gradient(distance, temps) * 1000 / vitesse
    image_lacher = round(INSTANT_LACHER_S * FPS)

    # Soleil : 15° par heure de temps réel, vers l'ouest
    heures = distance * 1000 / vitesse / 3600
    repere_soleil = objet(scene, "Repere_soleil", None)
    soleil = objet(scene, "Soleil", bpy.data.lights.new("Soleil", "SUN"))
    soleil.data.energy = 4.0
    soleil.data.angle = math.radians(0.53)
    for i, h in enumerate(heures):
        direction = sph(0.0, SOLEIL_LONGITUDE_DEPART - 15.0 * h)
        rotation = direction.to_track_quat("Z", "Y").to_euler()
        repere_soleil.rotation_euler = rotation
        repere_soleil.keyframe_insert("rotation_euler", frame=IMAGE_DEBUT + i)
        soleil.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
        soleil.keyframe_insert("rotation_euler", frame=IMAGE_DEBUT + i)

    terre = objet(scene, "Terre", maillage_sphere("Terre", 1.0, 512, 256),
                  materiau_terre(dossier_textures, repere_soleil))
    nuages = objet(scene, "Nuages", maillage_sphere("Nuages", 1.006, 256, 128), materiau_nuages(dossier_textures))
    nuages.visible_shadow = False
    atmosphere = objet(scene, "Atmosphere", maillage_sphere("Atmosphere", 1.015, 128, 64), materiau_atmosphere())
    atmosphere.visible_shadow = False
    anneau = objet(scene, "Chaine_terrestre", maillage_anneau("Chaine_terrestre", BILLES_VISIBLES, RAYON_ANNEAU),
                   materiau_anneau())
    halo = objet(scene, "Halo_front", maillage_sphere("Halo_front", 1.0, 32, 16), materiau_halo())
    halo.visible_shadow = False

    # Pays en cours (pour la Terre) : identifiant et intensité à chaque image
    def etape(km):
        return next((t for t in traversees if t["km_entree"] <= km < t["km_sortie"]), traversees[-1])

    dernier_id, intensite = 0.0, 0.0
    for i, km in enumerate(distance):
        t = etape(km)
        if i >= image_lacher and t["terre"]:
            dernier_id, intensite = t["identifiant"] / 255, min(1.0, intensite + 0.15)
        else:
            intensite = max(0.0, intensite - 0.05)
        terre.color = (dernier_id, intensite, 0.0, 1.0)
        terre.keyframe_insert("color", frame=IMAGE_DEBUT + i)
        anneau.color = (km / TOUR_MERIDIEN_KM, 1.0 if i >= image_lacher else 0.0, 0.0, 1.0)
        anneau.keyframe_insert("color", frame=IMAGE_DEBUT + i)

    # Contours lumineux : chaque pays se dessine à l'entrée de l'impulsion,
    # brille pendant la traversée puis reste en filigrane.
    mat_contour = materiau_contour()
    for nom_ne, anneaux in contours.items():
        passages = [t for t in traversees if t.get("nom_natural_earth") == nom_ne]
        proches = [a for a in anneaux if any(
            math.degrees(sph(a[0][1], a[0][0]).angle(sph(t["lat_milieu"], t["lon_milieu"]))) < 35
            or len(a) > 2000 for t in passages)]
        if not proches:
            continue
        contour = objet(scene, f"Contour_{nom_ne}", courbe_contour(f"Contour_{nom_ne}", proches), mat_contour)
        contour.visible_shadow = False
        contour.color = (0.0, 0.0, 0.0, 1.0)
        contour.keyframe_insert("color", frame=IMAGE_DEBUT)
        contour.data.bevel_factor_end = 0.0
        contour.data.keyframe_insert("bevel_factor_end", frame=IMAGE_DEBUT)
        for rang, t in enumerate(passages):
            entree = IMAGE_DEBUT + max(image_lacher, int(np.searchsorted(distance, t["km_entree"])))
            sortie = IMAGE_DEBUT + int(np.searchsorted(distance, t["km_sortie"]))
            if rang == 0:  # le contour se dessine au premier passage seulement
                contour.data.bevel_factor_end = 0.0
                contour.data.keyframe_insert("bevel_factor_end", frame=max(IMAGE_DEBUT, entree - 1))
                contour.data.bevel_factor_end = 1.0
                contour.data.keyframe_insert("bevel_factor_end", frame=entree + 12)
            filigrane = 0.0 if rang == 0 else 0.25
            for image, force in ((entree - 1, filigrane), (entree, 1.0), (max(entree + 1, sortie), 1.0),
                                 (max(entree + 1, sortie) + 18, 0.25)):
                contour.color = (force, 0.0, 0.0, 1.0)
                contour.keyframe_insert("color", frame=image)

    # Caméra : un seul mouvement qui suit l'impulsion
    donnees_camera = bpy.data.cameras.new("Camera_terre")
    donnees_camera.lens = 35
    donnees_camera.clip_start = 0.005
    camera = objet(scene, "Camera_terre", donnees_camera)
    camera.rotation_mode = "QUATERNION"
    scene.camera = camera
    altitude = np.exp(courbe([(t, math.log(a)) for t, a in CLES_ALTITUDE], temps))
    inclinaison = np.radians(courbe(CLES_INCLINAISON, temps))
    roulis = courbe(CLES_ROULIS, temps) * 2 * math.pi
    precedent = None
    positions_camera = []
    for i in range(len(temps)):
        km = distance[i]
        sol = point_anneau(km, 1.0)
        recul = -tangente_anneau(km)  # le nord sur le méridien de Paris
        cote = recul.cross(sol)
        haut = (recul * math.cos(roulis[i]) + cote * math.sin(roulis[i])).normalized()
        position = sol * (1 + altitude[i] * math.cos(inclinaison[i])) - haut * altitude[i] * math.sin(inclinaison[i])
        cible = sol.lerp(Vector((0, 0, 0)), min(0.8, max(0.0, (altitude[i] - 0.5) / 2.0)))
        rotation = regarder(position, cible, haut)
        if precedent is not None and precedent.dot(rotation) < 0:
            rotation.negate()
        precedent = rotation
        positions_camera.append(position)
        camera.location = position
        camera.rotation_quaternion = rotation
        camera.keyframe_insert("location", frame=IMAGE_DEBUT + i)
        camera.keyframe_insert("rotation_quaternion", frame=IMAGE_DEBUT + i)

    # Halo de taille apparente constante, avec un éclat au lâcher et au retour
    image_retour = int(np.searchsorted(distance, TOUR_MERIDIEN_KM - 1))
    for i, km in enumerate(distance):
        halo.location = point_anneau(km)
        eclat = (1.0 + 2.5 * math.exp(-((i - image_lacher) / 6) ** 2)
                 + 2.5 * math.exp(-((i - image_retour) / 8) ** 2))
        halo.scale = [TAILLE_HALO * eclat * (positions_camera[i] - halo.location).length] * 3
        halo.keyframe_insert("location", frame=IMAGE_DEBUT + i)
        halo.keyframe_insert("scale", frame=IMAGE_DEBUT + i)
    visible_entre(halo, IMAGE_DEBUT + image_lacher, image_fin + 1, image_fin)

    # Textes dans le champ de la caméra (à 0,1 unité devant l'objectif)
    mat_texte = materiau_emission("Texte_choc", (1.0, 1.0, 1.0, 1.0), 1.5)
    mat_texte_dore = materiau_emission("Texte_dore_choc", COULEUR_PAYS, 2.0)
    textes = [
        texte(scene, "Compteur", "", camera, (0.048, 0.025, -0.1), 0.0024, "RIGHT", mat_texte),
        texte(scene, "Cartouche_nom", "", camera, (-0.049, -0.0195, -0.1), 0.0055, "LEFT", mat_texte_dore),
        texte(scene, "Cartouche_info", "", camera, (-0.049, -0.0245, -0.1), 0.0019, "LEFT", mat_texte),
    ]
    n_reel = TOUR_MERIDIEN_KM * 1e3 / (2 * rayon_bille_reel)
    textes.append(texte(scene, "Note", f"Billes agrandies : il en faudrait {n_reel / 1e9:.1f} milliards de "
                        f"{2 * rayon_bille_reel * 1e3:.0f} mm.\nVitesse calculée de l'onde : {vitesse:.0f} m/s.",
                        camera, (0.048, -0.0245, -0.1), 0.0014, "RIGHT", mat_texte))
    for obj in textes:
        obj.color = (1.0, 0.0, 0.0, 1.0)
    fin_voyage = IMAGE_DEBUT + round(FIN_VOYAGE_S * FPS)
    visible_entre(textes[0], IMAGE_DEBUT + image_lacher, fin_voyage, image_fin)
    visible_entre(textes[3], IMAGE_DEBUT + image_lacher, fin_voyage, image_fin)
    visible_entre(textes[1], IMAGE_DEBUT + round(1.6 * FPS), fin_voyage, image_fin)
    visible_entre(textes[2], IMAGE_DEBUT + round(1.6 * FPS), fin_voyage, image_fin)

    # Plan final : la caméra s'éloigne de Paris, le titre apparaît
    titres = [
        texte(scene, "Titre", "Le choc autour du monde", camera, (0.0, -0.013, -0.1), 0.0062, "CENTER",
              mat_texte),
        texte(scene, "Sous_titre", "UNE EXPÉRIENCE DE PENSÉE SUR LA PROPAGATION DES ONDES", camera,
              (0.0, -0.0185, -0.1), 0.0018, "CENTER", mat_texte),
        texte(scene, "Bilan", f"{TOUR_MERIDIEN_KM:,.0f} km · {TOUR_MERIDIEN_KM * 1e3 / vitesse / 3600:.0f} h "
              f"{TOUR_MERIDIEN_KM * 1e3 / vitesse / 60 % 60:02.0f} · {vitesse:.0f} m/s".replace(",", " "),
              camera, (0.0, -0.0235, -0.1), 0.0019, "CENTER", mat_texte_dore),
    ]
    for rang, obj in enumerate(titres):
        obj.color = (1.0, 0.0, 0.0, 1.0)
        visible_entre(obj, fin_voyage + 12 + 10 * rang, image_fin + 1, image_fin)

    # Textes mis à jour à chaque image ; le code est rangé dans le .blend
    # (module enregistré) pour fonctionner aussi après réouverture du fichier.
    scene["terre_image_debut"] = IMAGE_DEBUT
    scene["terre_image_lacher"] = image_lacher
    scene["terre_distance_km"] = distance.tolist()
    scene["terre_acceleration"] = acceleration.tolist()
    scene["vitesse_onde_m_s"] = vitesse
    scene["tour_km"] = TOUR_MERIDIEN_KM
    scene["traversees_json"] = json.dumps(traversees, ensure_ascii=False)
    code = bpy.data.texts.get("textes_choc.py") or bpy.data.texts.new("textes_choc.py")
    code.from_string(CODE_TEXTES)
    code.use_module = True
    exec(compile(CODE_TEXTES, "textes_choc.py", "exec"), {"__name__": "textes_choc"})

    couche = scene.view_layers[0]
    couche.use_pass_emit = True
    if NOM_AOV not in couche.aovs:
        aov = couche.aovs.add()
        aov.name = NOM_AOV
        aov.type = "VALUE"

    en_mouvement = acceleration[acceleration > 0]
    print(f"Scène « {NOM_SCENE} » : images {IMAGE_DEBUT} à {image_fin} ({FPS} i/s)")
    print(f"Vitesse de l'onde : {vitesse:.0f} m/s ; tour complet en "
          f"{TOUR_MERIDIEN_KM * 1e3 / vitesse / 3600:.1f} h réelles")
    print(f"Accéléré : ×{en_mouvement.min():,.0f} à ×{en_mouvement.max():,.0f}")


if __name__ == "__main__":
    main()
