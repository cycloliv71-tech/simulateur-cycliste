package fr.cycliste.jumeau.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import fr.cycliste.jumeau.modele.frCompact
import fr.cycliste.jumeau.modele.graduations
import kotlin.math.roundToInt

private val Arrondi = RoundedCornerShape(16.dp)

/** Colonne défilante commune à tous les écrans. */
@Composable
fun EcranDefilant(etiquette: String, contenu: @Composable ColumnScope.() -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .testTag(etiquette)
            .imePadding()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
        content = contenu,
    )
}

/** Bandeau dégradé en haut de chaque écran (comme le « hero » Streamlit). */
@Composable
fun EnTete(titre: String, sousTitre: String) {
    Column(
        Modifier
            .fillMaxWidth()
            .clip(Arrondi)
            .background(
                Brush.horizontalGradient(
                    listOf(Couleurs.Accent.copy(alpha = 0.14f), Couleurs.Accent2.copy(alpha = 0.14f)),
                ),
            )
            .border(1.dp, Couleurs.Accent.copy(alpha = 0.3f), Arrondi)
            .padding(horizontal = 18.dp, vertical = 14.dp),
    ) {
        Text(
            titre,
            fontSize = 22.sp,
            lineHeight = 28.sp,
            fontWeight = FontWeight.Bold,
            color = Couleurs.Texte,
        )
        Text(sousTitre, fontSize = 14.sp, lineHeight = 20.sp, color = Couleurs.TexteClair)
    }
}

@Composable
fun Carte(
    titre: String? = null,
    modifier: Modifier = Modifier,
    contenu: @Composable ColumnScope.() -> Unit,
) {
    Column(
        modifier
            .fillMaxWidth()
            .clip(Arrondi)
            .background(Couleurs.Surface)
            .border(1.dp, Couleurs.Bordure, Arrondi)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        if (titre != null) {
            Text(
                titre.uppercase(),
                fontSize = 12.sp,
                letterSpacing = 1.sp,
                fontWeight = FontWeight.SemiBold,
                color = Couleurs.TexteClair,
            )
        }
        contenu()
    }
}

/** Grand chiffre mis en avant (puissance, temps…). */
@Composable
fun GrosChiffre(
    valeur: String,
    unite: String,
    couleur: Color = Couleurs.Accent,
    etiquette: String? = null,
) {
    Row(verticalAlignment = Alignment.Bottom) {
        Text(
            valeur,
            fontSize = 52.sp,
            lineHeight = 58.sp,
            fontWeight = FontWeight.ExtraBold,
            color = couleur,
            modifier = Modifier
                .alignByBaseline()
                .then(if (etiquette != null) Modifier.testTag(etiquette) else Modifier),
        )
        if (unite.isNotEmpty()) {
            Spacer(Modifier.width(6.dp))
            Text(
                unite,
                fontSize = 22.sp,
                lineHeight = 28.sp,
                fontWeight = FontWeight.Bold,
                color = couleur.copy(alpha = 0.8f),
                modifier = Modifier.alignByBaseline(),
            )
        }
    }
}

/** Petite tuile « libellé / valeur ». */
@Composable
fun Statistique(
    libelle: String,
    valeur: String,
    modifier: Modifier = Modifier,
    couleur: Color = Couleurs.Texte,
    etiquette: String? = null,
) {
    Column(
        modifier
            .clip(RoundedCornerShape(12.dp))
            .background(couleur.copy(alpha = 0.08f))
            .border(1.dp, couleur.copy(alpha = 0.25f), RoundedCornerShape(12.dp))
            .padding(horizontal = 10.dp, vertical = 8.dp),
    ) {
        Text(libelle, fontSize = 12.sp, lineHeight = 16.sp, color = Couleurs.TexteClair)
        Text(
            valeur,
            fontSize = 18.sp,
            lineHeight = 24.sp,
            fontWeight = FontWeight.Bold,
            color = couleur,
            modifier = if (etiquette != null) Modifier.testTag(etiquette) else Modifier,
        )
    }
}

