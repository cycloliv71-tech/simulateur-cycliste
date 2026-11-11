package fr.cycliste.jumeau.ui

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertTextEquals
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextReplacement
import androidx.test.core.app.ApplicationProvider
import fr.cycliste.jumeau.MainActivity
import fr.cycliste.jumeau.donnees.ProfilStore
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/** Lance la vraie application (sans téléphone, grâce à Robolectric) et parcourt les écrans. */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
class ApplicationTest {

    @get:Rule
    val regle = createAndroidComposeRule<MainActivity>()

    @Test
    fun lesQuatreEcransSAffichent() {
        regle.onNodeWithTag("ecran_JUMEAU").assertIsDisplayed()

        regle.onNodeWithTag("onglet_PUISSANCE").performClick()
        regle.onNodeWithTag("ecran_PUISSANCE").assertIsDisplayed()
        // Profil par défaut (90 + 8 kg) à 16 km/h sur 8 %
        regle.onNodeWithTag("puissance_totale").assertTextEquals("371")

        regle.onNodeWithTag("onglet_MONTEE").performClick()
        regle.onNodeWithTag("ecran_MONTEE").assertIsDisplayed()
        regle.onNodeWithTag("temps_montee").assertExists()

        regle.onNodeWithTag("onglet_ZONES").performClick()
        regle.onNodeWithTag("ecran_ZONES").assertIsDisplayed()
        regle.onNodeWithTag("zone_7").assertExists()
    }

    @Test
    fun leJumeauSeMetAJourEtEstEnregistre() {
        regle.onNodeWithTag("resume_wkg").assertTextEquals("3,11")

        regle.onNodeWithTag("champ_poidsCycliste").performTextReplacement("70")
        regle.onNodeWithTag("resume_wkg").assertTextEquals("4,00")

        regle.onNodeWithTag("champ_ftp").performTextReplacement("305")
        regle.onNodeWithTag("resume_wkg").assertTextEquals("4,36")

        val enregistre = ProfilStore(ApplicationProvider.getApplicationContext()).charger()
        assertEquals(70.0, enregistre.poidsCycliste, 0.0)
        assertEquals(305.0, enregistre.ftp, 0.0)
    }
}
