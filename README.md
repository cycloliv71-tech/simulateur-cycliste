# simulateur-cycliste
Permet de réaliser des calculs de puissance

## Version web (Streamlit)

```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Application Android « Jumeau Cycliste »

Le dossier [`android/`](android/) contient une application Android native (Kotlin, Jetpack Compose)
construite autour de ton **jumeau numérique** : un profil (poids, vélo, CdA, Crr, FTP) enregistré
dans le téléphone et utilisé par tous les calculs.

| Onglet | Ce qu'il fait |
| --- | --- |
| 🚴 Jumeau | Saisie du profil, et ce que le jumeau donne à FTP (vitesse sur le plat, sur 8 %, VAM, W/kg) |
| ⚡ Puissance | Puissance nécessaire selon la vitesse et la pente, avec la répartition gravité / roulement / aéro et la courbe puissance – vitesse |
| ⛰️ Montée | Temps estimé sur un col (Alpe d'Huez, Madeleine, Galibier, Iseran ou montée personnalisée), VAM, et ce que rapporteraient 2 kg en moins, 10 W en plus, une meilleure position ou de meilleurs pneus |
| ❤️ Zones | Les 7 zones de puissance calculées depuis la FTP (les mêmes que Strava) |

Les calculs reprennent la formule de `streamlit_app.py` (gravité + roulement + aérodynamique), en
ajoutant le poids du vélo à celui du cycliste.

### Installer l'APK sur le téléphone

L'APK est construit automatiquement par GitHub Actions à chaque modification du dossier `android/` :

- **Page Releases** du dépôt (versions publiées depuis la branche `main`) : ouvre-la sur le téléphone
  et télécharge `jumeau-cycliste.apk`.
- **Onglet Actions** → « Application Android » → dernier passage → artefact `jumeau-cycliste-apk`
  (un fichier zip qui contient l'APK).

À l'ouverture de l'APK, Android demande d'autoriser l'installation depuis cette source.
Toutes les versions sont signées avec la même clé (`android/app/debug.keystore`) : une nouvelle version
s'installe par-dessus l'ancienne sans effacer ton jumeau.

### Compiler soi-même

Il faut le SDK Android (par exemple via Android Studio) et Java 17 :

```
cd android
./gradlew testDebugUnitTest assembleDebug
```

L'APK se trouve dans `android/app/build/outputs/apk/debug/`.
