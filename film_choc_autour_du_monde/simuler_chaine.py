#!/usr/bin/env python3
"""Simulation physique de la séquence « Le choc autour du monde ».

Calcule, sans aucun effet visuel :
  1. la chute de la première bille (pendule simple, non linéaire) ;
  2. la propagation de l'impulsion dans une chaîne de billes d'acier
     en contact de Hertz (F = k·δ^(3/2)) ;
  3. le balancement des billes après le choc, jusqu'à ce que la dernière
     atteigne son amplitude maximale.

Les résultats sont écrits en unités SI (CSV + JSON). Le script
importer_blender.py les transforme ensuite en animation, sans rien recalculer.

Hypothèses : chocs parfaitement élastiques, chaîne rectiligne et sans
précompression, fils et gravité négligés pendant le choc (quelques
millisecondes), un seul degré de liberté par bille.

Usage :
    python3 simuler_chaine.py --billes 60 --sortie donnees_choc
"""

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

G = 9.81  # m/s²

# Grands cercles terrestres (m)
TOUR_MERIDIEN_M = 40_008e3
TOUR_EQUATEUR_M = 40_075e3

# Distances depuis Paris en descendant le méridien de Paris (2,35° E), en km
REPERES_MERIDIEN_KM = {
    "Alger (côte algérienne)": 1_345,
    "Cotonou (golfe de Guinée)": 4_722,
    "Antipode de Paris": 20_004,
    "Retour à Paris": 40_008,
}


def raideur_hertz(young, poisson, rayon):
    """Raideur k de F = k·δ^(3/2) pour deux sphères identiques de rayon R."""
    return (2 / 3) * young / (1 - poisson**2) * math.sqrt(rayon / 2)


def integrer_pendule(theta, omega, longueur, evenement, dt=1e-4, tous_les=10):
    """Intègre θ'' = -(g/L)·sin θ (RK4) jusqu'au changement de signe de
    evenement(θ, ω). Le dernier point est interpolé sur l'événement.

    Renvoie (temps, angles, ω final), un point enregistré tous les `tous_les` pas."""

    def derivee(th, om):
        return om, -G / longueur * math.sin(th)

    t, pas = 0.0, 0
    temps, angles = [t], [theta]
    e0 = evenement(theta, omega)
    while True:
        k1 = derivee(theta, omega)
        k2 = derivee(theta + dt / 2 * k1[0], omega + dt / 2 * k1[1])
        k3 = derivee(theta + dt / 2 * k2[0], omega + dt / 2 * k2[1])
        k4 = derivee(theta + dt * k3[0], omega + dt * k3[1])
        th = theta + dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        om = omega + dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        e1 = evenement(th, om)
        if e0 * e1 <= 0:
            s = e0 / (e0 - e1)
            temps.append(t + s * dt)
            angles.append(theta + s * (th - theta))
            return np.array(temps), np.array(angles), omega + s * (om - omega)
        t += dt
        pas += 1
        theta, omega, e0 = th, om, e1
        if pas % tous_les == 0:
            temps.append(t)
            angles.append(theta)


def balancer(omegas, longueur, duree, dt=1e-4, tous_les=10):
    """Balancement libre de toutes les billes, parties de la verticale avec
    les vitesses angulaires `omegas`, pendant `duree` (RK4 vectorisé).

    Renvoie (temps, angles[instant, bille])."""
    pas = max(1, math.ceil(duree / dt))
    dt = duree / pas
    theta = np.zeros_like(omegas)
    omega = omegas.copy()
    temps, angles = [0.0], [theta.copy()]
    for i in range(1, pas + 1):
        k1t, k1o = omega, -G / longueur * np.sin(theta)
        k2t, k2o = omega + dt / 2 * k1o, -G / longueur * np.sin(theta + dt / 2 * k1t)
        k3t, k3o = omega + dt / 2 * k2o, -G / longueur * np.sin(theta + dt / 2 * k2t)
        k4t, k4o = omega + dt * k3o, -G / longueur * np.sin(theta + dt * k3t)
        theta = theta + dt / 6 * (k1t + 2 * k2t + 2 * k3t + k4t)
        omega = omega + dt / 6 * (k1o + 2 * k2o + 2 * k3o + k4o)
        if i % tous_les == 0 or i == pas:
            temps.append(i * dt)
            angles.append(theta.copy())
    return np.array(temps), np.array(angles)


