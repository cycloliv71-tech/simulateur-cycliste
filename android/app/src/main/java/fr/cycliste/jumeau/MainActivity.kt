package fr.cycliste.jumeau

import android.graphics.Color
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.saveable.rememberSaveableStateHolder
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.sp
import fr.cycliste.jumeau.donnees.ProfilStore
import fr.cycliste.jumeau.modele.Profil
import fr.cycliste.jumeau.ui.Couleurs
import fr.cycliste.jumeau.ui.EcranJumeau
import fr.cycliste.jumeau.ui.EcranMontee
import fr.cycliste.jumeau.ui.EcranPuissance
import fr.cycliste.jumeau.ui.EcranZones
import fr.cycliste.jumeau.ui.ThemeJumeau

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(Color.TRANSPARENT),
        )
        val store = ProfilStore(applicationContext)
        setContent {
            ThemeJumeau { AppJumeau(store) }
        }
    }
}

enum class Onglet(val emoji: String, val libelle: String) {
    JUMEAU("🚴", "Jumeau"),
    PUISSANCE("⚡", "Puissance"),
    MONTEE("⛰️", "Montée"),
    ZONES("❤️", "Zones"),
}

@Composable
fun AppJumeau(store: ProfilStore) {
    var profil by remember { mutableStateOf(store.charger()) }
    var version by rememberSaveable { mutableIntStateOf(0) }
    var onglet by rememberSaveable { mutableStateOf(Onglet.JUMEAU) }
    // Garde l'état de chaque onglet (curseurs, saisies) quand on change d'onglet.
    val etats = rememberSaveableStateHolder()

    val mettreAJour: (Profil) -> Unit = { nouveau ->
        profil = nouveau
        store.enregistrer(nouveau)
    }

    Scaffold(
        containerColor = Couleurs.Fond,
        bottomBar = {
            NavigationBar(containerColor = Couleurs.Surface) {
                Onglet.entries.forEach { o ->
                    NavigationBarItem(
                        selected = onglet == o,
                        onClick = { onglet = o },
                        icon = { Text(o.emoji, fontSize = 20.sp) },
                        label = { Text(o.libelle) },
                        modifier = Modifier.testTag("onglet_${o.name}"),
                    )
                }
            }
        },
    ) { marges ->
        Box(Modifier.padding(marges)) {
            etats.SaveableStateProvider(onglet.name) {
                when (onglet) {
                    Onglet.JUMEAU -> EcranJumeau(
                        profil = profil,
                        version = version,
                        onChange = mettreAJour,
                        onReinitialiser = {
                            mettreAJour(Profil())
                            version++
                        },
                    )
                    Onglet.PUISSANCE -> EcranPuissance(profil)
                    Onglet.MONTEE -> EcranMontee(profil)
                    Onglet.ZONES -> EcranZones(profil, version, mettreAJour)
                }
            }
        }
    }
}
