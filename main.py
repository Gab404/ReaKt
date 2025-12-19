import streamlit as st
import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import joblib
import time
import os
import json
import sys
import argparse
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import gc

# Ajout du path courant pour trouver preprocess.py
sys.path.append(os.getcwd())

# CONSTANTE TEMPORELLE
STEP_DURATION = 12 / 60  # 12 minutes en heures = 0.2h

def clean_memory():
    gc.collect()                # Nettoie la RAM (CPU)
    if torch.cuda.is_available():
        torch.cuda.empty_cache() # Vide le cache VRAM (GPU)

# ==========================================
# 0. GESTION DES ARGUMENTS (FLAGS)
# ==========================================
def get_arguments():
    parser = argparse.ArgumentParser(description="Digital Twin Bioreactor")
    parser.add_argument('--path-to-data', type=str, default='100_Batches_IndPenSim_V3.csv', help='Chemin CSV (Fallback)')
    parser.add_argument('--path-to-model', type=str, default='saved_model', help='Dossier contenant le modèle et les datasets .pt')
    args, _ = parser.parse_known_args()
    return args

args = get_arguments()

# ==========================================
# 1. CONFIGURATION & IMPORTS
# ==========================================
st.set_page_config(page_title="ReaKt", layout="wide")

st.markdown("""
    <style>
    h1, h2, h3, h4, h5, h6, p, li, span { color: #00FFCC !important; }
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #00FFCC !important; }
    .stMarkdown, .stText { color: #00FFCC !important; }
    .css-1d391kg { color: #00FFCC !important; }
    
    /* Style léger pour encadrer le benchmark sans HTML complexe */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        background-color: rgba(0, 255, 204, 0.05);
        border-radius: 10px;
        padding: 10px;
    }
    </style>
""", unsafe_allow_html=True)

sys.path.append(os.path.join(os.path.dirname(__file__), 'lstm'))

try:
    from mpc import BioreactorMPC
    from model import LSTMModel 
    from preprocess import BioreactorDataset 
except ImportError:
    st.error("Erreur: Impossible d'importer 'mpc', 'model' ou 'preprocess'. Vérifiez que tous les fichiers sont présents.")
    st.stop()

# ==========================================
# 2. GESTION DU DEVICE (CPU/GPU)
# ==========================================
st.sidebar.header("Hardware Settings")

if torch.cuda.is_available():
    available_devices = ["GPU (CUDA)", "CPU"]
    device_index = 0
else:
    available_devices = ["CPU"]
    device_index = 0

selected_device_label = st.sidebar.radio(
    "Compute Device", 
    available_devices, 
    index=device_index,
    help="Select GPU to accelerate the compute"
)

if "GPU" in selected_device_label:
    device = torch.device("cuda")
    st.sidebar.success(f"Running on **GPU** ({torch.cuda.get_device_name(0)})")
else:
    device = torch.device("cpu")
    st.sidebar.info("Running on **CPU**")

# ==========================================
# 3. CHARGEMENT DES COMPOSANTS
# ==========================================
@st.cache_resource
def load_components(model_dir, _device):
    BASE_DIR = model_dir
    if not os.path.exists(BASE_DIR):
        if os.path.exists("lstm/saved_model"): BASE_DIR = "lstm/saved_model"
        elif os.path.exists("saved_model"): BASE_DIR = "saved_model"
            
    JSON_PATH = os.path.join(BASE_DIR, "dataset_metadata.json")
    MODEL_PATH = os.path.join(BASE_DIR, "lstm_dynamics.pt")
    SCALER_X_PATH = os.path.join(BASE_DIR, "scaler_X.pkl")
    SCALER_Y_PATH = os.path.join(BASE_DIR, "scaler_y.pkl")

    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, 'r') as f:
            metadata = json.load(f)
        input_cols = metadata['input_columns']
        output_cols = metadata['output_columns']
        control_settings = metadata.get('control_columns', [])
        # Récupération des statistiques globales pour le benchmark
        statistics = metadata.get('statistics', {})
    else:
        st.stop()

    if not os.path.exists(MODEL_PATH): st.stop()

    # Chargement avec mappage sur le device choisi
    checkpoint = torch.load(MODEL_PATH, map_location=_device, weights_only=True)
    seq_len = checkpoint.get('sequence_length', 10)
    hidden_size = checkpoint.get('hidden_size', 128)
    
    model = LSTMModel(len(input_cols), hidden_size, len(output_cols))
    model.load_state_dict(checkpoint['model_state_dict'])
    
    # On place le modèle sur le device DANS la fonction
    model.to(_device)
    model.eval()

    if not os.path.exists(SCALER_X_PATH) or not os.path.exists(SCALER_Y_PATH): st.stop()
         
    scaler_X = joblib.load(SCALER_X_PATH)
    scaler_y = joblib.load(SCALER_Y_PATH)
    
    return model, scaler_X, scaler_y, input_cols, output_cols, control_settings, seq_len, statistics

