package fr.cycliste.jumeau.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import fr.cycliste.jumeau.modele.Profil
import fr.cycliste.jumeau.modele.fr
import fr.cycliste.jumeau.modele.frCompact
import fr.cycliste.jumeau.modele.puissance
import fr.cycliste.jumeau.modele.simulerMontee
import fr.cycliste.jumeau.modele.vitesse
import kotlin.math.roundToInt

@Composable
fun EcranJumeau(
    profil: Profil,
    version: Int,
    onChange: (Profil) -> Unit,
    onReinitialiser: () -> Unit,
) {
    EcranDefilant("ecran_JUMEAU") {
        EnTete(
            "🚴 Mon jumeau numérique",
            "Ton double virtuel roule avec ta morphologie, ton vélo et ton moteur. " +
                "Tous les calculs de l'appli utilisent ce profil.",
        )

        CarteResume(profil)

        Carte("Identité") {
            var nom by remember(version) { mutableStateOf(profil.nom) }
            OutlinedTextField(
                value = nom,
                onValueChange = { saisi ->
                    val texte = saisi.take(30)
                    nom = texte
                    onChange(profil.copy(nom = texte))
                },
                label = { Text("Nom du jumeau") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
        }

        Carte("Corps et machine") {
            ChampNombre(
                libelle = "Poids du cycliste",
                valeur = profil.poidsCycliste,
                suffixe = "kg",
                min = 30.0,
                max = 200.0,
                decimales = 1,
                cle = version,
                aide = "Ton poids, que tu peux reprendre de Strava",
                etiquette = "champ_poidsCycliste",
            ) { onChange(profil.copy(poidsCycliste = it)) }
            ChampNombre(
                libelle = "Poids du vélo équipé",
                valeur = profil.poidsVelo,
                suffixe = "kg",
                min = 0.0,
                max = 40.0,
                decimales = 1,
                cle = version,
                aide = "Vélo, bidons, sacoche…",
            ) { onChange(profil.copy(poidsVelo = it)) }
            Remarque("Masse totale simulée : ${profil.masseTotale.frCompact(1)} kg")
        }

        Carte("Aérodynamique et roulement") {
            ChampNombre(
                libelle = "CdA",
                valeur = profil.cda,
                suffixe = "m²",
                min = 0.10,
                max = 0.80,
                decimales = 3,
                cle = version,
                aide = "≈ 0,25 en contre-la-montre · 0,30 mains en bas · 0,38 mains en haut",
            ) { onChange(profil.copy(cda = it)) }
            ChampNombre(
                libelle = "Crr (résistance au roulement)",
                valeur = profil.crr,
                suffixe = "",
                min = 0.001,
                max = 0.03,
                decimales = 4,
                cle = version,
                aide = "≈ 0,003 route lisse · 0,005 route abîmée · 0,008 gravier",
            ) { onChange(profil.copy(crr = it)) }
        }

        Carte("Moteur") {
            ChampNombre(
                libelle = "FTP",
                valeur = profil.ftp,
                suffixe = "W",
                min = 50.0,
                max = 700.0,
                decimales = 0,
                cle = version,
                aide = "Puissance tenable environ une heure",
                etiquette = "champ_ftp",
            ) { onChange(profil.copy(ftp = it)) }
        }

        OutlinedButton(onClick = onReinitialiser, modifier = Modifier.fillMaxWidth()) {
            Text("Remettre les valeurs par défaut")
        }
        Remarque("Ton jumeau est enregistré uniquement sur ce téléphone.")
    }
}

@Composable
private fun CarteResume(profil: Profil) {
    val vitessePlat = profil.vitesse(profil.ftp, 0.0)
    val montee = profil.simulerMontee(distanceKm = 1.0, pentePct = 8.0, puissanceW = profil.ftp)
    val puissance30 = profil.puissance(30.0, 0.0).totale

    Carte(profil.nom.ifBlank { "Mon jumeau" }) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Statistique(
                "W/kg à FTP",
                profil.wattsParKg.fr(2),
                Modifier.weight(1f),
                Couleurs.Accent,
                etiquette = "resume_wkg",
            )
            Statistique("FTP", "${profil.ftp.roundToInt()} W", Modifier.weight(1f), Couleurs.Accent2)
            Statistique("Masse", "${profil.masseTotale.frCompact(1)} kg", Modifier.weight(1f), Couleurs.Warn)
        }
        Text("À ta FTP, ton jumeau roule…", fontSize = 14.sp, color = Couleurs.TexteClair)
        LigneResume("sur le plat", "${vitessePlat.fr(1)} km/h")
        LigneResume("sur une pente de 8 %", "${montee.vitesseKmh.fr(1)} km/h")
        LigneResume("en vitesse ascensionnelle (8 %)", "${montee.vamMh.roundToInt()} m/h")
        LigneResume("Pour 30 km/h sur le plat, il faut", "${puissance30.roundToInt()} W")
    }
}

@Composable
private fun LigneResume(libelle: String, valeur: String) {
    Row(Modifier.fillMaxWidth()) {
        Text(libelle, fontSize = 15.sp, color = Couleurs.Texte, modifier = Modifier.weight(1f))
        Text(valeur, fontSize = 15.sp, fontWeight = FontWeight.Bold, color = Couleurs.Accent)
    }
}
