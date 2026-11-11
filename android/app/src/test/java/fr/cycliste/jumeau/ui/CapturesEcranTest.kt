package fr.cycliste.jumeau.ui

import android.graphics.Bitmap
import android.graphics.Canvas
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import fr.cycliste.jumeau.MainActivity
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File

/**
 * Prend une capture de chaque écran (rendu réel, sans téléphone) dans app/build/captures.
 * L'écran simulé est très haut pour que tout le contenu tienne sur une seule image.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [34], qualifiers = "w360dp-h1900dp-hdpi")
class CapturesEcranTest {

    @get:Rule
    val regle = createAndroidComposeRule<MainActivity>()

    @Test
    fun capturerLesQuatreEcrans() {
        val dossier = File("build/captures").apply { mkdirs() }
        listOf("JUMEAU", "PUISSANCE", "MONTEE", "ZONES").forEachIndexed { i, onglet ->
            regle.onNodeWithTag("onglet_$onglet").performClick()
            regle.waitForIdle()
            val vue = regle.activity.window.decorView
            val image = Bitmap.createBitmap(vue.width, vue.height, Bitmap.Config.ARGB_8888)
            regle.runOnUiThread { vue.draw(Canvas(image)) }
            File(dossier, "${i + 1}_$onglet.png").outputStream().use {
                image.compress(Bitmap.CompressFormat.PNG, 100, it)
            }
        }
    }
}