# Chargement
model, scaler_X, scaler_y, input_cols, output_cols, control_settings, seq_len, stats = load_components(args.path_to_model, device)

# Sécurité Device
model.to(device)

mpc = BioreactorMPC(model, scaler_X, scaler_y, input_cols, output_cols, control_settings)

# ==========================================
# 4. MOTEUR 3D
# ==========================================
def get_cylinder_mesh(radius, height, z_offset=0, color='blue', opacity=0.8, resolution=12):
    theta = np.linspace(0, 2*np.pi, resolution)
    z = np.linspace(0, height, 2) + z_offset
    theta_grid, z_grid = np.meshgrid(theta, z)
    x_grid = radius * np.cos(theta_grid)
    y_grid = radius * np.sin(theta_grid)
    lateral = go.Surface(x=x_grid, y=y_grid, z=z_grid, colorscale=[[0, color], [1, color]], showscale=False, opacity=opacity, hoverinfo='skip')
    top_cap = go.Scatter3d(x=x_grid[1], y=y_grid[1], z=z_grid[1], mode='lines', line=dict(color=color, width=2), hoverinfo='skip')
    return lateral, top_cap

def render_3d_bioreactor(vol, max_vol, rpm, fg, biomass, step_idx):
    fill_ratio = min(0.95, max(0.1, vol / max_vol))
    tank_height = 10
    liquid_height = tank_height * fill_ratio
    radius = 3
    biomass_norm = min(1.0, max(0.0, biomass / 18.0))
    r, g, b = int(255 - (biomass_norm * 116)), int(255 - (biomass_norm * 255)), 0
    liquid_color = f'rgb({r}, {g}, {b})'
    
    fig = go.Figure()
    theta = np.linspace(0, 2*np.pi, 16)
    xc, yc = radius * np.cos(theta), radius * np.sin(theta)
    for h in [0, tank_height]:
        fig.add_trace(go.Scatter3d(x=xc, y=yc, z=[h]*16, mode='lines', line=dict(color='lightgrey', width=3), hoverinfo='skip'))
    
    liq_surf, liq_top = get_cylinder_mesh(radius=radius*0.95, height=liquid_height, color=liquid_color, opacity=0.7)
    fig.add_trace(liq_surf)
    fig.add_trace(liq_top)

    angle = (step_idx * rpm * 0.8) % 360
    rad_angle = np.deg2rad(angle)
    fig.add_trace(go.Scatter3d(x=[0,0], y=[0,0], z=[0, tank_height+0.5], mode='lines', line=dict(color='black', width=4), hoverinfo='skip'))
    
    blade_len = radius * 0.8
    bx = [blade_len * np.cos(rad_angle), -blade_len * np.cos(rad_angle)]
    by = [blade_len * np.sin(rad_angle), -blade_len * np.sin(rad_angle)]
    fig.add_trace(go.Scatter3d(x=bx, y=by, z=[1, 1], mode='lines', line=dict(color='black', width=8), hoverinfo='skip'))

    fig.update_layout(scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False, range=[0, 12]), aspectmode='manual', aspectratio=dict(x=1, y=1, z=1.5)), margin=dict(l=0,r=0,t=0,b=0), height=350, showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    return fig

# ==========================================
# 5. INTERFACE STREAMLIT
# ==========================================
if os.path.exists("./assets/logo.png"): st.image("./assets/logo.png", width=300)

