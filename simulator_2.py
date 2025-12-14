import streamlit as st
import pandas as pd
import time
import base64

# ================= 1. ETATS DE SESSION (MÉMOIRE) =================
if 'premium_user' not in st.session_state:
    st.session_state.premium_user = False
if 'show_login' not in st.session_state:
    st.session_state.show_login = False
if 'ai_mode' not in st.session_state:
    st.session_state.ai_mode = False

# ================= 2. CSS SPÉCIFIQUE (BIG BUTTON & LOGIN) =================
st.markdown("""
<style>
    /* --- STYLE DU GROS BOUTON AI (Rose Néon) --- */
    .premium-btn > button {
        border: 3px solid #ff00ff !important; /* Bordure plus épaisse */
        color: #ff00ff !important;
        background-color: rgba(255, 0, 255, 0.05) !important; /* Fond très léger */
       
        /* TAILLE XXL */
        font-size: 22px !important;
        font-weight: 900 !important; /* Ultra Gras */
        padding: 15px 10px !important; /* Hauteur du bouton */
        margin-top: 10px !important;
       
        text-transform: uppercase;
        width: 100%;
        letter-spacing: 3px;
       
        /* EFFET DE BRILLANCE PERMANENT */
        box-shadow: 0 0 15px rgba(255, 0, 255, 0.4);
        transition: all 0.3s ease-in-out;
    }

    /* AU SURVOL DE LA SOURIS */
    .premium-btn > button:hover {
        background: #ff00ff !important;
        color: white !important;
        box-shadow: 0 0 40px #ff00ff !important; /* Gros flash lumineux */
        transform: scale(1.05); /* Le bouton grossit un peu */
    }
   
    /* BOUTON SWITCH IA (Quand on a payé) */
    .ai-active-btn > button {
        border: 2px solid #00ffcc !important;
        color: #000 !important;
        background: #00ffcc !important;
        font-weight: bold;
    }

    /* --- STYLE DE LA BOITE DE LOGIN --- */
    .login-container {
        max_width: 600px;
        margin: 50px auto;
        padding: 50px;
        background: #111;
        border: 2px solid #ff00ff;
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 0 80px rgba(255, 0, 255, 0.15);
    }
    .login-title {
        font-family: 'Orbitron', sans-serif;
        color: #ff00ff;
        font-size: 2.5em;
        margin-bottom: 10px;
        text-shadow: 0 0 10px #ff00ff;
    }
</style>
""", unsafe_allow_html=True)

# ================= 3. LOGIQUE DE NAVIGATION =================

def go_to_login():
    st.session_state.show_login = True

def unlock_premium():
    st.session_state.premium_user = True
    st.session_state.ai_mode = True
    st.session_state.show_login = False
    st.rerun()

# ================= 4. PAGE DE PAIEMENT (PAYWALL) =================
if st.session_state.show_login and not st.session_state.premium_user:
   
    st.markdown("""
    <div class="login-container">
        <div class="login-title"> AI ENTERPRISE</div>
        <p style="color:#eee; font-size: 1.2em;">Débloquez nos algorithmes de réseaux de neurones pour optimiser vos rendements en temps réel.</p>
        <h1 style="color:#fff; margin-top:20px;">499 € <span style="font-size:0.5em">/ mois</span></h1>
    </div>
    """, unsafe_allow_html=True)
   
    col_spacer1, col_form, col_spacer2 = st.columns([1, 1, 1])
    with col_form:
        with st.form("payment_form"):
            st.text_input("Email Professionnel")
            st.text_input("Numéro de Carte", type="password")
            st.markdown("🔒 *Paiement Sécurisé SSL*")
           
            # Bouton de validation large
            if st.form_submit_button("ACTIVER L'ABONNEMENT", type="primary", use_container_width=True):
                with st.spinner("Validation de la transaction..."):
                    time.sleep(1.5)
                    unlock_premium()
   
    if st.button("← Retour au mode gratuit"):
        st.session_state.show_login = False
        st.rerun()
       
    st.stop()


# ================= 5. HEADER PRINCIPAL =================

col_header_L, col_header_R = st.columns([2.5, 1])

with col_header_L:
    st.title("REAKT")

