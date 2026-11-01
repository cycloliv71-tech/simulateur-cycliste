#!/usr/bin/env python3
"""Pays traversés par la chaîne de billes autour du méridien de Paris.

Lit les frontières Natural Earth (TopoJSON du paquet npm world-atlas,
domaine public) et calcule, le long du grand cercle qui passe par Paris
et les deux pôles :
  - les pays et les mers traversés, avec la distance d'entrée et de sortie
    depuis Paris en partant vers le sud ;
  - l'heure d'arrivée de l'impulsion, à la vitesse calculée par
    simuler_chaine.py (meta.json).

Écrit pays_meridien.json, contours_pays.json (contours des pays traversés,
pour les tracer en 3D) et deux textures équirectangulaires pour Blender :
pays_id.png (un niveau de gris par pays traversé, 0 ailleurs) et
frontieres.png (toutes les frontières, en blanc sur fond transparent).

Usage :
    npm pack world-atlas@2.0.2 && tar xzf world-atlas-2.0.2.tgz
    python3 preparer_pays.py --topojson package/countries-10m.json \\
        --meta donnees_choc/meta.json --sortie textures
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

PARIS = (48.8566, 2.3522)
TOUR_MERIDIEN_KM = 40_008.0
PAS_KM = 1.0

# Noms français des pays que le méridien peut traverser (Natural Earth → français)
NOMS = {
    "France": "France",
    "Spain": "Espagne",
    "Algeria": "Algérie",
    "Mali": "Mali",
    "Niger": "Niger",
    "Burkina Faso": "Burkina Faso",
    "Benin": "Bénin",
    "Togo": "Togo",
    "Antarctica": "Antarctique",
    "Fiji": "Fidji",
    "Tonga": "Tonga",
    "Russia": "Russie",
    "United Kingdom": "Royaume-Uni",
    "Belgium": "Belgique",
}

# Étendues d'eau le long du tour : (côté du globe, latitude min, latitude max, nom).
# « paris » = méridien de Paris, « anti » = antiméridien (180° plus loin).
MERS = [
    ("paris", 35, 44, "Mer Méditerranée"),
    ("paris", -60, 35, "Océan Atlantique"),
    ("paris", -90, -60, "Océan Austral"),
    ("anti", -90, -60, "Océan Austral"),
    ("anti", -60, 60, "Océan Pacifique"),
    ("anti", 60, 66, "Mer de Béring"),
    ("anti", 66, 72, "Mer des Tchouktches"),
    ("anti", 72, 90, "Océan Arctique"),
    ("paris", 72, 90, "Océan Arctique"),
    ("paris", 62, 72, "Mer de Norvège"),
    ("paris", 44, 62, "Mer du Nord"),
]


def decoder_topojson(chemin):
    """TopoJSON → liste de (nom, [polygones]) ; un polygone = liste d'anneaux
    (tableaux N×2 de longitude, latitude)."""
    topo = json.loads(Path(chemin).read_text(encoding="utf-8"))
    echelle = np.array(topo["transform"]["scale"])
    origine = np.array(topo["transform"]["translate"])
    arcs = [np.cumsum(np.array(a, dtype=float), axis=0) * echelle + origine for a in topo["arcs"]]

    def anneau(indices):
        points = []
        for i in indices:
            arc = arcs[i] if i >= 0 else arcs[~i][::-1]
            points.append(arc if not points else arc[1:])
        return deplier(np.concatenate(points))

    pays = []
    for g in topo["objects"]["countries"]["geometries"]:
        if g["type"] == "Polygon":
            polygones = [g["arcs"]]
        elif g["type"] == "MultiPolygon":
            polygones = g["arcs"]
        else:
            continue
        pays.append((g["properties"]["name"], [[anneau(r) for r in p] for p in polygones]))
    return pays


def deplier(ring):
    """Rend la longitude continue le long d'un anneau qui franchit
    l'antiméridien (îles à cheval, Tchoukotka). Un anneau qui fait le tour
    complet d'un pôle (Antarctique) est refermé en passant par ce pôle.
    L'anneau déplié peut sortir de [-180, 180] : les tests et le tracé le
    reprennent décalé de ±360°."""
    lon = np.degrees(np.unwrap(np.radians(ring[:, 0])))
    lat = ring[:, 1]
    if abs(lon[-1] - lon[0]) > 180:
        pole = 90.0 if lat.mean() > 0 else -90.0
        lon = np.concatenate([lon, [lon[-1], lon[0]]])
        lat = np.concatenate([lat, [pole, pole]])
    return np.column_stack([lon, lat])


DECALAGES = (-360.0, 0.0, 360.0)


def dans_anneau(lon, lat, ring):
    """Test du rayon (pair-impair), vectorisé sur les points."""
    x, y = ring[:, 0], ring[:, 1]
    x2, y2 = np.roll(x, -1), np.roll(y, -1)
    dedans = np.zeros(len(lon), dtype=bool)
    for xa, ya, xb, yb in zip(x, y, x2, y2):
        croise = (ya > lat) != (yb > lat)
        if not croise.any():
            continue
        xi = xa + (lat - ya) * (xb - xa) / np.where(yb != ya, yb - ya, 1.0)
        dedans ^= croise & (lon < xi)
    return dedans


def dans_pays(lon, lat, polygones):
    resultat = np.zeros(len(lon), dtype=bool)
    for anneaux in polygones:
        exterieur = anneaux[0]
        for decalage in DECALAGES:
            lon_d = lon + decalage
            boite = ((lon_d >= exterieur[:, 0].min()) & (lon_d <= exterieur[:, 0].max())
                     & (lat >= exterieur[:, 1].min()) & (lat <= exterieur[:, 1].max()))
            if not boite.any():
                continue
            idx = np.nonzero(boite)[0]
            dedans = dans_anneau(lon_d[idx], lat[idx], exterieur)
            for trou in anneaux[1:]:
                dedans &= ~dans_anneau(lon_d[idx], lat[idx], trou)
            resultat[idx] |= dedans
    return resultat


def points_du_tour():
    """Latitude et longitude tous les PAS_KM le long du tour, depuis Paris vers le sud."""
    km = np.arange(0.0, TOUR_MERIDIEN_KM, PAS_KM)
    theta = math.radians(PARIS[0]) - km / TOUR_MERIDIEN_KM * 2 * math.pi
    x = np.cos(theta) * math.cos(math.radians(PARIS[1]))
    y = np.cos(theta) * math.sin(math.radians(PARIS[1]))
    z = np.sin(theta)
    lat = np.degrees(np.arcsin(np.clip(z, -1, 1)))
    lon = np.degrees(np.arctan2(y, x))
    return km, lat, lon


def indice_mer(cote, lat):
    for i, (c, lat_min, lat_max, _) in enumerate(MERS):
        if c == cote and lat_min <= lat < lat_max:
            return i
    raise ValueError(f"Aucune mer définie à {lat:.1f}° ({cote})")


def formater_heure(secondes):
    minutes = round(secondes / 60)
    return f"{minutes // 60} h {minutes % 60:02d}"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--topojson", type=Path, required=True, help="countries-10m.json de world-atlas")
    p.add_argument("--meta", type=Path, default=Path("donnees_choc/meta.json"))
    p.add_argument("--sortie", type=Path, default=Path("textures"))
    p.add_argument("--largeur", type=int, default=8192, help="largeur des textures (px)")
    args = p.parse_args()

    vitesse = json.loads(args.meta.read_text(encoding="utf-8"))["chaine"]["vitesse_onde_m_s"]
    pays = decoder_topojson(args.topojson)
    km, lat, lon = points_du_tour()

    # Pays présent à chaque pas
    code = np.full(len(km), -1)
    for i, (nom, polygones) in enumerate(pays):
        code[dans_pays(lon, lat, polygones)] = i

    # Les points en mer reçoivent un code négatif propre à chaque mer
    cote = np.where(np.abs(lon - PARIS[1]) < 90, "paris", "anti")
    for k in np.nonzero(code < 0)[0]:
        code[k] = -1 - indice_mer(cote[k], lat[k])

    # Découpage en traversées successives
    traversees = []
    debut = 0
    for k in range(1, len(km) + 1):
        if k == len(km) or code[k] != code[debut]:
            milieu = (debut + k - 1) // 2
            if code[debut] >= 0:
                nom_en = pays[code[debut]][0]
                nom = NOMS.get(nom_en, nom_en)
            else:
                nom_en, nom = None, MERS[-1 - code[debut]][3]
            traversees.append({
                "nom": nom,
                "nom_natural_earth": nom_en,
                "terre": bool(code[debut] >= 0),
                "km_entree": float(km[debut]),
                "km_sortie": float(km[k - 1] + PAS_KM),
                "lat_milieu": round(float(lat[milieu]), 3),
                "lon_milieu": round(float(lon[milieu]), 3),
            })
            debut = k

    # Fusionne les morceaux trop courts (îlots, criques) avec ce qui les entoure,
    # sauf s'il s'agit d'un pays qui n'apparaît nulle part ailleurs.
    noms_pays = [t["nom"] for t in traversees if t["terre"]]
    fusion = []
    for t in traversees:
        court = t["km_sortie"] - t["km_entree"] < 30
        unique = t["terre"] and noms_pays.count(t["nom"]) == 1
        if fusion and (t["nom"] == fusion[-1]["nom"] or (court and not unique)):
            fusion[-1]["km_sortie"] = t["km_sortie"]
        else:
            fusion.append(t)
    for t in fusion:
        t["heure_entree"] = formater_heure(t["km_entree"] * 1e3 / vitesse)
        t["duree_km"] = round(t["km_sortie"] - t["km_entree"])

    # Textures : identifiant des pays traversés et frontières de tous les pays
    largeur, hauteur = args.largeur, args.largeur // 2

    def pixels(ring, decalage):
        return [((x + decalage + 180) / 360 * largeur, (90 - y) / 180 * hauteur) for x, y in ring]

    traverses = sorted({t["nom_natural_earth"] for t in fusion if t["terre"]})
    identifiants = {nom: (i + 1) * 255 // (len(traverses) + 1) for i, nom in enumerate(traverses)}
    carte_id = Image.new("L", (largeur, hauteur), 0)
    trace_id = ImageDraw.Draw(carte_id)
    frontieres = Image.new("LA", (largeur, hauteur), (255, 0))
    trace_f = ImageDraw.Draw(frontieres)
    epaisseur = max(1, largeur // 4096)
    for nom, polygones in pays:
        for anneaux in polygones:
            for decalage in DECALAGES:
                if nom in identifiants:
                    trace_id.polygon(pixels(anneaux[0], decalage), fill=identifiants[nom])
                    for trou in anneaux[1:]:
                        trace_id.polygon(pixels(trou, decalage), fill=0)
                for ring in anneaux:
                    # Le bord ajouté pour refermer un anneau polaire n'est pas une frontière
                    contour = ring[:-2] if abs(ring[-1, 1]) == 90 and abs(ring[-2, 1]) == 90 else ring
                    trace_f.line(pixels(contour, decalage), fill=(255, 255), width=epaisseur)
    args.sortie.mkdir(parents=True, exist_ok=True)
    carte_id.save(args.sortie / "pays_id.png")
    frontieres.save(args.sortie / "frontieres.png")

    for t in fusion:
        if t["terre"]:
            t["identifiant"] = identifiants[t["nom_natural_earth"]]
    resultat = {
        "source": "Natural Earth 1:10m (world-atlas 2.0.2), domaine public",
        "vitesse_onde_m_s": vitesse,
        "traversees": fusion,
    }
    with open(args.sortie / "pays_meridien.json", "w", encoding="utf-8") as f:
        json.dump(resultat, f, ensure_ascii=False, indent=2)

    # Contours des pays traversés, allégés à 4 000 points par anneau au plus ;
    # les anneaux minuscules (îlots) sont ignorés.
    contours = {}
    for nom, polygones in pays:
        if nom not in identifiants:
            continue
        anneaux = []
        for polygone in polygones:
            ring = polygone[0]
            etendue = np.ptp(ring[:, 0]) + np.ptp(ring[:, 1])
            if etendue < 0.5 or len(ring) < 8:
                continue
            pas = max(1, len(ring) // 4000)
            allege = np.vstack([ring[::pas], ring[-1:]])
            if abs(allege[-1, 1]) == 90 and abs(allege[-2, 1]) == 90:
                allege = allege[:-2]
            anneaux.append(np.round(allege, 3).tolist())
        contours[nom] = anneaux
    with open(args.sortie / "contours_pays.json", "w", encoding="utf-8") as f:
        json.dump(contours, f, separators=(",", ":"))

    for t in fusion:
        print(f"{t['km_entree']:>8,.0f} km  {t['heure_entree']:>8}  {t['nom']:<22} ({t['duree_km']:,} km)")


if __name__ == "__main__":
    main()
