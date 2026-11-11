package fr.cycliste.jumeau.modele

import java.util.Locale
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.log10
import kotlin.math.pow
import kotlin.math.roundToInt
import kotlin.math.roundToLong
import kotlin.math.sqrt

// Ce fichier ne dépend pas d'Android : il contient toute la physique du jumeau
// et peut être testé sur n'importe quelle machine Java.

/** Constantes identiques à la version Streamlit (streamlit_app.py). */
const val GRAVITE = 9.81
const val DENSITE_AIR = 1.225

/** Le jumeau numérique : la morphologie, le vélo et le moteur du cycliste. */
data class Profil(
    val nom: String = "Mon jumeau",
    val poidsCycliste: Double = 90.0,
    val poidsVelo: Double = 8.0,
    val cda: Double = 0.30,
    val crr: Double = 0.003,
    val ftp: Double = 280.0,
) {
    val masseTotale: Double get() = poidsCycliste + poidsVelo
    val wattsParKg: Double get() = if (poidsCycliste > 0.0) ftp / poidsCycliste else 0.0
}

/** Répartition de la puissance, en watts. */
data class Puissances(val gravite: Double, val roulement: Double, val aero: Double) {
    val totale: Double get() = gravite + roulement + aero
}

/** Même formule que calcul_puissance() de la version Streamlit. */
fun calculPuissance(
    masse: Double,
    vitesseKmh: Double,
    pentePct: Double,
    crr: Double,
    cda: Double,
): Puissances {
    val v = vitesseKmh / 3.6
    val pente = pentePct / 100.0
    return Puissances(
        gravite = masse * GRAVITE * pente * v,
        roulement = masse * GRAVITE * crr * v,
        aero = 0.5 * DENSITE_AIR * cda * v * v * v,
    )
}

/** Puissance que le jumeau doit fournir pour tenir cette vitesse sur cette pente. */
fun Profil.puissance(vitesseKmh: Double, pentePct: Double): Puissances =
    calculPuissance(masseTotale, vitesseKmh, pentePct, crr, cda)

/**
 * Calcul inverse : vitesse (km/h) atteinte avec une puissance donnée.
 * Résout a·v³ + b·v = P par dichotomie (une seule solution positive existe).
 * Avec 0 W dans une descente, on obtient la vitesse en roue libre.
 */
fun calculVitesse(
    masse: Double,
    puissanceW: Double,
    pentePct: Double,
    crr: Double,
    cda: Double,
): Double {
    if (!puissanceW.isFinite() || !masse.isFinite()) return 0.0
    val a = 0.5 * DENSITE_AIR * cda.coerceAtLeast(1e-4)
    val b = masse * GRAVITE * (pentePct / 100.0 + crr)
    val p = puissanceW.coerceAtLeast(0.0)
    fun f(v: Double) = a * v * v * v + b * v

    var bas = if (b < 0.0) sqrt(-b / a) else 0.0
    var haut = maxOf(bas, 1.0)
    while (f(haut) < p) haut *= 2.0
    repeat(200) {
        val milieu = (bas + haut) / 2.0
        if (f(milieu) < p) bas = milieu else haut = milieu
    }
    return (bas + haut) / 2.0 * 3.6
}

/** Vitesse (km/h) du jumeau avec cette puissance sur cette pente. */
fun Profil.vitesse(puissanceW: Double, pentePct: Double): Double =
    calculVitesse(masseTotale, puissanceW, pentePct, crr, cda)

// -----------------------------------------------------------------
//                     SIMULATION DE MONTÉE
// -----------------------------------------------------------------

data class Montee(val nom: String, val distanceKm: Double, val pentePct: Double)

/** Quelques cols connus des Alpes (valeurs moyennes approximatives). */
val MONTEES_CELEBRES = listOf(
    Montee("Alpe d'Huez", 13.8, 8.1),
    Montee("Madeleine (La Chambre)", 19.2, 8.0),
    Montee("Galibier (Valloire)", 18.1, 6.9),
    Montee("Iseran (Bonneval)", 13.4, 7.3),
)

data class ResultatMontee(
    val vitesseKmh: Double,
    val tempsS: Double,
    val deniveleM: Double,
    /** Vitesse ascensionnelle moyenne, en mètres par heure. */
    val vamMh: Double,
)

fun Profil.simulerMontee(distanceKm: Double, pentePct: Double, puissanceW: Double): ResultatMontee {
    val vitesseKmh = vitesse(puissanceW, pentePct)
    val distanceM = distanceKm * 1000.0
    val tempsS = if (vitesseKmh > 0.0) distanceM / (vitesseKmh / 3.6) else Double.POSITIVE_INFINITY
    val deniveleM = distanceM * pentePct / 100.0
    val vam = if (tempsS.isFinite() && tempsS > 0.0) deniveleM / tempsS * 3600.0 else 0.0
    return ResultatMontee(vitesseKmh, tempsS, deniveleM, vam)
}

/** Un « levier » : ce que le jumeau gagnerait (en secondes) en changeant un paramètre. */
data class Levier(val libelle: String, val gainS: Double)