with col_header_R:
    # Si PAS premium : GROS BOUTON ROSE
    if not st.session_state.premium_user:
        st.markdown('<div class="premium-btn">', unsafe_allow_html=True)
        st.button(" OPTIMIZE WITH AI", on_click=go_to_login)
        st.markdown('</div>', unsafe_allow_html=True)
       
    # Si PREMIUM : Switch
    else:
        st.write("") # Spacer pour aligner verticalement
        if st.session_state.ai_mode:
            st.markdown('<div class="ai-active-btn">', unsafe_allow_html=True)
            st.button("🔄 SWITCH TO MANUAL", on_click=lambda: st.session_state.update(ai_mode=False))
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.button("🤖 SWITCH TO AI MODE", on_click=lambda: st.session_state.update(ai_mode=True))

st.markdown("---")

# ... METS LA SUITE DE TON CODE (BIOREACTEUR) ICI ...
# ================= 1. CONFIGURATION GLOBALE =================
st.set_page_config(page_title="Bioreactor Supervisor", layout="wide", page_icon="🧪")

# ================= 2. STYLE CSS (DARK INDUSTRIAL) =================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Roboto+Mono:wght@400;700&display=swap');
   
    /* FOND GÉNÉRAL */
    .stApp { background-color: #0e0e0e; color: #ffffff; }
   
    /* TITRES */
    h1, h2, h3 {
        font-family: 'Orbitron', sans-serif;
        color: #00ffcc !important;
        text-transform: uppercase;
        letter-spacing: 2px;
        border-bottom: 1px solid #333;
        padding-bottom: 10px;
    }
   
    /* TEXTE BLANC PUR POUR LES INPUTS */
    .stSlider p, .stNumberInput p, .stCheckbox p, .stMarkdown p, label, .stCaption {
        color: #ffffff !important;
        font-family: 'Roboto Mono', monospace;
        font-weight: bold;
    }
   
    /* Valeurs au dessus du curseur du slider */
    div[data-testid="stThumbValue"] { color: #00ffcc !important; }
   
    /* BOITES KPI */
    .kpi-card {
        background: linear-gradient(145deg, #1a1a1a, #222);
        border: 1px solid #333;
        border-left: 4px solid #00ffcc;
        padding: 15px;
        margin: 5px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        text-align: center;
    }
    .kpi-title { font-family: 'Roboto Mono', monospace; font-size: 0.8em; color: #aaa; text-transform: uppercase; }
    .kpi-value { font-family: 'Orbitron', sans-serif; font-size: 1.8em; color: #fff; font-weight: bold; text-shadow: 0 0 5px rgba(0, 255, 204, 0.3); }
    .kpi-unit { font-size: 0.5em; color: #00ffcc; }
   
    /* BOUTONS CUSTOM */
    .stButton>button {
        background: transparent;
        border: 2px solid #00ffcc;
        color: #00ffcc;
        font-family: 'Orbitron', sans-serif;
        transition: 0.3s;
        width: 100%;
        text-transform: uppercase;
    }
    .stButton>button:hover {
        background: #00ffcc;
        color: black;
        box-shadow: 0 0 15px #00ffcc;
    }
</style>
""", unsafe_allow_html=True)

# ================= 3. FONCTIONS VISUELLES (SVG) =================
def get_reactor_svg(level_percent, rpm, temp):
    """Génère le SVG animé de la cuve"""
    # Animation de rotation (purement visuelle ici, fixée par le code ou un paramètre caché)
    rot_duration = f"{60000 / (rpm + 1)}ms" if rpm > 0 else "0s"
   
    # Couleur liquide selon Température
    if temp < 30: liq_color = "#00bfff" # Froid (Bleu)
    elif temp < 45: liq_color = "#00ffcc" # Optimal (Vert)
    else: liq_color = "#ff4444" # Chaud (Rouge)

    liq_height = 200 * (level_percent / 100)
    liq_y = 250 - liq_height

    svg = f"""
    <svg width="300" height="400" viewBox="0 0 300 400" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="steel" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" style="stop-color:#333"/><stop offset="50%" style="stop-color:#eee"/><stop offset="100%" style="stop-color:#333"/></linearGradient>
            <linearGradient id="glass" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#fff;stop-opacity:0.1"/><stop offset="100%" style="stop-color:#000;stop-opacity:0.3"/></linearGradient>
        </defs>
       
        <rect x="50" y="380" width="20" height="20" fill="#444" /><rect x="230" y="380" width="20" height="20" fill="#444" />
       
        <path d="M50,50 L250,50 L250,350 Q250,380 150,380 Q50,380 50,350 Z" fill="url(#steel)" stroke="#222" stroke-width="2"/>
        <rect x="40" y="40" width="220" height="20" rx="5" fill="#222" /><rect x="125" y="10" width="50" height="40" fill="#111" stroke="#555" />
       
        <mask id="liquidMask"><rect x="70" y="80" width="160" height="200" rx="10" fill="white"/></mask>
        <rect x="70" y="80" width="160" height="200" rx="10" fill="#111" stroke="#555" stroke-width="4"/>
        <rect x="70" y="{liq_y}" width="160" height="{liq_height}" fill="{liq_color}" mask="url(#liquidMask)" opacity="0.8">
            <animate attributeName="opacity" values="0.8;0.9;0.8" dur="2s" repeatCount="indefinite" />
        </rect>
       
        <circle cx="100" cy="{liq_y + 20}" r="3" fill="white" opacity="0.5"><animate attributeName="cy" from="300" to="100" dur="2s" repeatCount="indefinite" /></circle>
       
        <rect x="70" y="80" width="160" height="200" rx="10" fill="url(#glass)" pointer-events="none"/>
       
        <g transform="translate(150, 330)"><rect x="-60" y="-5" width="120" height="10" rx="2" fill="#aaa" stroke="#000"><animateTransform attributeName="transform" type="rotate" from="0 0 0" to="360 0 0" dur="{rot_duration}" repeatCount="indefinite" /></rect></g>
        <rect x="148" y="50" width="4" height="280" fill="#888" /><rect x="200" y="50" width="4" height="150" fill="#a00" /><rect x="90" y="50" width="4" height="150" fill="#00a" />
    </svg>
    """
    b64 = base64.b64encode(svg.encode('utf-8')).decode("utf-8")
    return f'<img src="data:image/svg+xml;base64,{b64}" width="100%"/>'

# ================= 4. INTERFACE PRINCIPALE =================

st.title("BIOREACTOR CONTROL // DT-1")

col_left, col_mid, col_right = st.columns([1, 1.2, 1.5])

# --- GAUCHE : LES 5 ENTRÉES SPÉCIFIQUES ---
with col_left:
    st.markdown("###  PROCESS INPUTS")
   
    with st.container(border=True):
        # 1. Aeration (Fg)
        fg = st.slider("AERATION RATE (Fg) [L/min]", 0.0, 10.0, 1.5, key="input_fg")
       
        # 2. Sugar Feed (Fs)
        fs = st.slider("SUGAR FEED (Fs) [L/h]", 0.0, 2.0, 0.5, key="input_fs")
       
        # 3. Acid Flow (Fa)
        fa = st.number_input("ACID FLOW (Fa) [mL/h]", 0.0, 500.0, 0.0, step=10.0, key="input_fa")
       
        # 4. Base Flow (Fb)
        fb = st.number_input("BASE FLOW (Fb) [mL/h]", 0.0, 500.0, 0.0, step=10.0, key="input_fb")
       
        # 5. Temperature (T)
        temp = st.slider("TEMPERATURE (T) [°C]", 20.0, 60.0, 37.0, key="input_temp")

    st.markdown("<br>", unsafe_allow_html=True)
    start_btn = st.button("▶ DÉMARRER SIMULATION", use_container_width=True)

# --- MILIEU : VISUALISATION ---
with col_mid:
    st.markdown("###  REACTOR VISUAL")
    reactor_container = st.empty()

# --- DROITE : GRAPHIQUES ---
with col_right:
    st.markdown("###  DATA LIVE")
    kpi_container = st.empty()
    chart_container = st.empty()

# ================= 5. LOGIQUE DE SIMULATION =================
if start_btn:
    # Conditions initiales
    vol = 5.0        # Volume initial (L)
    max_vol = 20.0   # Volume max cuve (L)
    biomasse = 0.5   # g/L initial
    rpm_visuel = 300 # Vitesse visuelle de l'hélice (fixe car pas d'entrée RPM demandée)
   
    data_history = []
   
    # Barre de progression pour simuler le temps
    prog_bar = st.progress(0)
   
    # Boucle de simulation (100 itérations)
    for t in range(100):
       
        # --- PHYSIQUE SIMPLIFIÉE ---
       
        # 1. Calcul du débit total entrant (Conversion mL -> L pour acide/base)
        # Fs est déjà en L/h
        total_inflow_L = fs + (fa / 1000.0) + (fb / 1000.0)
       
        # 2. Mise à jour Volume
        if vol < max_vol:
            # On divise par 10 pour simuler un pas de temps court
            vol += (total_inflow_L / 10.0)
        else:
            vol = max_vol # Débordement bloqué
           
        # 3. Calcul Croissance Biomasse
        # Optimum à 37°C
        temp_factor = 1.0 - (abs(temp - 37.0) / 25.0)
        if temp_factor < 0: temp_factor = 0
       
        # L'aération (Fg) aide la croissance
        aeration_factor = 1 + (fg / 5.0)
       
        # Le sucre (Fs) nourrit
        nutrient_factor = 1 + (fs * 2.0)
       
        growth_rate = 0.02 * temp_factor * aeration_factor * nutrient_factor
        biomasse += growth_rate

        # --- MISE À JOUR INTERFACE ---
       
        # 1. SVG
        svg_html = get_reactor_svg((vol/max_vol)*100, rpm_visuel, temp)
        reactor_container.markdown(svg_html, unsafe_allow_html=True)
       
        # 2. KPIs
        kpi_html = f"""
        <div style="display:flex; gap:10px;">
            <div class="kpi-card" style="flex:1">
                <div class="kpi-title">VOLUME</div>
                <div class="kpi-value">{vol:.2f}<span class="kpi-unit">L</span></div>
            </div>
            <div class="kpi-card" style="flex:1">
                <div class="kpi-title">BIOMASSE</div>
                <div class="kpi-value">{biomasse:.2f}<span class="kpi-unit">g/L</span></div>
            </div>
        </div>
        """
        kpi_container.markdown(kpi_html, unsafe_allow_html=True)
       
        # 3. Graphique
        data_history.append({"Temps": t, "Biomasse": biomasse, "Volume": vol})
        chart_container.line_chart(pd.DataFrame(data_history).set_index("Temps"))
       
        # Tempo
        time.sleep(0.05)
        prog_bar.progress(t + 1)

    st.success("BATCH TERMINÉ")

else:
    # État "En attente"
    reactor_container.markdown(get_reactor_svg(25, 0, 20), unsafe_allow_html=True)
    kpi_container.info("Prêt à démarrer.")
   
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import numpy as np
import base64
import plotly.graph_objects as go

# ================= 1. CONFIGURATION & CSS GLOBAL =================

st.set_page_config(page_title="RTE Power Predictor", layout="wide", page_icon="⚡")

# --- CSS "DARK INDUSTRIAL" ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Roboto+Mono:wght@400;700&display=swap');
   
    /* FOND GÉNÉRAL */
    .stApp { background-color: #0e0e0e; color: #ffffff; }
   
    /* TITRES */
    h1, h2, h3 {
        font-family: 'Orbitron', sans-serif;
        color: #00ffcc !important;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
   
    /* TEXTE BLANC POUR LES INPUTS */
    .stSlider p, .stNumberInput p, .stCheckbox p, .stMarkdown p, label {
        color: #ffffff !important;
        font-family: 'Roboto Mono', monospace;
    }
   
    /* BOITES KPI (PREDICTION) */
    .kpi-card {
        background: linear-gradient(145deg, #1a1a1a, #222);
        border: 1px solid #333;
        border-left: 4px solid #00ffcc;
        padding: 20px;
        margin-bottom: 20px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0, 255, 204, 0.1);
        height: 100%; /* S'assure que les deux cartes ont la même hauteur */
    }
    .kpi-title { font-family: 'Roboto Mono', monospace; font-size: 0.9em; color: #aaa; text-transform: uppercase; }
    .kpi-value { font-family: 'Orbitron', sans-serif; font-size: 2.5em; color: #fff; font-weight: bold; text-shadow: 0 0 10px rgba(0,255,204,0.5); }
    .kpi-sub { font-size: 0.8em; color: #00ffcc; }

</style>
""", unsafe_allow_html=True)

# ================= 2. API CONFIG =================
HOST = "digital.iservices.rte-france.com"
DATA_ENDPOINT_PATH = "/open_api/wholesale_market/v3/france_power_exchanges"
DATA_API_URL = f"https://{HOST}{DATA_ENDPOINT_PATH}"
TOKEN_API_URL = f"https://{HOST}/token/oauth/"

# Identifiants RTE
CLIENT_ID = "a13b48af-637a-42cc-b332-65335bc3cdea"
CLIENT_SECRET = "8b1f7961-84b9-426b-b439-bea5a20a7f10"

# ================= 3. AUTHENTIFICATION =================
@st.cache_data(ttl=3600)
def get_access_token():
    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {"grant_type": "client_credentials"}

    try:
        response = requests.post(TOKEN_API_URL, headers=headers, data=payload)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        st.error(f"Erreur d'authentification API: {e}")
        return None

# ================= 4. RÉCUPÉRATION DATA =================
@st.cache_data(ttl=600)
def get_historical_data(token, start_date, end_date):
    if not token: return pd.DataFrame()
   
    headers = {"Authorization": f"Bearer {token}"}
    params = {"start_date": start_date, "end_date": end_date}

    try:
        response = requests.get(DATA_API_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        values = data["france_power_exchanges"][0]["values"]
        df = pd.DataFrame(values)

        df["start_date"] = pd.to_datetime(df["start_date"])
        df["price"] = pd.to_numeric(df["price"], errors="coerce")

        return df.dropna().sort_values("start_date")
    except Exception as e:
        st.error(f"Erreur récupération données: {e}")
        return pd.DataFrame()

# ================= 5. OPTIMISATION =================
def find_optimal_batches(df, num_batches, batch_duration=2):
    if df.empty: return []
    df = df.copy()
    df['hour'] = df['start_date'].dt.hour
    windows = []
   
    for start in range(24 - batch_duration + 1):
        end = start + batch_duration
        avg_price = df[(df['hour'] >= start) & (df['hour'] < end)]['price'].mean()
        windows.append((start, end, avg_price))
   
    windows.sort(key=lambda x: x[2])
   
    selected = []
    for start, end, price in windows:
        if not any(max(start, s) < min(end, e) for s, e, p in selected): # Correction tuple
            # ICI : On stocke (start, end, price) au lieu de juste (start, end)
            selected.append((start, end, price))
            if len(selected) == num_batches:
                break
    return selected

# ================= 6. ANALYSE & AFFICHAGE =================
def plot_streamlit(df, batch_times):
    if df.empty:
        st.warning("Pas de données à afficher.")
        return

    # ----- Modèle simple (Régression Linéaire) -----
    df["time_feature"] = (df["start_date"] - df["start_date"].min()).dt.total_seconds()
    X = df[["time_feature"]]
    y = df["price"]

    model = LinearRegression()
    model.fit(X, y)

    # Prédiction heure suivante
    next_date = df["start_date"].max() + timedelta(hours=1)
    next_tf = (next_date - df["start_date"].min()).total_seconds()
    X_next = pd.DataFrame({"time_feature": [next_tf]})
    predicted_price = model.predict(X_next)[0]
   
    # --- CALCUL DU MEILLEUR BATCH ---
    # batch_times contient maintenant des tuples (start, end, price)
    # On cherche le batch avec le prix le plus bas
    if batch_times:
        best_batch = min(batch_times, key=lambda x: x[2]) # Le moins cher
        best_start, best_end, best_price = best_batch
    else:
        best_start, best_end, best_price = (0, 0, 0)

    # --- AFFICHAGE DES KPI (2 COLONNES) ---
    col_kpi1, col_kpi2 = st.columns(2)
   
    with col_kpi1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">PRÉDICTION IA ({next_date.strftime('%H:%M')} UTC)</div>
            <div class="kpi-value">{predicted_price:.2f} <span style="font-size:0.5em">€/MWh</span></div>
            <div class="kpi-sub">Tendance court terme</div>
        </div>
        """, unsafe_allow_html=True)
       
    with col_kpi2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">MEILLEUR BATCH ({best_start:02d}h - {best_end:02d}h)</div>
            <div class="kpi-value" style="color: #00ffcc;">{best_price:.2f} <span style="font-size:0.5em">€/MWh</span></div>
            <div class="kpi-sub">Créneau le moins cher</div>
        </div>
        """, unsafe_allow_html=True)

    # --- PLOTLY INTERACTIF (CUSTOMISÉ DARK MODE) ---
    fig = go.Figure()

    # Courbe principale -> BLANC
    fig.add_trace(go.Scatter(
        x=df["start_date"],
        y=df["price"],
        mode="lines+markers",
        name="PRIX RÉEL",
        line=dict(color='#ffffff', width=2),
        marker=dict(size=6, color='#ffffff'),
        hovertemplate="<b>%{x|%H:%M}</b><br>%{y:.2f} €/MWh<extra></extra>"
    ))

    # Point de prédiction -> BLANC
    fig.add_trace(go.Scatter(
        x=[next_date],
        y=[predicted_price],
        mode="markers",
        marker=dict(size=15, color="#ffffff", symbol="diamond"),
        name="PRÉDICTION IA",
        hovertemplate="<b>%{x|%H:%M}</b><br>Prédit: %{y:.2f} €/MWh<extra></extra>"
    ))

    # Zones de batches (Rectangles verts)
    day_start = df["start_date"].dt.normalize().iloc[0]
    # On déballe maintenant 3 valeurs: start, end, price (le prix n'est pas utilisé pour le dessin)
    for start_h, end_h, _ in batch_times:
        fig.add_vrect(
            x0=day_start + pd.Timedelta(hours=start_h),
            x1=day_start + pd.Timedelta(hours=end_h),
            fillcolor="#00ffcc",
            opacity=0.15,
            layer="below",
            line_width=0,
            annotation_text="BATCH",
            annotation_position="top left",
            annotation_font_color="#00ffcc"
        )

    # MISE EN FORME DU GRAPHIQUE (DARK THEME)
    fig.update_layout(
        title="PROFIL JOURNALIER & OPTIMISATION",
        title_font=dict(family="Orbitron", size=20, color="#00ffcc"),
        paper_bgcolor='#0e0e0e', # Fond extérieur
        plot_bgcolor='#1a1a1a',  # Fond du graphique
        font=dict(family="Roboto Mono", color="#e0e0e0"),
        xaxis=dict(
            title="HEURE (UTC)",
            showgrid=True, gridcolor='#333',
            tickformat="%Hh",
            dtick=2 * 3600000,
            range=[day_start, day_start + pd.Timedelta(hours=24)]
        ),
        yaxis=dict(
            title="PRIX (€/MWh)",
            showgrid=True, gridcolor='#333',
            zerolinecolor='#555'
        ),
        hovermode="x unified",
        margin=dict(l=40, r=40, t=60, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="white") # Légende Blanche
        )
    )

    st.plotly_chart(fig, width="100%", use_container_width=True)


# ================= MAIN EXECUTION =================

st.title(" ENERGY PRICE FORECASTER")

col_left, col_right = st.columns([1, 3])

# --- SIDEBAR / CONTROLS ---
with col_left:
    st.markdown("###  PARAMÈTRES")
    with st.container(border=True):
        num_batches = st.number_input("NOMBRE DE BATCHES", min_value=1, max_value=8, value=2, step=1)
        st.caption("Durée par batch : 2 heures")
       
    st.markdown("###  INFO API")
    st.info("Source: RTE France\nModel: Linear Regression")

# --- DATA PROCESSING ---
hours = 24
end_dt = datetime.now(timezone.utc)
start_dt = end_dt - timedelta(hours=hours)

# Formatage pour API RTE
start_str = start_dt.strftime("%Y-%m-%dT%H:00:00Z")
end_str = end_dt.strftime("%Y-%m-%dT%H:00:00Z")

token = get_access_token()

if token:
    df = get_historical_data(token, start_str, end_str)
   
    if not df.empty:
        batch_times = find_optimal_batches(df, num_batches)
       
        # --- DISPLAY GRAPHS ---
        with col_right:
            plot_streamlit(df, batch_times)
           
    else:
        st.error("Impossible de récupérer les données historiques.")
else:
    st.error("Échec de l'authentification API.")