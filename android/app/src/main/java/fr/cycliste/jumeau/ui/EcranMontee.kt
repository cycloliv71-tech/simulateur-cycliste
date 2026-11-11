package fr.cycliste.jumeau.ui

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import fr.cycliste.jumeau.modele.MONTEES_CELEBRES
import fr.cycliste.jumeau.modele.Profil
import fr.cycliste.jumeau.modele.arrondi5
import fr.cycliste.jumeau.modele.formaterChrono
import fr.cycliste.jumeau.modele.formaterDuree
import fr.cycliste.jumeau.modele.fr
import fr.cycliste.jumeau.modele.leviers
import fr.cycliste.jumeau.modele.simulerMontee
import fr.cycliste.jumeau.modele.zoneDe
import kotlin.math.abs
import kotlin.math.roundToInt

private val EFFORTS = listOf("Endurance" to 0.70, "Tempo" to 0.85, "Seuil" to 1.00)

@Composable
fun EcranMontee(profil: Profil) {
    val premiere = MONTEES_CELEBRES.first()
    var choix by rememberSaveable { mutableIntStateOf(0) }
    var cleChamps by rememberSaveable { mutableIntStateOf(0) }
    var distance by rememberSaveable { mutableStateOf(premiere.distanceKm) }
    var pente by rememberSaveable { mutableStateOf(premiere.pentePct) }
    var puissance by rememberSaveable { mutableStateOf(arrondi5(profil.ftp * 0.85)) }

    val resultat = profil.simulerMontee(distance, pente, puissance)
    val zone = zoneDe(puissance, profil.ftp)
    val puissanceMax = maxOf(600f, (profil.ftp * 1.6).toFloat())

    EcranDefilant("ecran_MONTEE") {
        EnTete("⛰️ Simulateur de montée", "Combien de temps mettrait ton jumeau pour grimper ce col ?")

        Carte("La montée") {
            Row(
                Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                MONTEES_CELEBRES.forEachIndexed { i, montee ->
                    FilterChip(
                        selected = choix == i,
                        onClick = {
                            choix = i
                            distance = montee.distanceKm
                            pente = montee.pentePct
                            cleChamps++
                        },
                        label = { Text(montee.nom) },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = Couleurs.Accent.copy(alpha = 0.18f),
                            selectedLabelColor = Couleurs.Accent,
                            labelColor = Couleurs.TexteClair,
                        ),
                    )
                }
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                ChampNombre(
                    libelle = "Distance",
                    valeur = distance,
                    suffixe = "km",
                    min = 0.1,
                    max = 200.0,
                    decimales = 1,
                    cle = "distance$cleChamps",
                    modifier = Modifier.weight(1f),
                ) {
                    distance = it
                    choix = -1
                }
                ChampNombre(
                    libelle = "Pente moy.",
                    valeur = pente,
                    suffixe = "%",
                    min = -15.0,
                    max = 30.0,
                    decimales = 1,
                    cle = "pente$cleChamps",
                    modifier = Modifier.weight(1f),
                ) {
                    pente = it
                    choix = -1
                }
            }
            Remarque(
                "Dénivelé : ${resultat.deniveleM.roundToInt()} m. " +
                    "Valeurs des cols approximatives : ajuste-les avec celles de ton parcours.",
            )
        }

        Carte("Ton effort") {
            Curseur(
                "Puissance moyenne",
                "${puissance.roundToInt()} W · ${(puissance / profil.ftp * 100).roundToInt()} % FTP",
                puissance.toFloat(),
                50f..puissanceMax,
                { puissance = arrondi5(it.toDouble()) },
            )
            Row(
                Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                EFFORTS.forEach { (nom, fraction) ->
                    val cible = arrondi5(profil.ftp * fraction)
                    FilterChip(
                        selected = abs(puissance - cible) < 1.0,
                        onClick = { puissance = cible },
                        label = { Text("$nom ${(fraction * 100).roundToInt()} %") },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = Couleurs.Accent2.copy(alpha = 0.22f),
                            selectedLabelColor = Couleurs.Texte,
                            labelColor = Couleurs.TexteClair,
                        ),
                    )
                }
            }
            Remarque("Zone ${zone.zone.numero} · ${zone.zone.nom} — ${zone.zone.description}", couleurZone(zone.zone.numero))
        }

        Carte("Temps estimé") {
            GrosChiffre(formaterChrono(resultat.tempsS), "", etiquette = "temps_montee")
            Remarque(formaterDuree(resultat.tempsS))
            Row(Modifier.fillMaxWidth().height(IntrinsicSize.Min), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Statistique("Vitesse (km/h)", resultat.vitesseKmh.fr(1), Modifier.weight(1f), Couleurs.Accent)
                Statistique("VAM (m/h)", "${resultat.vamMh.roundToInt()}", Modifier.weight(1f), Couleurs.Accent2)
                Statistique(
                    "W/kg",
                    (puissance / profil.poidsCycliste).fr(2),
                    Modifier.weight(1f),
                    Couleurs.Warn,
                )
            }
        }

        Carte("Leviers de progression") {
            Remarque("Ce que ton jumeau gagnerait sur cette montée, à puissance égale :")
            profil.leviers(distance, pente, puissance).forEach { levier ->
                Row(Modifier.fillMaxWidth()) {
                    Text(levier.libelle, fontSize = 15.sp, color = Couleurs.Texte, modifier = Modifier.weight(1f))
                    Text(
                        if (levier.gainS >= 0.5) "−${formaterDuree(levier.gainS)}" else "≈ 0 s",
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = Couleurs.Ok,
                    )
                }
            }
        }

        Carte("Temps selon la puissance") {
            val debut = minOf(profil.ftp * 0.6, puissance).roundToInt()
            val fin = maxOf(profil.ftp * 1.3, puissance).roundToInt()
            val points = (debut..fin step 5).map { w ->
                w.toDouble() to profil.simulerMontee(distance, pente, w.toDouble()).tempsS / 60.0
            }
            Courbe(
                series = listOf(Serie("Temps", points, Couleurs.Accent, 2.5f)),
                libelleX = "Puissance moyenne (W)",
                libelleY = "Temps (min)",
                marqueur = puissance to resultat.tempsS / 60.0,
                depuisZero = false,
            )
        }
    }
}
