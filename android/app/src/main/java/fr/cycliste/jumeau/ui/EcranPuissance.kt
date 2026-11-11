package fr.cycliste.jumeau.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import fr.cycliste.jumeau.modele.Profil
import fr.cycliste.jumeau.modele.fr
import fr.cycliste.jumeau.modele.puissance
import fr.cycliste.jumeau.modele.vitesse
import fr.cycliste.jumeau.modele.zoneDe
import kotlin.math.abs
import kotlin.math.roundToInt

@Composable
fun EcranPuissance(profil: Profil) {
    // Mêmes valeurs de départ que la version Streamlit : 16 km/h sur 8 %.
    var vitesse by rememberSaveable { mutableStateOf(16.0) }
    var pente by rememberSaveable { mutableStateOf(8.0) }
    val p = profil.puissance(vitesse, pente)
    val total = p.totale

    EcranDefilant("ecran_PUISSANCE") {
        EnTete("⚡ Puissance", "Combien de watts faut-il à ton jumeau pour tenir cette vitesse ?")

        Carte("Terrain") {
            Curseur("Vitesse", "${vitesse.fr(1)} km/h", vitesse.toFloat(), 5f..60f, {
                vitesse = (it * 2f).roundToInt() / 2.0
            })
            Curseur("Pente", "${pente.fr(1)} %", pente.toFloat(), -20f..20f, {
                pente = (it * 2f).roundToInt() / 2.0
            })
        }

        Carte("Puissance nécessaire") {
            GrosChiffre("${total.coerceAtLeast(0.0).roundToInt()}", "W", etiquette = "puissance_totale")
            if (total > 0.0) {
                val zone = zoneDe(total, profil.ftp)
                Remarque(
                    "${(total / profil.poidsCycliste).fr(2)} W/kg · " +
                        "${(total / profil.ftp * 100).roundToInt()} % de ta FTP · " +
                        "Z${zone.zone.numero} ${zone.zone.nom}",
                    couleurZone(zone.zone.numero),
                )
            } else {
                Remarque(
                    "La pente suffit : roue libre ! Il y a ${(-total).roundToInt()} W de trop, " +
                        "ton jumeau doit freiner pour rester à cette vitesse.",
                    Couleurs.Ok,
                )
            }

            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Statistique("Gravité", "${p.gravite.roundToInt()} W", Modifier.weight(1f), Couleurs.Accent2)
                Statistique("Roulement", "${p.roulement.roundToInt()} W", Modifier.weight(1f), Couleurs.Warn)
                Statistique("Aéro", "${p.aero.roundToInt()} W", Modifier.weight(1f), Couleurs.AeroClair)
            }

            val somme = p.gravite.coerceAtLeast(0.0) + p.roulement + p.aero
            if (somme > 0.0) {
                BarreRepartition("Gravité", (p.gravite.coerceAtLeast(0.0) / somme).toFloat(), Couleurs.Accent2)
                BarreRepartition("Roulement", (p.roulement / somme).toFloat(), Couleurs.Warn)
                BarreRepartition("Aéro", (p.aero / somme).toFloat(), Couleurs.AeroClair)
            }

            val vitesseFtp = profil.vitesse(profil.ftp, pente)
            val ecart = vitesseFtp - vitesse
            Remarque(
                "À ta FTP (${profil.ftp.roundToInt()} W) sur cette pente, ton jumeau roulerait à " +
                    "${vitesseFtp.fr(1)} km/h" +
                    if (abs(ecart) < 0.05) "." else " (${if (ecart > 0) "+" else "−"}${abs(ecart).fr(1)} km/h).",
            )
        }

        Carte("Courbe puissance – vitesse") {
            val vitesses = (10..120).map { it / 2.0 } // 5 à 60 km/h
            val points = vitesses.map { v -> v to profil.puissance(v, pente) }
            Courbe(
                series = listOf(
                    Serie("Total", points.map { (v, q) -> v to q.totale }, Couleurs.Accent, 2.5f),
                    Serie("Gravité", points.map { (v, q) -> v to q.gravite }, Couleurs.Accent2, 1.5f, true),
                    Serie("Roulement", points.map { (v, q) -> v to q.roulement }, Couleurs.Warn, 1.5f, true),
                    Serie("Aéro", points.map { (v, q) -> v to q.aero }, Couleurs.AeroClair, 1.5f, true),
                ),
                libelleX = "Vitesse (km/h)",
                libelleY = "Puissance (W) sur ${pente.fr(1)} %",
                marqueur = vitesse to total,
            )
        }
    }
}