fun Profil.leviers(distanceKm: Double, pentePct: Double, puissanceW: Double): List<Levier> {
    val reference = simulerMontee(distanceKm, pentePct, puissanceW).tempsS
    fun gain(autre: Profil, puissance: Double = puissanceW) =
        reference - autre.simulerMontee(distanceKm, pentePct, puissance).tempsS
    return listOf(
        Levier("−2 kg (cycliste ou vélo)", gain(copy(poidsCycliste = poidsCycliste - 2.0))),
        Levier("+10 W de puissance", gain(this, puissanceW + 10.0)),
        Levier("CdA −0,02 m² (position)", gain(copy(cda = (cda - 0.02).coerceAtLeast(0.05)))),
        Levier("Crr −0,001 (pneus)", gain(copy(crr = (crr - 0.001).coerceAtLeast(0.0005)))),
    )
}

// -----------------------------------------------------------------
//                     ZONES DE PUISSANCE
// -----------------------------------------------------------------

/** Les 7 zones de Coggan, les mêmes que celles affichées par Strava. */
data class Zone(
    val numero: Int,
    val nom: String,
    val description: String,
    val pctBas: Double,
    val pctHaut: Double?,
)

val ZONES = listOf(
    Zone(1, "Récupération active", "Très facile, pour récupérer", 0.00, 0.55),
    Zone(2, "Endurance", "Longues sorties, on peut discuter", 0.55, 0.75),
    Zone(3, "Tempo", "Rythme soutenu mais régulier", 0.75, 0.90),
    Zone(4, "Seuil", "Effort tenable environ une heure", 0.90, 1.05),
    Zone(5, "VO2max", "Intervalles de 3 à 8 minutes", 1.05, 1.20),
    Zone(6, "Anaérobie", "Efforts de 30 s à 2 min", 1.20, 1.50),
    Zone(7, "Neuromusculaire", "Sprints très courts", 1.50, null),
)

/** Bornes en watts d'une zone. [maxW] vaut null pour la dernière zone (sans limite). */
data class BornesZone(val zone: Zone, val minW: Int, val maxW: Int?)

fun zonesPour(ftp: Double): List<BornesZone> {
    val hautes = ZONES.map { zone -> zone.pctHaut?.let { (it * ftp).roundToInt() } }
    return ZONES.mapIndexed { i, zone ->
        val min = if (i == 0) 0 else (hautes[i - 1] ?: 0) + 1
        BornesZone(zone, min, hautes[i])
    }
}

fun zoneDe(puissanceW: Double, ftp: Double): BornesZone {
    val p = puissanceW.roundToInt()
    val bornes = zonesPour(ftp)
    return bornes.firstOrNull { it.maxW == null || p <= it.maxW } ?: bornes.last()
}

// -----------------------------------------------------------------
//                     MISE EN FORME
// -----------------------------------------------------------------

/** Nombre au format français (virgule décimale). */
fun Double.fr(decimales: Int = 1): String =
    String.format(Locale.FRANCE, "%.${decimales}f", this)

/** Comme [fr], sans les zéros inutiles : 90,0 → « 90 », 0,0030 → « 0,003 ». */
fun Double.frCompact(decimalesMax: Int): String {
    val texte = fr(decimalesMax)
    return if (texte.contains(',')) texte.trimEnd('0').trimEnd(',') else texte
}

/** 3 912 s → « 1 h 05 min 12 s » ; 754 s → « 12 min 34 s ». */
fun formaterDuree(secondes: Double): String {
    if (!secondes.isFinite() || secondes < 0.0) return "—"
    val total = secondes.roundToLong()
    val h = total / 3600
    val m = (total % 3600) / 60
    val s = total % 60
    return when {
        h > 0 -> String.format(Locale.FRANCE, "%d h %02d min %02d s", h, m, s)
        m > 0 -> String.format(Locale.FRANCE, "%d min %02d s", m, s)
        else -> "$s s"
    }
}

/** Format chronomètre : 3 912 s → « 1:05:12 » ; 754 s → « 12:34 ». */
fun formaterChrono(secondes: Double): String {
    if (!secondes.isFinite() || secondes < 0.0) return "—"
    val total = secondes.roundToLong()
    val h = total / 3600
    val m = (total % 3600) / 60
    val s = total % 60
    return if (h > 0) String.format(Locale.FRANCE, "%d:%02d:%02d", h, m, s)
    else String.format(Locale.FRANCE, "%d:%02d", m, s)
}

/** Graduations « rondes » pour un axe de graphique (1, 2 ou 5 × 10ⁿ). */
fun graduations(min: Double, max: Double, nombreVise: Int): List<Double> {
    val etendue = max - min
    if (!etendue.isFinite() || etendue <= 0.0 || nombreVise < 1) return listOf(min)
    val brut = etendue / nombreVise
    val magnitude = 10.0.pow(floor(log10(brut)))
    val normalise = brut / magnitude
    val pas = magnitude * when {
        normalise < 1.5 -> 1.0
        normalise < 3.0 -> 2.0
        normalise < 7.0 -> 5.0
        else -> 10.0
    }
    val resultat = mutableListOf<Double>()
    var valeur = ceil(min / pas) * pas
    while (valeur <= max + pas * 1e-9) {
        resultat += valeur
        valeur += pas
    }
    return resultat
}

/** Arrondi aux 5 W les plus proches (pour les curseurs de puissance). */
fun arrondi5(valeur: Double): Double = (valeur / 5.0).roundToInt() * 5.0
