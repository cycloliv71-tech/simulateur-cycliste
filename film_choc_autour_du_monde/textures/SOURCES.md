# Textures et données géographiques

Projection équirectangulaire (longitude −180° à gauche, latitude +90° en haut).

| Fichier | Contenu | Origine |
|---|---|---|
| `terre_jour.jpg` | Blue Marble, 4096 × 2048 | NASA Visible Earth (domaine public) |
| `terre_nuit.jpg` | Lumières des villes, 4096 × 2048 | NASA Earth Observatory (domaine public) |
| `nuages.jpg` | Couverture nuageuse, 4096 × 2048 | NASA (domaine public) |
| `relief.png` | Relief (niveaux de gris), 2048 × 1024 | NASA (domaine public) |
| `eau.png` | Masque des océans, 1600 × 800 | NASA (domaine public) |
| `frontieres.png` | Frontières de tous les pays, 8192 × 4096 | Natural Earth 1:10m (domaine public), tracé par `preparer_pays.py` |
| `pays_id.png` | Un niveau de gris par pays traversé | Natural Earth 1:10m, tracé par `preparer_pays.py` |
| `contours_pays.json` | Contours des pays traversés | Natural Earth 1:10m, extrait par `preparer_pays.py` |
| `pays_meridien.json` | Pays et mers traversés, distances, heures | Calculé par `preparer_pays.py` |

Les images NASA sont des copies tirées du paquet npm `three-globe` 2.31.0
(`example/img/` et `example/clouds/`) ; les nuages et l'eau y ont été convertis en
niveaux de gris. Les frontières viennent du paquet npm `world-atlas` 2.0.2
(Natural Earth 4.1.0). Pour un rendu plus fin, on peut remplacer les images par les
versions haute définition de la NASA, sous les mêmes noms.
