package fr.cycliste.jumeau.donnees

import android.content.Context
import fr.cycliste.jumeau.modele.Profil

/** Enregistre le jumeau dans le téléphone (rien n'est envoyé sur Internet). */
class ProfilStore(context: Context) {

    private val prefs = context.getSharedPreferences("jumeau", Context.MODE_PRIVATE)

    fun charger(): Profil {
        val defaut = Profil()
        return Profil(
            nom = prefs.getString(NOM, null) ?: defaut.nom,
            poidsCycliste = lire(POIDS_CYCLISTE, defaut.poidsCycliste),
            poidsVelo = lire(POIDS_VELO, defaut.poidsVelo),
            cda = lire(CDA, defaut.cda),
            crr = lire(CRR, defaut.crr),
            ftp = lire(FTP, defaut.ftp),
        )
    }

    fun enregistrer(profil: Profil) {
        prefs.edit()
            .putString(NOM, profil.nom)
            .putLong(POIDS_CYCLISTE, profil.poidsCycliste.toRawBits())
            .putLong(POIDS_VELO, profil.poidsVelo.toRawBits())
            .putLong(CDA, profil.cda.toRawBits())
            .putLong(CRR, profil.crr.toRawBits())
            .putLong(FTP, profil.ftp.toRawBits())
            .apply()
    }

    private fun lire(cle: String, defaut: Double): Double =
        if (prefs.contains(cle)) Double.fromBits(prefs.getLong(cle, 0L)) else defaut

    private companion object {
        const val NOM = "nom"
        const val POIDS_CYCLISTE = "poidsCycliste"
        const val POIDS_VELO = "poidsVelo"
        const val CDA = "cda"
        const val CRR = "crr"
        const val FTP = "ftp"
    }
}