/** Barre horizontale de répartition (0 à 1). */
@Composable
fun BarreRepartition(libelle: String, fraction: Float, couleur: Color) {
    val f = if (fraction.isFinite()) fraction.coerceIn(0f, 1f) else 0f
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(Modifier.fillMaxWidth()) {
            Text(libelle, fontSize = 13.sp, color = Couleurs.TexteClair, modifier = Modifier.weight(1f))
            Text("${(f * 100).roundToInt()} %", fontSize = 13.sp, color = Couleurs.Texte)
        }
        Box(
            Modifier
                .fillMaxWidth()
                .height(8.dp)
                .clip(RoundedCornerShape(4.dp))
                .background(Couleurs.Bordure),
        ) {
            Box(
                Modifier
                    .fillMaxWidth(f)
                    .fillMaxHeight()
                    .clip(RoundedCornerShape(4.dp))
                    .background(couleur),
            )
        }
    }
}

/** Curseur avec son libellé et sa valeur affichée à droite. */
@Composable
fun Curseur(
    libelle: String,
    valeurAffichee: String,
    valeur: Float,
    plage: ClosedFloatingPointRange<Float>,
    onChange: (Float) -> Unit,
) {
    Column {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(libelle, color = Couleurs.TexteClair, fontSize = 14.sp, modifier = Modifier.weight(1f))
            Text(valeurAffichee, color = Couleurs.Texte, fontWeight = FontWeight.Bold, fontSize = 16.sp)
        }
        Slider(
            value = valeur.coerceIn(plage.start, plage.endInclusive),
            onValueChange = onChange,
            valueRange = plage,
            colors = SliderDefaults.colors(
                thumbColor = Couleurs.Accent,
                activeTrackColor = Couleurs.Accent,
                inactiveTrackColor = Couleurs.Bordure,
            ),
        )
    }
}

/**
 * Champ de saisie d'un nombre. Accepte la virgule comme le point.
 * La valeur n'est transmise que si elle est valide et dans [min, max].
 * Changer [cle] réinitialise le texte affiché à partir de [valeur].
 */
@Composable
fun ChampNombre(
    libelle: String,
    valeur: Double,
    suffixe: String,
    min: Double,
    max: Double,
    decimales: Int,
    cle: Any?,
    modifier: Modifier = Modifier,
    aide: String? = null,
    etiquette: String? = null,
    onValide: (Double) -> Unit,
) {
    var texte by remember(cle) { mutableStateOf(valeur.frCompact(decimales)) }
    val nombre = lireNombre(texte)
    val valide = nombre != null && nombre in min..max
    val message = if (!valide) "Entre ${min.frCompact(decimales)} et ${max.frCompact(decimales)} $suffixe" else aide
    val support: (@Composable () -> Unit)? = if (message == null) null else { { Text(message) } }
    OutlinedTextField(
        value = texte,
        onValueChange = { nouveau ->
            texte = nouveau
            val n = lireNombre(nouveau)
            if (n != null && n in min..max) onValide(n)
        },
        label = { Text(libelle) },
        suffix = { Text(suffixe) },
        isError = !valide,
        supportingText = support,
        singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal, imeAction = ImeAction.Done),
        modifier = modifier
            .fillMaxWidth()
            .then(if (etiquette != null) Modifier.testTag(etiquette) else Modifier),
    )
}

private fun lireNombre(texte: String): Double? =
    texte.trim().replace(',', '.').replace(" ", "").toDoubleOrNull()?.takeIf { it.isFinite() }

/** Une courbe du graphique. */
data class Serie(
    val nom: String,
    val points: List<Pair<Double, Double>>,
    val couleur: Color,
    val epaisseurDp: Float = 2f,
    val pointillee: Boolean = false,
)

