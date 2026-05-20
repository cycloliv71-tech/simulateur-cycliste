"""
Simulateur Cycliste – version Streamlit
Lancer en local :  streamlit run streamlit_app.py
"""

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# =====================================================
#                CONFIGURATION DE LA PAGE
# =====================================================
st.set_page_config(
    page_title="Simulateur Cycliste",
    page_icon="🚴",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Palette de couleurs (cohérente avec la version desktop)
COULEURS = {
    "accent":  "#00d4ff",
    "accent2": "#7c5cff",
    "ok":      "#3ddc97",
    "warn":    "#ffb454",
    "danger":  "#ff5f6d",
    "texte_clair": "#9aa6b2",
}

# Style CSS personnalisé
st.markdown(
    """
    <style>
    .big-metric {
        font-size: 56px;
        font-weight: 800;
        color: #00d4ff;
        line-height: 1;
        margin-bottom: 8px;
    }
    .metric-label {
        font-size: 13px;
        color: #9aa6b2;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
    .chip {
        display: inline-block;
        padding: 8px 14px;
        border-radius: 10px;
        font-weight: 600;
        margin-right: 8px;
        margin-bottom: 6px;
        font-size: 14px;
    }
    .chip-grav { background: rgba(124,92,255,0.18); color: #b9a8ff;
                 border: 1px solid #4a3e8a; }
    .chip-rr   { background: rgba(255,180,84,0.16); color: #ffd29a;
                 border: 1px solid #7a5a2c; }
    .chip-aero { background: rgba(0,212,255,0.15); color: #9fe9ff;
                 border: 1px solid #2e6f86; }
    .zone-row {
        display: flex;
        justify-content: space-between;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 8px;
        background: rgba(255,255,255,0.03);
        border-left: 4px solid;
    }
    .zone-name { font-weight: 700; }
    .zone-pct  { color: #9aa6b2; }
    .zone-watts { font-weight: 700; }
    .hero {
        padding: 18px 24px;
        border-radius: 14px;
        background: linear-gradient(90deg, rgba(0,212,255,0.12), rgba(124,92,255,0.12));
        border: 1px solid rgba(0,212,255,0.3);
        margin-bottom: 18px;
    }
    .hero h1 { margin: 0; font-size: 28px; }
    .hero p  { margin: 4px 0 0 0; color: #9aa6b2; }
    </style>
    """,
    unsafe_allow_html=True,
)

# =====================================================
#                EN-TÊTE
# =====================================================
st.markdown(
    """
    <div class="hero">
      <h1>🚴 Simulateur Cycliste</h1>
      <p>Puissance · Graphiques · Physiologie — par Olivier</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# =====================================================
#                FONCTION DE CALCUL
# =====================================================
def calcul_puissance(m, v_kmh, pente_pct, c_rr, cda):
    """Retourne (p_grav, p_rr, p_aero, p_tot) en W."""
    g = 9.81
    rho = 1.225
    pente = pente_pct / 100
    v = v_kmh / 3.6
    p_grav = m * g * pente * v
    p_rr = m * g * c_rr * v
    p_aero = 0.5 * rho * cda * v ** 3
    return p_grav, p_rr, p_aero, p_grav + p_rr + p_aero


def styliser_axes(ax, fig):
    fig.patch.set_facecolor("#0e1117")
    ax.set_facecolor("#1a2330")
    for spine in ax.spines.values():
        spine.set_color("#2f3e54")
    ax.tick_params(colors="#9aa6b2")
    ax.xaxis.label.set_color("#e6edf3")
    ax.yaxis.label.set_color("#e6edf3")
    ax.title.set_color("#e6edf3")
    ax.grid(True, color="#2f3e54", linestyle="--", linewidth=0.6, alpha=0.7)


# =====================================================
#                ONGLETS
# =====================================================
onglet_puissance, onglet_graph, onglet_physio = st.tabs(
    ["⚡ Puissance", "📈 Graphiques", "❤️ Physiologie"]
)


# -----------------------------------------------------
#                ONGLET PUISSANCE
# -----------------------------------------------------
with onglet_puissance:
    st.subheader("Calcul de puissance cycliste")
    st.caption("Estime la puissance en fonction des paramètres et du terrain.")

    col_param, col_resultat = st.columns([1, 1])

    with col_param:
        preset = st.selectbox(
            "Profil",
            [
                "Profil personnalisé",
                "Grimpeur (65 kg · CdA 0.28)",
                "Routier (75 kg · CdA 0.30)",
                "Sprinteur (85 kg · CdA 0.33)",
            ],
        )
        # Valeurs par défaut selon le preset
        if preset.startswith("Grimpeur"):
            poids_default, cda_default = 65.0, 0.28
        elif preset.startswith("Routier"):
            poids_default, cda_default = 75.0, 0.30
        elif preset.startswith("Sprinteur"):
            poids_default, cda_default = 85.0, 0.33
        else:
            poids_default, cda_default = 90.0, 0.30

        poids = st.number_input("Poids (kg)", min_value=30.0, max_value=150.0,
                                value=poids_default, step=0.5)
        vitesse = st.slider("Vitesse (km/h)", min_value=5, max_value=60, value=16)
        pente = st.slider("Pente (%)", min_value=-20, max_value=20, value=8)
        c_rr = st.number_input("Crr (coefficient de roulement)",
                               min_value=0.001, max_value=0.02,
                               value=0.003, step=0.0005, format="%.4f")
        cda = st.number_input("CdA (m²)", min_value=0.10, max_value=0.60,
                              value=cda_default, step=0.01)

    p_grav, p_rr, p_aero, p_tot = calcul_puissance(poids, vitesse, pente, c_rr, cda)

    with col_resultat:
        st.markdown('<div class="metric-label">PUISSANCE TOTALE ESTIMÉE</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="big-metric">{p_tot:.0f} W</div>',
                    unsafe_allow_html=True)

        st.markdown(
            f"""
            <span class="chip chip-grav">Gravité : {p_grav:.0f} W</span>
            <span class="chip chip-rr">Roulement : {p_rr:.0f} W</span>
            <span class="chip chip-aero">Aéro : {p_aero:.0f} W</span>
            """,
            unsafe_allow_html=True,
        )

        # Répartition en pourcentages
        if p_tot > 0:
            st.markdown("&nbsp;", unsafe_allow_html=True)
            st.caption("Répartition de la puissance")
            r_grav = max(0, p_grav) / max(1e-9, abs(p_grav) + p_rr + p_aero) * 100
            r_rr = p_rr / max(1e-9, abs(p_grav) + p_rr + p_aero) * 100
            r_aero = p_aero / max(1e-9, abs(p_grav) + p_rr + p_aero) * 100
            st.progress(min(100, int(r_grav)), text=f"Gravité {r_grav:.0f}%")
            st.progress(min(100, int(r_rr)), text=f"Roulement {r_rr:.0f}%")
            st.progress(min(100, int(r_aero)), text=f"Aéro {r_aero:.0f}%")


# -----------------------------------------------------
#                ONGLET GRAPHIQUES
# -----------------------------------------------------
with onglet_graph:
    st.subheader("Courbe puissance – vitesse")
    st.caption("Visualise la puissance nécessaire de 5 à 60 km/h.")

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        poids_g = st.number_input("Poids (kg) ", min_value=30.0, max_value=150.0,
                                  value=75.0, step=0.5, key="poids_g")
        c_rr_g = st.number_input("Crr ", min_value=0.001, max_value=0.02,
                                 value=0.003, step=0.0005, format="%.4f", key="crr_g")
    with col_g2:
        cda_g = st.number_input("CdA (m²) ", min_value=0.10, max_value=0.60,
                                value=0.30, step=0.01, key="cda_g")
        pente_g = st.slider("Pente (%) ", min_value=-20, max_value=20,
                            value=8, key="pente_g")

    vitesses = np.linspace(5, 60, 100)
    pg, pr, pa, pt = [], [], [], []
    for v_kmh in vitesses:
        a, b, c, t = calcul_puissance(poids_g, v_kmh, pente_g, c_rr_g, cda_g)
        pg.append(a); pr.append(b); pa.append(c); pt.append(t)

    fig, ax = plt.subplots(figsize=(10, 5))
    styliser_axes(ax, fig)
    ax.fill_between(vitesses, 0, pt, color=COULEURS["accent"], alpha=0.10)
    ax.plot(vitesses, pt, color=COULEURS["accent"], lw=2.4, label="Total")
    ax.plot(vitesses, pg, color=COULEURS["accent2"], lw=1.4, ls="--", label="Gravité")
    ax.plot(vitesses, pr, color=COULEURS["warn"], lw=1.4, ls="--", label="Roulement")
    ax.plot(vitesses, pa, color="#9fe9ff", lw=1.4, ls="--", label="Aéro")
    ax.set_xlabel("Vitesse (km/h)")
    ax.set_ylabel("Puissance (W)")
    leg = ax.legend(facecolor="#243042", edgecolor="#2f3e54", loc="upper left")
    for txt in leg.get_texts():
        txt.set_color("#e6edf3")
    fig.tight_layout()
    st.pyplot(fig)


# -----------------------------------------------------
#                ONGLET PHYSIOLOGIE
# -----------------------------------------------------
with onglet_physio:
    st.subheader("Zones de puissance")
    st.caption("Calcule tes zones d'entraînement à partir de la FTP.")

    ftp = st.number_input("FTP (W)", min_value=50.0, max_value=600.0,
                          value=280.0, step=5.0)

    zones = [
        ("Z1 · Récupération",  0.00, 0.55, "#3ddc97"),
        ("Z2 · Endurance",     0.55, 0.75, "#54c1ff"),
        ("Z3 · Tempo",         0.75, 0.90, "#7c5cff"),
        ("Z4 · Seuil",         0.90, 1.05, "#ffb454"),
        ("Z5 · VO2max",        1.05, 1.20, "#ff8a5c"),
        ("Z6 · Anaérobie",     1.20, 1.50, "#ff5f6d"),
    ]

    for nom, bas, haut, couleur in zones:
        html = f"""
        <div class="zone-row" style="border-left-color:{couleur};">
            <div class="zone-name" style="color:{couleur};">{nom}</div>
            <div class="zone-pct">{int(bas*100)} – {int(haut*100)} % FTP</div>
            <div class="zone-watts">{bas*ftp:.0f} – {haut*ftp:.0f} W</div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)


# =====================================================
#                PIED DE PAGE
# =====================================================
st.markdown("---")
st.caption("🚴 Simulateur Cycliste v2.0 — Streamlit edition")