st.sidebar.header("Simulation Parameters")
st.sidebar.caption(f"📂 Model: `{args.path_to_model}`")

# Moyennes historiques
mean_p_hist = stats.get('Penicillin concentration(P:g/L)', {}).get('mean', 2.0)
target_penicillin = st.sidebar.slider("Target Penicilline (g/L)", 0.5, 5.0, float(mean_p_hist) * 1.5) 

# Modification du slider pour clarifier que c'est le nombre de pas de temps
sim_steps = st.sidebar.slider("Simulation Steps (12min/step)", 50, 500, 100)
# Calcul de la durée estimée pour info
estimated_hours = sim_steps * STEP_DURATION
st.sidebar.caption(f"⏱️ Duration: {estimated_hours:.1f} hours")

replay_speed = st.sidebar.slider("Speed Replay (s)", 0.02, 0.5, 0.1)

col1, col2 = st.sidebar.columns(2)
start_btn = col1.button("Compute", type="primary")

if 'simulation_movie' not in st.session_state: st.session_state['simulation_movie'] = None
if 'ground_truth' not in st.session_state: st.session_state['ground_truth'] = None

if st.session_state['simulation_movie'] is not None:
    replay_btn = col2.button("Replay")

# --- MISE EN PAGE PRINCIPALE ---
main_col, side_col = st.columns([0.65, 0.35]) 

with main_col:
    m1, m2, m3, m4 = st.columns(4)
    metric_p, metric_biomass, metric_v, metric_step = m1.empty(), m2.empty(), m3.empty(), m4.empty()
    progress_container, chart_placeholder = st.empty(), st.empty()

with side_col:
    reactor_placeholder = st.empty()
    # PLACEHOLDER POUR LE BENCHMARK (Natif Streamlit)
    st.markdown("---")
    performance_placeholder = st.empty()

# --- PHASE 1 : CALCUL ---
if start_btn:
    # Nettoyage mémoire préventif
    if 'simulation_movie' in st.session_state:
        del st.session_state['simulation_movie']
        st.session_state['simulation_movie'] = None
    clean_memory()

    progress_container.info(f"MPC is thinking on {device}... Loading Test Set...")
    progress_bar = progress_container.progress(0)
    
    # 1. Chargement du Test Set (.pt)
    test_set_path = os.path.join(args.path_to_model, "test_set.pt")
    
    if not os.path.exists(test_set_path):
        st.error(f"Fichier introuvable : {test_set_path}. Veuillez lancer train.py d'abord.")
        st.stop()
        
    try:
        test_dataset = torch.load(test_set_path, weights_only=False)
    except Exception as e:
        st.error(f"Erreur chargement test_set.pt : {e}")
        st.stop()

    idx_start = np.random.randint(0, len(test_dataset))
    X_init_tensor, _ = test_dataset[idx_start]
    current_seq_tensor = X_init_tensor.unsqueeze(0).float().to(device)

    # Reconstruction de l'historique
    X_init_np = X_init_tensor.cpu().numpy()
    X_init_physical = scaler_X.inverse_transform(X_init_np)
    
    raw_seq_df = pd.DataFrame(X_init_physical, columns=input_cols)
    movie = []
    
    # Initialisation avec l'historique
    for i in range(len(raw_seq_df)): 
        snap = raw_seq_df.iloc[i].to_dict()
        # Ajout du temps négatif pour l'historique (ex: -2h, -1.8h...)
        snap['Time (h)'] = (i - len(raw_seq_df)) * STEP_DURATION
        movie.append(snap)

    st.session_state['ground_truth'] = pd.DataFrame() 

    # Indices
    idx_vol, idx_sugar = mpc.idx['Vessel Volume(V:L)'], mpc.idx['Sugar feed rate(Fs:L/h)']
    start_out = len(input_cols) - len(output_cols)

    # 5. Boucle de Simulation
    for step in range(sim_steps):
        progress_bar.progress((step + 1) / sim_steps)
        
        current_seq_np = current_seq_tensor[0].cpu().numpy()
        best_controls_scaled = mpc.optimize(current_seq_np, horizon=5, steps=10)
        
        last_row_scaled = current_seq_np[-1, :].copy()
        for i, c_idx in enumerate(mpc.ctrl_indices): last_row_scaled[c_idx] = best_controls_scaled[i]
            
        row_df_scaled = pd.DataFrame([last_row_scaled], columns=input_cols)
        row_unscaled = scaler_X.inverse_transform(row_df_scaled)[0]
        row_unscaled[idx_vol] += (row_unscaled[idx_sugar] + 10) * 1.0 - 5.0 
        
        new_row_scaled = scaler_X.transform(pd.DataFrame([row_unscaled], columns=input_cols))[0]
        
        with torch.no_grad():
            temp_seq = current_seq_tensor.clone()
            new_row_tensor = torch.tensor(new_row_scaled, dtype=torch.float32).to(device)
            temp_seq[0, -1, :] = new_row_tensor
            pred_out_scaled = model(temp_seq).cpu().numpy()[0]
        
        new_row_scaled[start_out:] = pred_out_scaled
        
        final_row_unscaled = scaler_X.inverse_transform(pd.DataFrame([new_row_scaled], columns=input_cols))[0]
        snapshot = dict(zip(input_cols, final_row_unscaled))
        
        # --- AJOUT TEMPS REEL ---
        snapshot['step_idx'] = step
        snapshot['Time (h)'] = step * STEP_DURATION
        # ------------------------
        
        movie.append(snapshot)
        
        new_tensor = torch.tensor(new_row_scaled, dtype=torch.float32).unsqueeze(0).unsqueeze(0).to(device)
        current_seq_tensor = torch.cat((current_seq_tensor[:, 1:, :], new_tensor), dim=1)
        
        if snapshot['Penicillin concentration(P:g/L)'] >= target_penicillin: break
            
    st.session_state['simulation_movie'] = movie
    clean_memory()
    st.rerun()

