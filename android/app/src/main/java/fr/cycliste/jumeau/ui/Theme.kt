package fr.cycliste.jumeau.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

/** Palette reprise de la version Streamlit (.streamlit/config.toml). */
object Couleurs {
    val Accent = Color(0xFF00D4FF)
    val Accent2 = Color(0xFF7C5CFF)
    val Ok = Color(0xFF3DDC97)
    val Warn = Color(0xFFFFB454)
    val Danger = Color(0xFFFF5F6D)
    val AeroClair = Color(0xFF9FE9FF)
    val Texte = Color(0xFFE6EDF3)
    val TexteClair = Color(0xFF9AA6B2)
    val Fond = Color(0xFF0F1720)
    val Surface = Color(0xFF1A2330)
    val SurfaceHaute = Color(0xFF243042)
    val Bordure = Color(0xFF2F3E54)
}

/** Couleur de chaque zone de puissance (Z1 → Z7). */
val CouleursZones = listOf(
    Color(0xFF3DDC97),
    Color(0xFF54C1FF),
    Color(0xFF7C5CFF),
    Color(0xFFFFB454),
    Color(0xFFFF8A5C),
    Color(0xFFFF5F6D),
    Color(0xFFFF4FA3),
)

fun couleurZone(numero: Int): Color = CouleursZones[(numero - 1).coerceIn(0, CouleursZones.lastIndex)]

private val schema = darkColorScheme(
    primary = Couleurs.Accent,
    onPrimary = Color(0xFF00151C),
    secondary = Couleurs.Accent2,
    onSecondary = Color.White,
    tertiary = Couleurs.Ok,
    background = Couleurs.Fond,
    onBackground = Couleurs.Texte,
    surface = Couleurs.Fond,
    onSurface = Couleurs.Texte,
    surfaceVariant = Couleurs.SurfaceHaute,
    onSurfaceVariant = Couleurs.TexteClair,
    outline = Color(0xFF3B4C64),
    outlineVariant = Couleurs.Bordure,
    error = Couleurs.Danger,
    onError = Color.Black,
    secondaryContainer = Color(0xFF16394A),
    onSecondaryContainer = Couleurs.Accent,
    surfaceContainerLowest = Color(0xFF0B121A),
    surfaceContainerLow = Color(0xFF141C27),
    surfaceContainer = Couleurs.Surface,
    surfaceContainerHigh = Color(0xFF1F2A38),
    surfaceContainerHighest = Couleurs.SurfaceHaute,
)

@Composable
fun ThemeJumeau(contenu: @Composable () -> Unit) {
    MaterialTheme(colorScheme = schema, content = contenu)
}
