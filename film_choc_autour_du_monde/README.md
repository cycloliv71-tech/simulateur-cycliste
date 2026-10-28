# Le choc autour du monde — mouvement calculé pour Blender

Les scripts séparent ce qui est **calculé** de ce qui est **mis en scène** :

| Script | Rôle | Où il tourne |
|---|---|---|
| `simuler_chaine.py` | Physique seule : chute du pendule, onde dans la chaîne de billes (contact de Hertz), balancement après le choc. Écrit des données en unités SI. | Python 3 + NumPy |
| `importer_blender.py` | Plans 1 à 4 et 10 (le pendule) : place les données sur la ligne de temps, amplifie les déplacements, pilote la lueur par la compression. Ne calcule aucune physique. | Blender 4.x / 5.x |
| `plans_terre_blender.py` | Plans 5 à 9 et 11 (la Terre) : chaîne le long du méridien de Paris, impulsion en accéléré, compteurs et titre. N'utilise que la vitesse de l'onde calculée. | Blender 4.x / 5.x |

`apercu_choc.mp4` montre les plans du pendule, `apercu_film.mp4` le film assemblé.

## Utilisation

```bash
python3 simuler_chaine.py --billes 60 --sortie donnees_choc
```

Puis, avec le fichier `.blend` enregistré à côté du dossier `donnees_choc` :
Blender > Scripting > Ouvrir `importer_blender.py` > Exécuter. En ligne de commande :

```bash
blender scene.blend --python importer_blender.py -- --donnees /chemin/donnees_choc
```

Le script peut être relancé : il vide et recrée la collection `Choc_Billes`.
Le matériau `Acier_choc` n'est créé qu'une fois, donc vos retouches sont conservées.

Pour les plans de la Terre, le `.blend` enregistré dans ce dossier (à côté de
`donnees_choc` et `textures`) :

```bash
blender scene.blend --python plans_terre_blender.py -- --donnees /chemin/donnees_choc --textures /chemin/textures
```

Le script crée la scène `Choc_Terre` (recréée à chaque exécution) : la Terre texturée,
l'atmosphère, l'anneau de billes, le halo qui repère l'impulsion, la caméra de chaque plan
et les textes. Les compteurs sont mis à jour à chaque image par `compteur_choc.py`, rangé
dans le `.blend` ; après réouverture du fichier, autorisez l'exécution automatique des
scripts pour qu'ils restent à jour.

Les instants de passage (`CLES_DISTANCE`) et le découpage des plans (`PLANS`) se règlent en
tête du script. Le temps réel affiché vaut toujours distance / vitesse calculée, et le
facteur « Accéléré » est celui de l'image en cours (de ×600 environ au départ à ×75 000).

## Ce qui est créé dans Blender (pendule)

- `Pivot.000…` : point d'attache de chaque fil, qui porte le balancement. Accrochez-y les fils.
- `Bille.000…` : enfant de son pivot, qui porte le déplacement dans la chaîne.
- `Front_onde` : suit le centre de l'onde (moyenne pondérée par la force).
  Une contrainte *Copy Location* ou *Child Of* dessus fait suivre l'impulsion par la caméra (plan 3).
- La lueur de chaque bille est sa compression calculée, normalisée entre 0 et 1, stockée dans
  la **couleur d'objet** et lue par le nœud *Object Info* du matériau.
- La lueur sort dans la passe **Emit** et dans l'AOV **`lueur`**. Elle se dose au compositing
  sans toucher au mouvement.
- Les propriétés de la scène `ralenti_choc`, `amplification_deplacements` et
  `vitesse_onde_m_s` contiennent les valeurs à citer au générique.

## Réglages (en tête de `importer_blender.py`)

`DUREE_ATTENTE_S`, `RALENTI_BALANCEMENT`, `DUREE_CHOC_S`, `FRACTION_RAYON`,
`INTENSITE_LUEUR` et `COULEUR_LUEUR`. Ils changent l'apparence, jamais les données.

## Résultats avec les réglages par défaut

Billes d'acier de 25 mm, fil de 30 cm, lâcher à 30°, 60 billes :

| Grandeur | Valeur |
|---|---|
| Vitesse d'impact | 0,89 m/s |
| Durée d'un contact | 78 µs |
| Compression maximale | 24 µm |
| Vitesse de l'onde dans la chaîne | **≈ 650 m/s** |
| Son dans une barre d'acier | ≈ 5 050 m/s |
| Traversée des 60 billes | 2,5 ms → ralenti ×1 200 pour 3 s à l'écran |
| Amplification des déplacements | ×32 |

Sur Terre, le long du méridien de Paris (les durées sont aussi dans `meta.json`) :

| Repère | Chaîne de billes (650 m/s) | Barre d'acier (5 050 m/s) |
|---|---|---|
| Alger (1 345 km) | 0 h 34 | 0 h 04 |
| Cotonou (4 722 km) | 2 h 01 | 0 h 16 |
| Antipode (20 004 km) | 8 h 31 | 1 h 06 |
| Retour à Paris (40 008 km) | **17 h 02** | 2 h 12 |

La vitesse de l'onde dépend légèrement de la force du choc (elle varie comme v₀^(1/5)).
Changer l'angle de lâcher modifie donc un peu ces durées.

## Limites à assumer dans le film

- **Chocs parfaitement élastiques, sans frottement** : l'énergie est conservée à 10⁻⁶ près.
  Dans une vraie chaîne, l'onde s'amortirait sur une distance bien plus courte qu'un tour de
  Terre. Les plans terrestres restent une **expérience de pensée** qui prolonge la vitesse calculée.
- **Déplacements amplifiés** (environ 30 µm en réalité) par un facteur unique pour toutes les
  billes. L'interpénétration visible au passage de l'onde correspond à la compression réelle,
  amplifiée du même facteur.
- **Le recul des premières billes est réel** : une chaîne de Hertz n'est pas un pendule de
  Newton idéal. La dernière bille repart avec 98,6 % de la vitesse d'impact, et le reste se
  répartit en petits mouvements résiduels.
- Les fils et la gravité sont négligés pendant les 2,5 ms du choc. Le mouvement est calculé
  sur un seul axe.
- **Plans terrestres** : 600 billes agrandies figurent les 1,6 milliard de billes réelles.
  La lueur et le halo ne font que repérer l'impulsion, dont la largeur réelle (quelques billes,
  une dizaine de centimètres) serait invisible à l'échelle de la Terre.