# --- PHASE 2 : REPLAY ---
if st.session_state['simulation_movie'] is not None:
    
    movie = st.session_state['simulation_movie']
    full_df = pd.DataFrame(movie)
    gt_df = st.session_state.get('ground_truth', pd.DataFrame())

    # ==========================================
    # CALCUL & AFFICHAGE DU BENCHMARK (SANS HTML)
    # ==========================================
    hist_avg_p = stats.get('Penicillin concentration(P:g/L)', {}).get('mean', 0)
    final_p = full_df.iloc[-1]['Penicillin concentration(P:g/L)']
    
    # Gain Productivité
    gain_pct = ((final_p - hist_avg_p) / hist_avg_p) * 100 if hist_avg_p != 0 else 0
    
    with performance_placeholder.container():
        st.markdown("### ROI Report")
        
        # Section 1 : Productivité
        c1, c2 = st.columns(2)
        c1.metric("Final Product", f"{final_p:.2f} g/L")
        # Le gain est vert si positif (classique)
        c2.metric("Yield Gain", f"{gain_pct:+.1f}%", delta=f"{gain_pct:+.1f}%")
        
        st.markdown("#### Resource Efficiency")
        st.caption("Comparison vs Historical Average")
        
        # Section 2 : Consommation Ressources (Grille 2x2)
        resources_to_track = {
            'Sugar Feed': 'Sugar feed rate(Fs:L/h)',
            'Acid Flow': 'Acid flow rate(Fa:L/h)',
            'Base Flow': 'Base flow rate(Fb:L/h)',
            'Aeration': 'Aeration rate(Fg:L/h)'
        }
        
        res_cols = st.columns(2)
        idx = 0
        
        for label, col_name in resources_to_track.items():
            if col_name in full_df.columns:
                mpc_mean = full_df[col_name].mean()
                hist_mean = stats.get(col_name, {}).get('mean', 1e-6)
                
                # Calcul de la différence en %
                usage_diff = ((mpc_mean - hist_mean) / hist_mean) * 100
                
                # Logique couleur inversée
                with res_cols[idx % 2]:
                    st.metric(
                        label=label,
                        value=f"{mpc_mean:.2f}",
                        delta=f"{usage_diff:+.1f}%",
                        delta_color="inverse" 
                    )
                idx += 1
    # ==========================================

    start_replay = max(seq_len, 30)
    progress_container.empty()
    
    for i in range(start_replay, len(full_df)):
        row = full_df.iloc[i]
        
        # Conversion index -> Temps réel
        current_time_h = row['Time (h)']
        
        metric_p.metric("Penicilin", f"{row['Penicillin concentration(P:g/L)']:.2f}", delta=f"{row['Penicillin concentration(P:g/L)'] - target_penicillin:.2f}")
        metric_biomass.metric("Biomass", f"{row['Offline Biomass concentratio(X_offline:X(g L^{-1}))']:.2f}")
        metric_v.metric("Volume", f"{row['Vessel Volume(V:L)']:.0f} L")
        # Affichage temps en Heures
        metric_step.metric("Time Elapsed", f"{current_time_h:.1f} h")
        
        fig_3d = render_3d_bioreactor(row['Vessel Volume(V:L)'], 100000.0, row['Agitator RPM(RPM:RPM)'], row['Aeration rate(Fg:L/h)'], row['Offline Biomass concentratio(X_offline:X(g L^{-1}))'], i)
        reactor_placeholder.plotly_chart(fig_3d, use_container_width=True)
        
        plot_df = full_df.iloc[max(0, i-50):i+1]
        
        plot_gt = pd.DataFrame()
        if not gt_df.empty and i < len(gt_df):
            plot_gt = gt_df.iloc[max(0, i-50):i+1]

        font_style = dict(color="#00FFCC")
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.3, 0.3, 0.2, 0.2],
                            subplot_titles=("Biomass & Penicilin", "Alimentation", "Temperature", "Volume"))
        
        # --- UTILISATION DU TEMPS EN X ---
        x_axis = plot_df['Time (h)']
        
        # --- Plot 1: Biologie ---
        fig.add_trace(go.Scatter(x=x_axis, y=plot_df['Penicillin concentration(P:g/L)'], name='Pred P', line=dict(color='#2ecc71', width=3)), row=1, col=1)
        fig.add_trace(go.Scatter(x=x_axis, y=plot_df['Offline Biomass concentratio(X_offline:X(g L^{-1}))'], name='Pred Biomass', line=dict(color='#8e44ad', width=2)), row=1, col=1)

        fig.add_hline(y=target_penicillin, line_dash="dash", line_color="red", row=1, col=1)
        
        # --- Plot 2: Alimentation ---
        fig.add_trace(go.Scatter(x=x_axis, y=plot_df['Sugar feed rate(Fs:L/h)'], name='Sugar (MPC)', line=dict(color='#e67e22')), row=2, col=1)

        fig.add_trace(go.Scatter(x=x_axis, y=plot_df['Aeration rate(Fg:L/h)'], name='O2', line=dict(color='#3498db')), row=2, col=1)
        fig.add_trace(go.Scatter(x=x_axis, y=plot_df['Acid flow rate(Fa:L/h)'], name='Acide', line=dict(color='#e74c3c', dash='dot')), row=2, col=1)
        
        fig.add_trace(go.Scatter(x=x_axis, y=plot_df['Base flow rate(Fb:L/h)'], name='Base (MPC)', line=dict(color='#9b59b6', dash='dot')), row=2, col=1)

        # --- Autres Plots ---
        fig.add_trace(go.Scatter(x=x_axis, y=plot_df['Temperature(T:K)'], name='Temp', line=dict(color='#d35400')), row=3, col=1)
        fig.add_trace(go.Scatter(x=x_axis, y=plot_df['Vessel Volume(V:L)'], name='Vol', line=dict(color='gray')), row=4, col=1)
        
        # Mise à jour Layout pour ajouter le label X
        fig.update_layout(height=800, margin=dict(t=20, b=20, l=10, r=10), showlegend=True, font=font_style, title_font=font_style, legend_font=font_style, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        fig.update_xaxes(title_text="Time (hours)", row=4, col=1, color="#00FFCC")
        
        chart_placeholder.plotly_chart(fig, use_container_width=True)
        time.sleep(replay_speed)
        
    st.success("End of the simulation.")