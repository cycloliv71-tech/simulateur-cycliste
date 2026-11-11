package fr.cycliste.jumeau.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import fr.cycliste.jumeau.modele.BornesZone
import fr.cycliste.jumeau.modele.Profil
import fr.cycliste.jumeau.modele.zonesPour
import kotlin.math.roundToInt

@Composable
fun EcranZones(profil: Profil, version: Int, onChange: (Profil) -> Unit) {
    EcranDefilant("ecran_ZONES") {
        EnTete(
            "❤️ Zones de puissance",
            "7 zones calculées à partir de la FTP de ton jumeau (modèle de Coggan, comme Strava).",
        )
        Carte {
            ChampNombre(
                libelle = "FTP",
                valeur = profil.ftp,
                suffixe = "W",
                min = 50.0,
                max = 700.0,
                decimales = 0,
                cle = version,
                aide = "Modifie-la ici ou dans « Mon jumeau »",
            ) { onChange(profil.copy(ftp = it)) }
        }
        zonesPour(profil.ftp).forEach { LigneZone(it) }
    }
}

@Composable
private fun LigneZone(bornes: BornesZone) {
    val zone = bornes.zone
    val couleur = couleurZone(zone.numero)
    val forme = RoundedCornerShape(10.dp)
    val pourcentages = if (zone.pctHaut == null) {
        "> ${(zone.pctBas * 100).roundToInt()} % FTP"
    } else {
        "${(zone.pctBas * 100).roundToInt()} – ${(zone.pctHaut * 100).roundToInt()} % FTP"
    }
    val watts = if (bornes.maxW == null) "≥ ${bornes.minW} W" else "${bornes.minW} – ${bornes.maxW} W"

    Row(
        Modifier
            .fillMaxWidth()
            .height(IntrinsicSize.Min)
            .clip(forme)
            .background(Couleurs.Surface)
            .border(1.dp, Couleurs.Bordure, forme)
            .testTag("zone_${zone.numero}"),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            Modifier
                .width(5.dp)
                .fillMaxHeight()
                .background(couleur),
        )
        Column(
            Modifier
                .weight(1f)
                .padding(horizontal = 12.dp, vertical = 10.dp),
        ) {
            Text(
                "Z${zone.numero} · ${zone.nom}",
                fontWeight = FontWeight.Bold,
                fontSize = 16.sp,
                lineHeight = 22.sp,
                color = couleur,
            )
            Text(pourcentages, fontSize = 12.sp, lineHeight = 16.sp, color = Couleurs.TexteClair)
            Text(zone.description, fontSize = 12.sp, lineHeight = 16.sp, color = Couleurs.TexteClair)
        }
        Text(
            watts,
            fontWeight = FontWeight.Bold,
            fontSize = 16.sp,
            color = Couleurs.Texte,
            modifier = Modifier.padding(end = 14.dp),
        )
    }
}
