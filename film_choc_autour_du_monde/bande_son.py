"""Bande son de « Le choc autour du monde », synthétisée avec NumPy.

Rien n'est enregistré : chaque son est calculé.
  - Le choc de la bille lâchée, puis un tintement à chaque contact entre
    deux billes, à l'instant calculé par simuler_chaine.py (au ralenti du film).
  - Une note de cloche à l'entrée dans chaque pays ou chaque mer.
  - Un accord tenu et discret pendant le tour du monde, une montée de souffle
    quand l'impulsion accélère, puis le retour, le dernier choc et le titre.

generer() reçoit les instants (en secondes de film) et écrit un WAV stéréo.
"""

import wave

import numpy as np

TAUX = 48_000
# Rapports des premiers modes de vibration d'une bille d'acier (inharmoniques)
MODES_BILLE = (1.0, 2.76, 5.40, 8.93)


def _env(n, attaque, chute):
    t = np.arange(n) / TAUX
    return np.minimum(1.0, t / max(attaque, 1e-4)) * np.exp(-t / chute)


def _ajouter(piste, debut_s, son):
    i = int(debut_s * TAUX)
    if i >= len(piste) or i + len(son) <= 0:
        return
    j = min(len(piste), i + len(son))
    piste[max(i, 0):j] += son[max(0, -i):j - i]


def choc_metallique(force=1.0, f0=3_100.0, duree=0.9, graine=0):
    """Claquement de deux billes : modes inharmoniques + transitoire de bruit."""
    n = int(duree * TAUX)
    t = np.arange(n) / TAUX
    son = np.zeros(n)
    for rang, rapport in enumerate(MODES_BILLE):
        son += np.sin(2 * np.pi * f0 * rapport * t) * np.exp(-t / (0.25 / (1 + rang))) / (1 + rang)
    bruit = np.random.default_rng(graine).standard_normal(n) * np.exp(-t / 0.004)
    return force * (0.6 * son + 0.5 * bruit)


def tintement(f0, force=0.15, duree=0.25):
    n = int(duree * TAUX)
    t = np.arange(n) / TAUX
    son = sum(np.sin(2 * np.pi * f0 * r * t) / (1 + k) for k, r in enumerate(MODES_BILLE[:3]))
    return force * son * _env(n, 0.001, 0.05)


def cloche(f0, force=0.25, duree=2.5):
    n = int(duree * TAUX)
    t = np.arange(n) / TAUX
    son = np.zeros(n)
    for rapport, poids, chute in ((1.0, 1.0, 1.2), (2.0, 0.5, 0.8), (2.76, 0.35, 0.5), (5.4, 0.15, 0.25)):
        son += poids * np.sin(2 * np.pi * f0 * rapport * t) * np.exp(-t / chute)
    return force * son * np.minimum(1.0, t / 0.003)


def nappe(frequences, duree, force=0.06, attaque=1.5, relache=2.0):
    """Accord tenu : sinus légèrement désaccordés, lente respiration."""
    n = int(duree * TAUX)
    t = np.arange(n) / TAUX
    son = np.zeros(n)
    for k, f in enumerate(frequences):
        for desaccord in (-0.15, 0.15):
            son += np.sin(2 * np.pi * f * (1 + desaccord / 100) * t + k)
    son *= 1 + 0.15 * np.sin(2 * np.pi * 0.2 * t)
    enveloppe = np.minimum(1.0, t / attaque) * np.minimum(1.0, (duree - t) / relache).clip(0)
    return force * son * enveloppe / len(frequences)


def souffle(duree, force=0.08, graine=1):
    """Bruit filtré qui enfle puis retombe (accélération de l'impulsion)."""
    n = int(duree * TAUX)
    bruit = np.random.default_rng(graine).standard_normal(n)
    spectre = np.fft.rfft(bruit)
    f = np.fft.rfftfreq(n, 1 / TAUX)
    spectre *= np.exp(-((np.log(f + 1) - np.log(900)) ** 2) / 0.8)
    son = np.fft.irfft(spectre, n)
    son /= np.abs(son).max() + 1e-9
    return force * son * np.sin(np.pi * np.arange(n) / n) ** 2