/** Graphique en lignes dessiné à la main (aucune bibliothèque externe). */
@Composable
fun Courbe(
    series: List<Serie>,
    libelleX: String,
    libelleY: String,
    marqueur: Pair<Double, Double>? = null,
    formatY: (Double) -> String = { it.roundToInt().toString() },
) {
    val mesureur = rememberTextMeasurer()
    val styleAxe = TextStyle(color = Couleurs.TexteClair, fontSize = 10.sp)
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(libelleY, fontSize = 12.sp, color = Couleurs.TexteClair)
        Canvas(
            Modifier
                .fillMaxWidth()
                .height(210.dp)
                .clipToBounds(),
        ) {
            val tous = series.flatMap { it.points }.filter { it.first.isFinite() && it.second.isFinite() }
            if (tous.isEmpty()) return@Canvas
            val xMin = tous.minOf { it.first }
            val xMax = tous.maxOf { it.first }
            val yMin = minOf(0.0, tous.minOf { it.second })
            var yMax = tous.maxOf { it.second }
            if (yMax <= yMin) yMax = yMin + 1.0
            yMax += (yMax - yMin) * 0.05

            val gauche = 40.dp.toPx()
            val droite = 8.dp.toPx()
            val haut = 6.dp.toPx()
            val bas = 20.dp.toPx()
            val largeur = size.width - gauche - droite
            val hauteur = size.height - haut - bas
            val etendueX = if (xMax > xMin) xMax - xMin else 1.0
            fun px(x: Double) = (gauche + (x - xMin) / etendueX * largeur).toFloat()
            fun py(y: Double) = (haut + hauteur - (y - yMin) / (yMax - yMin) * hauteur).toFloat()
            val tirets = PathEffect.dashPathEffect(floatArrayOf(8f, 8f))

            for (g in graduations(yMin, yMax, 4)) {
                val y = py(g)
                drawLine(Couleurs.Bordure, Offset(gauche, y), Offset(size.width - droite, y), 1f, pathEffect = tirets)
                val t = mesureur.measure(formatY(g), styleAxe)
                drawText(t, topLeft = Offset(gauche - t.size.width - 6.dp.toPx(), y - t.size.height / 2f))
            }
            for (g in graduations(xMin, xMax, 5)) {
                val x = px(g)
                val t = mesureur.measure(g.roundToInt().toString(), styleAxe)
                drawText(t, topLeft = Offset(x - t.size.width / 2f, size.height - bas + 4.dp.toPx()))
            }
            if (yMin < 0.0) {
                drawLine(
                    Couleurs.TexteClair.copy(alpha = 0.5f),
                    Offset(gauche, py(0.0)),
                    Offset(size.width - droite, py(0.0)),
                    1.dp.toPx(),
                )
            }
            for (serie in series) {
                val valides = serie.points.filter { it.first.isFinite() && it.second.isFinite() }
                if (valides.size < 2) continue
                val chemin = Path()
                valides.forEachIndexed { i, (x, y) ->
                    if (i == 0) chemin.moveTo(px(x), py(y)) else chemin.lineTo(px(x), py(y))
                }
                drawPath(
                    chemin,
                    serie.couleur,
                    style = Stroke(
                        width = serie.epaisseurDp.dp.toPx(),
                        cap = StrokeCap.Round,
                        pathEffect = if (serie.pointillee) tirets else null,
                    ),
                )
            }
            if (marqueur != null && marqueur.first.isFinite() && marqueur.second.isFinite()) {
                val centre = Offset(px(marqueur.first), py(marqueur.second))
                drawLine(
                    Couleurs.Accent.copy(alpha = 0.5f),
                    Offset(centre.x, haut),
                    Offset(centre.x, haut + hauteur),
                    1.dp.toPx(),
                    pathEffect = tirets,
                )
                drawCircle(Couleurs.Fond, 7.dp.toPx(), centre)
                drawCircle(Couleurs.Accent, 5.dp.toPx(), centre)
            }
        }
        Text(
            libelleX,
            fontSize = 12.sp,
            color = Couleurs.TexteClair,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth(),
        )
        if (series.size > 1) Legende(series)
    }
}

@Composable
private fun Legende(series: List<Serie>) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        series.chunked(2).forEach { ligne ->
            Row(Modifier.fillMaxWidth()) {
                ligne.forEach { serie ->
                    Row(Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            Modifier
                                .width(18.dp)
                                .height(3.dp)
                                .background(serie.couleur),
                        )
                        Spacer(Modifier.width(6.dp))
                        Text(serie.nom, fontSize = 12.sp, color = Couleurs.Texte)
                    }
                }
                if (ligne.size == 1) Spacer(Modifier.weight(1f))
            }
        }
    }
}

/** Texte secondaire (aide, remarque). */
@Composable
fun Remarque(texte: String, couleur: Color = Couleurs.TexteClair) {
    Text(texte, fontSize = 13.sp, lineHeight = 18.sp, color = couleur, style = MaterialTheme.typography.bodySmall)
}
