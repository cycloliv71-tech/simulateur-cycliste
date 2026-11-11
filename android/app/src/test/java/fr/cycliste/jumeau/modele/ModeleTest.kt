package fr.cycliste.jumeau.modele

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ModeleTest {

    @Test
    fun puissanceIdentiqueALaVersionStreamlit() {
        // streamlit_app.py : 90 kg, 16 km/h, 8 %, Crr 0,003, CdA 0,30
        val p = calculPuissance(90.0, 16.0, 8.0, 0.003, 0.30)
        assertEquals(313.92, p.gravite, 1e-6)
        assertEquals(11.772, p.roulement, 1e-6)
        assertEquals(16.1317, p.aero, 1e-3)
        assertEquals(341.82, p.totale, 1e-2)
    }

    @Test
    fun leProfilUtiliseLaMasseDuCyclisteEtDuVelo() {
        val profil = Profil(poidsCycliste = 82.0, poidsVelo = 8.0)
        assertEquals(90.0, profil.masseTotale, 0.0)
        assertEquals(
            calculPuissance(90.0, 20.0, 5.0, profil.crr, profil.cda).totale,
            profil.puissance(20.0, 5.0).totale,
            1e-9,
        )
    }

    @Test
    fun laVitesseEstLInverseDeLaPuissance() {
        val profil = Profil()
        for (pente in listOf(-6.0, -2.0, 0.0, 3.0, 8.0, 12.0)) {
            for (vitesse in listOf(8.0, 15.0, 25.0, 40.0, 55.0)) {
                val p = profil.puissance(vitesse, pente).totale
                if (p <= 0.0) continue
                assertEquals("pente $pente, vitesse $vitesse", vitesse, profil.vitesse(p, pente), 1e-6)
            }
        }
    }

    @Test
    fun enDescenteSansPedalerOnAtteintLaVitesseDeRoueLibre() {
        val profil = Profil()
        val v = profil.vitesse(0.0, -6.0)
        assertTrue(v > 30.0)
        assertEquals(0.0, profil.puissance(v, -6.0).totale, 1e-6)
    }

    @Test
    fun sansPuissanceSurLePlatOnNAvancePas() {
        assertEquals(0.0, Profil().vitesse(0.0, 0.0), 1e-9)
    }

    @Test
    fun simulationDeMonteeCoherente() {
        val profil = Profil()
        val r = profil.simulerMontee(distanceKm = 10.0, pentePct = 8.0, puissanceW = 280.0)
        assertEquals(800.0, r.deniveleM, 1e-9)
        assertEquals(10_000.0 / (r.vitesseKmh / 3.6), r.tempsS, 1e-6)
        assertEquals(800.0 / r.tempsS * 3600.0, r.vamMh, 1e-6)
        // Plus de puissance → plus rapide
        assertTrue(profil.simulerMontee(10.0, 8.0, 300.0).tempsS < r.tempsS)
    }

    @Test
    fun lesLeviersFontGagnerDuTemps() {
        val gains = Profil().leviers(13.8, 8.1, 250.0)
        assertEquals(4, gains.size)
        gains.forEach { assertTrue(it.libelle, it.gainS > 0.0) }
    }

    @Test
    fun zonesIdentiquesAStravaPourUneFtpDe305W() {
        val bornes = zonesPour(305.0)
        assertEquals(7, bornes.size)
        assertEquals(listOf(0, 169, 230, 276, 321, 367, 459), bornes.map { it.minW })
        assertEquals(listOf(168, 229, 275, 320, 366, 458), bornes.dropLast(1).map { it.maxW })
        assertNull(bornes.last().maxW)
    }

    @Test
    fun zoneDUnePuissance() {
        assertEquals(1, zoneDe(100.0, 280.0).zone.numero)
        assertEquals(4, zoneDe(280.0, 280.0).zone.numero)
        assertEquals(7, zoneDe(900.0, 280.0).zone.numero)
    }

    @Test
    fun miseEnForme() {
        assertEquals("1 h 05 min 12 s", formaterDuree(3912.0))
        assertEquals("12 min 34 s", formaterDuree(754.0))
        assertEquals("42 s", formaterDuree(42.0))
        assertEquals("1:05:12", formaterChrono(3912.0))
        assertEquals("12:34", formaterChrono(754.0))
        assertEquals("—", formaterChrono(Double.POSITIVE_INFINITY))
        assertEquals("3,11", (280.0 / 90.0).fr(2))
        assertEquals("90", 90.0.frCompact(1))
        assertEquals("89,5", 89.5.frCompact(1))
        assertEquals("0,003", 0.003.frCompact(4))
        assertEquals("280", 280.0.frCompact(0))
        assertEquals(255.0, arrondi5(253.0), 0.0)
    }

    @Test
    fun graduationsRondes() {
        assertEquals(listOf(0.0, 100.0, 200.0, 300.0, 400.0), graduations(0.0, 420.0, 4))
        assertEquals(listOf(10.0, 20.0, 30.0, 40.0, 50.0, 60.0), graduations(5.0, 60.0, 5))
        assertEquals(listOf(3.0), graduations(3.0, 3.0, 4))
    }
}
