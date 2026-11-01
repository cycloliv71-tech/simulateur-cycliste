"""Rend « Le choc autour du monde » (30 s) de bout en bout, en une commande :

    blender -b -P rendre_film.py
    blender -b -P rendre_film.py -- --apercu              (640×360, rapide)
    blender -b -P rendre_film.py -- --resolution 3840x2160 --echantillons 256

Étapes :
  1. la simulation physique (simuler_chaine.py), si donnees_choc n'existe pas ;
  2. la scène du pendule (plans_pendule_blender.py) et celle de la Terre
     (plans_terre_blender.py) ;
  3. le rendu de chaque image avec Cycles, sur la carte graphique si Blender
     en trouve une (OptiX, CUDA, HIP, oneAPI ou Metal). Les images déjà
     rendues sont gardées : on peut interrompre et relancer ;
  4. la bande son (bande_son.py), calée sur les mêmes données ;
  5. le montage (plans 1 à 4, Terre, plan 10, titre) et la vidéo MP4.

Tout est écrit dans le dossier de sortie (par défaut « rendu » à côté de ce
script), y compris film.blend pour ouvrir les scènes dans Blender.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import bpy
import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import bande_son  # noqa: E402
import plans_pendule_blender  # noqa: E402
import plans_terre_blender  # noqa: E402
import simuler_chaine  # noqa: E402

FPS = 24
NOM_FILM = "le_choc_autour_du_monde.mp4"


def lire_arguments():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(prog="rendre_film.py")
    p.add_argument("--sortie", type=Path, default=ICI / "rendu")
    p.add_argument("--donnees", type=Path, default=ICI / "donnees_choc")
    p.add_argument("--textures", type=Path, default=ICI / "textures")
    p.add_argument("--resolution", default="1920x1080")
    p.add_argument("--echantillons", type=int, default=128)
    p.add_argument("--apercu", action="store_true", help="640×360 et 12 échantillons, pour vérifier vite")
    p.add_argument("--processeur", action="store_true", help="ne pas chercher de carte graphique")
    p.add_argument("--montage-seul", action="store_true", help="refaire le son et la vidéo sans rien rendre")
    args = p.parse_args(argv)
    if args.apercu:
        args.resolution, args.echantillons = "640x360", 12
    args.largeur, args.hauteur = (int(v) for v in args.resolution.lower().split("x"))
    return args


def activer_gpu():
    """Active la première famille de cartes graphiques disponible ; renvoie son nom."""
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for famille in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
        try:
            prefs.compute_device_type = famille
        except TypeError:
            continue
        if hasattr(prefs, "refresh_devices"):
            prefs.refresh_devices()
        else:
            prefs.get_devices()
        cartes = [d for d in prefs.devices if d.type == famille]
        if cartes:
            for d in prefs.devices:
                d.use = d.type == famille
            return f"{famille} ({', '.join(d.name for d in cartes)})"
    return None


def regler_rendu(scene, args, gpu):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "GPU" if gpu else "CPU"
    scene.cycles.samples = args.echantillons
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = args.largeur, args.hauteur
    scene.render.resolution_percentage = 100
    scene.render.use_persistent_data = True
    scene.render.fps = FPS
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"


def rendre(scene, images, dossier):
    dossier.mkdir(parents=True, exist_ok=True)
    a_faire = [f for f in images if not (dossier / f"{f:04d}.png").exists()]
    print(f"{scene.name} : {len(images) - len(a_faire)} images déjà rendues, {len(a_faire)} à rendre")
    debut = time.time()
    for k, image in enumerate(a_faire, 1):
        scene.frame_set(image)
        scene.render.filepath = str(dossier / f"{image:04d}.png")
        bpy.ops.render.render(write_still=True, scene=scene.name)
        ecoule = time.time() - debut
        print(f"  {scene.name} {image} ({k}/{len(a_faire)}), reste ≈ {ecoule / k * (len(a_faire) - k) / 60:.0f} min",
              flush=True)


def instants_contacts(donnees, n, impact_s, duree_choc_s):
    """Instant du pic de force de chaque bille, ramené au ralenti du film."""
    chaine = np.loadtxt(donnees / "chaine.csv", delimiter=",", skiprows=1).reshape(-1, n, 6)
    temps, force = chaine[:, 0, 0], chaine[:, :, 5]
    pics = temps[force.argmax(axis=0)][1:]
    return list(impact_s + pics / temps[-1] * duree_choc_s)


def plages(masque, temps):
    """Plages (début, fin) où le masque est vrai."""
    resultat, debut = [], None
    for i, vrai in enumerate(masque):
        if vrai and debut is None:
            debut = i
        if (not vrai or i == len(masque) - 1) and debut is not None:
            resultat.append((temps[debut], temps[i]))
            debut = None
    return resultat


def ajouter_image(pistes, nom, dossier, premiere, derniere, canal, debut):
    strip = pistes.new_image(name=nom, filepath=str(dossier / f"{premiere:04d}.png"), channel=canal, frame_start=debut)
    for image in range(premiere + 1, derniere + 1):
        strip.elements.append(f"{image:04d}.png")
    return strip


def ajouter_effet(pistes, nom, type_, canal, debut, longueur):
    try:
        return pistes.new_effect(name=nom, type=type_, channel=canal, frame_start=debut, length=longueur)
    except TypeError:  # Blender 4.x
        return pistes.new_effect(name=nom, type=type_, channel=canal, frame_start=debut, frame_end=debut + longueur)


def ajouter_texte(pistes, contenu, canal, debut, longueur, hauteur):
    strip = ajouter_effet(pistes, contenu, "TEXT", canal, debut, longueur)
    strip.text = contenu
    strip.font_size = round(0.032 * hauteur)
    strip.location = (0.965, 0.93)
    strip.anchor_x, strip.anchor_y = "RIGHT", "TOP"
    strip.use_shadow = True
    strip.color = (1.0, 1.0, 1.0, 0.85)
    return strip


def fondu(strip, cles):
    for image, alpha in cles:
        strip.blend_alpha = alpha
        strip.keyframe_insert("blend_alpha", frame=image)


def main():
    args = lire_arguments()
    args.sortie.mkdir(parents=True, exist_ok=True)

    # 1. Simulation physique
    if not (args.donnees / "meta.json").exists():
        sys.argv = ["simuler_chaine.py", "--sortie", str(args.donnees)]
        simuler_chaine.main()

    # 2. Scènes
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sys.argv = [sys.argv[0], "--", "--donnees", str(args.donnees), "--textures", str(args.textures)]
    reperes = plans_pendule_blender.main()
    pendule = bpy.context.scene
    plans_terre_blender.main()
    terre = bpy.data.scenes[plans_terre_blender.NOM_SCENE]

    gpu = None if args.processeur else activer_gpu()
    print(f"Rendu sur : {gpu or 'processeur'}")
    for scene in (pendule, terre):
        regler_rendu(scene, args, gpu)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.sortie / "film.blend"))

    # 3. Rendu des images
    fin_choc, derniere = reperes["image_fin_choc"], reperes["image_derniere"]
    fin_voyage = plans_terre_blender.IMAGE_DEBUT + round(plans_terre_blender.FIN_VOYAGE_S * FPS) - 1
    dossier_pendule, dossier_terre = args.sortie / "pendule", args.sortie / "terre"
    if not args.montage_seul:
        rendre(pendule, range(1, derniere + 1), dossier_pendule)
        rendre(terre, range(terre.frame_start, terre.frame_end + 1), dossier_terre)

    # 4. Montage : plans 1-4 (pendule), 5-9 (Terre), 10 (pendule), 11 (titre sur la Terre)
    segments = [
        ("Pendule", dossier_pendule, 1, fin_choc),
        ("Tour_du_monde", dossier_terre, terre.frame_start, fin_voyage),
        ("Derniere_bille", dossier_pendule, fin_choc + 1, derniere),
        ("Titre", dossier_terre, fin_voyage + 1, terre.frame_end),
    ]
    positions, total = [], 0
    for _, _, premiere, fin in segments:
        positions.append(total + 1)
        total += fin - premiere + 1
    debut_terre, debut_plan10, debut_titre = positions[1], positions[2], positions[3]

    def secondes(image_film):
        return (image_film - 1) / FPS

    # 5. Bande son, calée sur les mêmes repères
    distance = np.array(terre["terre_distance_km"])
    acceleration = np.array(terre["terre_acceleration"])
    traversees = json.loads(terre["traversees_json"])
    image_lacher = terre["terre_image_lacher"]
    entrees = [secondes(debut_terre + image_lacher)]
    for t in traversees[1:]:
        entrees.append(secondes(debut_terre + int(np.searchsorted(distance, t["km_entree"]))))
    temps_terre = np.array([secondes(debut_terre + i) for i in range(fin_voyage)])
    chemin_son = args.sortie / "bande_son.wav"
    bande_son.generer(
        chemin_son,
        duree_s=total / FPS,
        impact_s=secondes(reperes["image_impact"]),
        contacts_s=instants_contacts(args.donnees, reperes["billes"], secondes(reperes["image_impact"]),
                                     plans_pendule_blender.DUREE_CHOC_S),
        entrees_s=entrees,
        voyage_s=(secondes(debut_terre), secondes(debut_plan10)),
        accelerations_s=plages(acceleration[:fin_voyage] > 5_000, temps_terre),
        retour_s=secondes(debut_terre + int(np.searchsorted(distance, plans_terre_blender.TOUR_MERIDIEN_KM - 1))),
        dernier_choc_s=secondes(debut_plan10),
        titre_s=secondes(debut_titre + 12),
    )

    # 6. Montage vidéo
    montage = bpy.data.scenes.new("Montage")
    montage.render.fps = FPS
    montage.render.resolution_x, montage.render.resolution_y = args.largeur, args.hauteur
    montage.render.resolution_percentage = 100
    montage.frame_start, montage.frame_end = 1, total
    montage.view_settings.view_transform = "Standard"  # les images sont déjà étalonnées
    pistes = montage.sequence_editor_create()
    pistes = pistes.strips if hasattr(pistes, "strips") else pistes.sequences
    for (nom, dossier, premiere, fin), position in zip(segments, positions):
        ajouter_image(pistes, nom, dossier, premiere, fin, 1, position)

    # Éclair blanc entre le pendule et la Terre, fondu au noir à la fin
    eclair = ajouter_effet(pistes, "Eclair", "COLOR", 3, debut_terre - 4, 12)
    eclair.color = (1.0, 1.0, 1.0)
    fondu(eclair, [(debut_terre - 4, 0.0), (debut_terre, 1.0), (debut_terre + 7, 0.0)])
    noir = ajouter_effet(pistes, "Fondu_noir", "COLOR", 3, total - 17, 18)
    noir.color = (0.0, 0.0, 0.0)
    fondu(noir, [(total - 17, 0.0), (total, 1.0)])

    # Échelle de temps des plans du pendule
    ralenti_choc = f"Ralenti ×{reperes['ralenti_choc']:,.0f}".replace(",", " ")
    ralenti_balancement = f"Ralenti ×{reperes['ralenti_balancement']:g}"
    impact = reperes["image_impact"]
    ajouter_texte(pistes, ralenti_balancement, 4, 1, impact - 1, args.hauteur)
    ajouter_texte(pistes, ralenti_choc, 5, impact, fin_choc - impact + 1, args.hauteur)
    ajouter_texte(pistes, ralenti_balancement, 4, debut_plan10, derniere - fin_choc, args.hauteur)

    pistes.new_sound(name="Bande_son", filepath=str(chemin_son), channel=6, frame_start=1)

    sortie = montage.render.image_settings
    if hasattr(sortie, "media_type"):
        sortie.media_type = "VIDEO"
    sortie.file_format = "FFMPEG"
    ffmpeg = montage.render.ffmpeg
    ffmpeg.format, ffmpeg.codec = "MPEG4", "H264"
    ffmpeg.constant_rate_factor = "HIGH"
    ffmpeg.audio_codec, ffmpeg.audio_bitrate, ffmpeg.audio_channels = "AAC", 192, "STEREO"
    montage.render.filepath = str(args.sortie / NOM_FILM)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.sortie / "film.blend"))
    bpy.ops.render.render(animation=True, scene=montage.name)
    # Blender ajoute la plage d'images au nom des vidéos : on remet le nom voulu
    for fichier in args.sortie.glob(f"{Path(NOM_FILM).stem}*.mp4"):
        if fichier.name != NOM_FILM:
            fichier.replace(args.sortie / NOM_FILM)
    print(f"Film : {args.sortie / NOM_FILM} ({total} images, {total / FPS:.1f} s)")


if __name__ == "__main__":
    main()