def grondement(duree=3.0, force=0.5):
    n = int(duree * TAUX)
    t = np.arange(n) / TAUX
    frequence = 55 * np.exp(-t / 2.5) + 35
    return force * np.sin(2 * np.pi * np.cumsum(frequence) / TAUX) * _env(n, 0.01, 1.0)


def reverberation(signal, duree=2.2, melange=0.25, graine=2):
    """Convolution par une réponse impulsionnelle de bruit à décroissance exponentielle."""
    n = int(duree * TAUX)
    reponse = np.random.default_rng(graine).standard_normal(n) * np.exp(-np.arange(n) / TAUX / (duree / 6.9))
    reponse /= np.sqrt((reponse ** 2).sum())
    taille = 1 << int(np.ceil(np.log2(len(signal) + n)))
    humide = np.fft.irfft(np.fft.rfft(signal, taille) * np.fft.rfft(reponse, taille), taille)[:len(signal)]
    return (1 - melange) * signal + melange * humide


def generer(chemin, duree_s, impact_s, contacts_s, entrees_s, voyage_s, accelerations_s,
            retour_s, dernier_choc_s, titre_s):
    """Écrit la bande son.

    contacts_s : instants des contacts entre billes (ralenti du film)
    entrees_s : instants d'entrée dans chaque pays ou mer
    voyage_s : (début, fin) du tour du monde
    accelerations_s : liste de (début, fin) des passages en forte accélération
    """
    piste = np.zeros(int(duree_s * TAUX) + TAUX)

    _ajouter(piste, impact_s, choc_metallique(1.0))
    for k, t in enumerate(contacts_s):
        _ajouter(piste, t, tintement(2_600 * 2 ** (k / len(contacts_s) / 2), 0.12))

    # Tour du monde : nappe en la mineur, une cloche par étape (gamme pentatonique)
    debut, fin = voyage_s
    for (accord, t0, t1) in (((110.0, 164.8, 220.0, 261.6), debut, debut + (fin - debut) / 2),
                             ((87.3, 130.8, 174.6, 220.0), debut + (fin - debut) / 2 - 1, fin + 1.5)):
        _ajouter(piste, t0, nappe(accord, t1 - t0))
    pentatonique = (440.0, 523.3, 587.3, 659.3, 784.0, 880.0)
    for k, t in enumerate(entrees_s):
        _ajouter(piste, t, cloche(pentatonique[k % len(pentatonique)], 0.18))
    for k, (t0, t1) in enumerate(accelerations_s):
        _ajouter(piste, t0, souffle(t1 - t0, graine=10 + k))

    _ajouter(piste, retour_s, cloche(880.0, 0.3, 3.0) + np.pad(cloche(1_318.5, 0.2, 2.5), (0, TAUX // 2)))
    _ajouter(piste, dernier_choc_s, choc_metallique(0.9, graine=3))
    _ajouter(piste, titre_s, grondement())
    _ajouter(piste, titre_s, nappe((110.0, 164.8, 220.0, 277.2, 329.6), duree_s - titre_s + 0.5,
                                   force=0.10, attaque=0.8, relache=1.2))

    gauche = reverberation(piste, graine=2)
    droite = reverberation(piste, graine=5)
    stereo = np.stack([gauche, droite], axis=1)[: int(duree_s * TAUX)]
    fondu = int(0.5 * TAUX)
    stereo[-fondu:] *= np.linspace(1, 0, fondu)[:, None]
    stereo *= 0.89 / (np.abs(stereo).max() + 1e-9)  # crête à -1 dBFS
    with wave.open(str(chemin), "wb") as fichier:
        fichier.setnchannels(2)
        fichier.setsampwidth(2)
        fichier.setframerate(TAUX)
        fichier.writeframes((stereo * 32767).astype("<i2").tobytes())
