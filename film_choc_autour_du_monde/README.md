# Le choc autour du monde

Film de 30 s sur la propagation d'une impulsion dans une chaîne de billes d'acier :
un pendule de Newton, puis la même chaîne étirée autour de la Terre, le long du
méridien de Paris. Le mouvement est **calculé** ; la lumière, les zooms et le
ralenti sont **mis en scène**, et le film dit toujours lequel est lequel.

## Rendre le film (une commande)

Il faut [Blender](https://www.blender.org/download/) 4.4 ou plus récent (testé avec 5.2).
Depuis ce dossier :

```bash
blender -b -P rendre_film.py                      # 1920×1080, 128 échantillons
blender -b -P rendre_film.py -- --apercu          # 640×360, pour vérifier vite
blender -b -P rendre_film.py -- --resolution 3840x2160 --echantillons 256
```

Sous Windows, remplacez `blender` par le chemin complet, par exemple
`"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"`.

Le script trouve tout seul la carte graphique (OptiX pour une NVIDIA RTX, sinon CUDA,
HIP, oneAPI ou Metal). Avec une RTX 5070 Ti, compter de l'ordre d'une à trois secondes
par image en 1080p, soit 15 à 40 minutes pour les 720 images. Les images déjà rendues
sont gardées : on peut interrompre et relancer. Tout arrive dans `rendu/` :
`le_choc_autour_du_monde.mp4`, les images, `bande_son.wav` et `film.blend`
(pour ouvrir les scènes et le montage dans Blender).

## Déroulé

| Temps | Plans | Contenu |
|---|---|---|
| 0:00 – 0:04,8 | 1 à 4 | Bille tenue puis lâchée (ralenti ×2), choc, impulsion suivie le long des 60 billes (ralenti ×1 218) |
| 0:04,8 – 0:24,8 | 5 à 9 | Tour du monde en un seul mouvement de caméra, zoom sur chaque pays traversé |
| 0:24,8 – 0:25,9 | 10 | La dernière bille du pendule s'envole |
| 0:25,9 – 0:30 | 11 | La caméra quitte Paris, titre et bilan : 40 008 km · 17 h 02 · 653 m/s |

Pays et mers traversés, calculés sur les frontières Natural Earth :
France, Espagne, Méditerranée, Algérie, Mali, Niger, Burkina Faso (15 km), Bénin,
Atlantique, océan Austral, Antarctique, Pacifique, mer de Béring, Russie (Tchoukotka),
mer des Tchouktches, Arctique, mer de Norvège, mer du Nord, France.

## Les scripts

| Script | Rôle |
|---|---|
| `simuler_chaine.py` | Physique : chute du pendule, onde dans la chaîne (contact de Hertz), balancement final. Écrit `donnees_choc/` en unités SI. Python + NumPy. |
| `preparer_pays.py` | Géographie : pays et mers traversés le long du méridien de Paris, distances et heures d'entrée, contours et cartes des frontières. Écrit dans `textures/`. |
| `importer_blender.py` | Pose le mouvement calculé sur la ligne de temps de Blender (ralenti, amplification unique des déplacements, lueur = compression calculée). |
| `plans_pendule_blender.py` | Décor du pendule, caméra calée sur le front d'onde calculé. |
| `plans_terre_blender.py` | La Terre (jour, nuit, nuages, relief, frontières), l'anneau de billes, l'impulsion, la caméra qui suit, les cartouches et compteurs, le titre. |
| `bande_son.py` | Son synthétisé : un tintement à chaque contact calculé entre billes, une note à chaque frontière, nappe, souffle, choc final. |
| `rendre_film.py` | Enchaîne tout et produit la vidéo. |

`preparer_pays.py` a besoin des frontières Natural Earth au format TopoJSON
(`npm pack world-atlas@2.0.2`). Ses résultats sont déjà dans `textures/` ; il ne faut
le relancer que si l'on change la vitesse de l'onde ou le tracé.

## Ce qui est calculé, ce qui est mis en scène

Calculé :
- la chute du pendule, la propagation du choc de bille en bille (énergie conservée à
  10⁻⁶ près) et la vitesse de l'onde : **653 m/s** pour des billes de 25 mm lâchées à 30°
  (le son va à 5 050 m/s dans une barre d'acier) ;
- les pays traversés et leurs distances ; le temps réel affiché vaut toujours
  distance / 653 m/s, soit **17 h 02** pour le tour complet ;
- la course du Soleil (15° par heure de temps réel, à l'équinoxe) : départ de jour,
  retour à Paris de nuit.

Mis en scène, et signalé à l'écran :
- le ralenti du pendule (×2 et ×1 218) et l'accéléré du tour du monde (affiché en
  permanence, de ×600 à ×19 000 environ) ;
- les déplacements des billes du pendule, amplifiés ×32 (environ 30 µm en réalité) ;
- les 600 billes agrandies du tour du monde : il en faudrait 1,6 milliard de 25 mm ;
- la lueur et le halo, qui repèrent l'impulsion.

Limites à assumer : chocs parfaitement élastiques et sans frottement. Une vraie chaîne
amortirait l'onde bien avant un tour de Terre : les plans terrestres sont une
**expérience de pensée** qui prolonge la vitesse calculée.

## Sources des données

Voir `textures/SOURCES.md` : images NASA (domaine public), frontières Natural Earth
(domaine public).