def simuler_chaine(n, rayon, masse, k, v0, pas_par_contact=200, echantillons_par_contact=20):
    """Chaîne de n billes au contact, la bille 0 arrivant à v0.

    Intégration de Verlet (vitesses). Le pas de temps est réglé sur la durée
    d'un choc de Hertz bille contre bille. La simulation s'arrête quand la
    dernière bille a quitté la chaîne."""
    m_eff = masse / 2
    compression_choc = (5 * m_eff * v0**2 / (4 * k)) ** 0.4
    duree_contact = 2.94 * compression_choc / v0
    dt = duree_contact / pas_par_contact
    tous_les = max(1, pas_par_contact // echantillons_par_contact)
    t_limite = 1000 * n * duree_contact  # garde-fou

    u = np.zeros(n)  # déplacement depuis la position de repos (m)
    v = np.zeros(n)
    v[0] = v0

    def calculer(u):
        delta = np.maximum(u[:-1] - u[1:], 0.0)  # interpénétration aux contacts
        f = k * delta**1.5
        a = np.zeros(n)
        a[:-1] -= f / masse
        a[1:] += f / masse
        return a, f, delta

    def par_bille(contacts):
        """Valeur au contact le plus sollicité de chaque bille."""
        b = np.zeros(n)
        b[:-1] = contacts
        b[1:] = np.maximum(b[1:], contacts)
        return b

    a, f, delta = calculer(u)
    f_pic = np.zeros(n - 1)
    t_pic = np.zeros(n - 1)
    enregistrements = []
    t, pas = 0.0, 0
    t_dernier_contact = None
    while True:
        if pas % tous_les == 0:
            enregistrements.append((t, u.copy(), v.copy(), par_bille(delta), par_bille(f)))
        v_demi = v + a * dt / 2
        u = u + v_demi * dt
        a, f, delta = calculer(u)
        v = v_demi + a * dt / 2
        t += dt
        pas += 1

        plus_fort = f > f_pic
        f_pic[plus_fort] = f[plus_fort]
        t_pic[plus_fort] = t
        if f[-1] > 0:
            t_dernier_contact = t
        if t_dernier_contact is not None and t - t_dernier_contact > 2 * duree_contact:
            enregistrements.append((t, u.copy(), v.copy(), par_bille(delta), par_bille(f)))
            break
        if t > t_limite:
            raise RuntimeError("L'impulsion n'a pas atteint la dernière bille.")

    # Vitesse de l'onde : régression sur l'instant du pic de force au milieu
    # de la chaîne, une fois l'onde solitaire formée et loin du bord de sortie.
    milieu = np.arange(n // 4, 3 * n // 4)
    position_contacts = (2 * milieu + 1) * rayon
    vitesse_onde = np.polyfit(t_pic[milieu], position_contacts, 1)[0]

    return {
        "enregistrements": enregistrements,
        "dt": dt,
        "duree_contact": duree_contact,
        "vitesse_onde": vitesse_onde,
        "vitesses_finales": v,
    }


def formater_duree(secondes):
    h, reste = divmod(round(secondes), 3600)
    m, s = divmod(reste, 60)
    return f"{h} h {m:02d} min {s:02d} s"


def temps_terrestres(vitesse):
    """Durées de parcours terrestres à vitesse constante."""
    return {
        "tour_meridien_paris": formater_duree(TOUR_MERIDIEN_M / vitesse),
        "tour_equateur": formater_duree(TOUR_EQUATEUR_M / vitesse),
        "reperes_meridien_paris": {
            nom: formater_duree(km * 1e3 / vitesse) for nom, km in REPERES_MERIDIEN_KM.items()
        },
    }


def ecrire_csv(chemin, entetes, lignes):
    with open(chemin, "w", newline="", encoding="utf-8") as fichier:
        ecrivain = csv.writer(fichier)
        ecrivain.writerow(entetes)
        ecrivain.writerows(lignes)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--billes", type=int, default=60, help="nombre de billes (≥ 8)")
    p.add_argument("--rayon", type=float, default=0.0125, help="rayon d'une bille (m)")
    p.add_argument("--longueur-fil", type=float, default=0.30, help="longueur du pendule (m)")
    p.add_argument("--angle", type=float, default=30.0, help="angle de lâcher (degrés)")
    p.add_argument("--young", type=float, default=200e9, help="module d'Young (Pa)")
    p.add_argument("--poisson", type=float, default=0.30, help="coefficient de Poisson")
    p.add_argument("--densite", type=float, default=7850.0, help="masse volumique (kg/m³)")
    p.add_argument("--sortie", type=Path, default=Path("donnees_choc"), help="dossier de sortie")
    args = p.parse_args()
    if args.billes < 8:
        p.error("il faut au moins 8 billes pour mesurer la vitesse de l'onde")

    masse = args.densite * 4 / 3 * math.pi * args.rayon**3
    k = raideur_hertz(args.young, args.poisson, args.rayon)
    angle = math.radians(args.angle)
    L = args.longueur_fil

    # 1. Chute de la première bille (angle compté positif vers la chaîne)
    t_entree, a_entree, omega_impact = integrer_pendule(-angle, 0.0, L, lambda th, om: th)
    v0 = L * omega_impact

    # 2. Propagation dans la chaîne
    res = simuler_chaine(args.billes, args.rayon, masse, k, v0)

    # 3. Après le choc, chaque bille repart avec sa vitesse finale : la dernière
    # s'envole, les premières reculent légèrement. On suit le balancement de
    # toutes jusqu'à ce que la dernière atteigne le haut de sa course.
    v_finales = res["vitesses_finales"]
    v_sortie = v_finales[-1]
    if np.any(np.diff(v_finales) < 0):
        print("Attention : des billes se rattrapent après le choc ; "
              "le balancement libre ne décrit pas ces nouveaux contacts.")
    duree_sortie = 0.0
    if v_sortie > 0:
        t_tmp, _, _ = integrer_pendule(0.0, v_sortie / L, L, lambda th, om: om)
        duree_sortie = t_tmp[-1]
    t_sortie, a_sortie = balancer(v_finales / L, L, duree_sortie)

    args.sortie.mkdir(parents=True, exist_ok=True)
    ecrire_csv(
        args.sortie / "pendule_entree.csv",
        ["t_s", "angle_rad"],
        ([f"{t:.6e}", f"{a:.9e}"] for t, a in zip(t_entree, a_entree)),
    )
    ecrire_csv(
        args.sortie / "pendule_sortie.csv",
        ["t_s", "bille", "angle_rad"],
        (
            [f"{t:.6e}", i, f"{a[i]:.9e}"]
            for t, a in zip(t_sortie, a_sortie)
            for i in range(args.billes)
        ),
    )
    ecrire_csv(
        args.sortie / "chaine.csv",
        ["t_s", "bille", "deplacement_m", "vitesse_m_s", "compression_m", "force_N"],
        (
            [f"{t:.9e}", i, f"{u[i]:.9e}", f"{v[i]:.9e}", f"{d[i]:.9e}", f"{f[i]:.9e}"]
            for t, u, v, d, f in res["enregistrements"]
            for i in range(args.billes)
        ),
    )

    vitesse_barre = math.sqrt(args.young / args.densite)
    compression_max = max(d.max() for _, _, _, d, _ in res["enregistrements"])
    meta = {
        "parametres": {
            "billes": args.billes,
            "rayon_m": args.rayon,
            "longueur_fil_m": L,
            "angle_lacher_deg": args.angle,
            "young_Pa": args.young,
            "poisson": args.poisson,
            "densite_kg_m3": args.densite,
        },
        "bille": {"masse_kg": masse, "raideur_hertz_N_m-1.5": k},
        "pendule": {
            "duree_chute_s": float(t_entree[-1]),
            "vitesse_impact_m_s": v0,
            "vitesse_impact_energie_m_s": math.sqrt(2 * G * L * (1 - math.cos(angle))),
            "vitesse_sortie_m_s": float(v_sortie),
            "vitesse_recul_premiere_bille_m_s": float(v_finales[0]),
            "duree_sortie_s": float(duree_sortie),
            "angle_sortie_deg": math.degrees(float(a_sortie[-1, -1])),
        },
        "chaine": {
            "duree_s": res["enregistrements"][-1][0],
            "pas_de_temps_s": res["dt"],
            "duree_contact_s": res["duree_contact"],
            "compression_max_m": float(compression_max),
            "vitesse_onde_m_s": float(res["vitesse_onde"]),
            "vitesse_barre_acier_m_s": vitesse_barre,
        },
        "terre": {
            "a_la_vitesse_de_l_onde": temps_terrestres(res["vitesse_onde"]),
            "a_la_vitesse_du_son_dans_l_acier": temps_terrestres(vitesse_barre),
        },
    }
    with open(args.sortie / "meta.json", "w", encoding="utf-8") as fichier:
        json.dump(meta, fichier, ensure_ascii=False, indent=2)

    print(f"Vitesse d'impact          : {v0:.3f} m/s (chute en {t_entree[-1] * 1e3:.0f} ms)")
    print(f"Durée d'un contact        : {res['duree_contact'] * 1e6:.0f} µs")
    print(f"Compression maximale      : {compression_max * 1e6:.1f} µm")
    print(f"Vitesse de l'onde (billes): {res['vitesse_onde']:.0f} m/s")
    print(f"Son dans l'acier (barre)  : {vitesse_barre:.0f} m/s")
    print(f"Vitesse de sortie         : {v_sortie:.3f} m/s ({meta['pendule']['angle_sortie_deg']:.1f}°)")
    print(f"Recul de la première bille: {v_finales[0]:.3f} m/s")
    print(f"Tour du méridien de Paris : {meta['terre']['a_la_vitesse_de_l_onde']['tour_meridien_paris']}")
    print(f"Données écrites dans      : {args.sortie}")


if __name__ == "__main__":
    main()
