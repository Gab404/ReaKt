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
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- IMPORTATION DU MPC ---
from mpc import BioreactorMPC
sys.path.append(os.path.join(os.path.dirname(__file__), 'lstm'))
from model import LSTMModel 

@st.cache_resource
def load_components():
    # ... (chemins et chargement scalers identiques) ...
    BASE_DIR = "lstm/saved_model"
    JSON_PATH = os.path.join(BASE_DIR, "dataset_metadata.json")
    MODEL_PATH = os.path.join(BASE_DIR, "lstm_dynamics.pt")
    SCALER_X_PATH = os.path.join(BASE_DIR, "scaler_X.pkl")
    SCALER_Y_PATH = os.path.join(BASE_DIR, "scaler_y.pkl")

    # 1. Chargement JSON
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, 'r') as f:
            metadata = json.load(f)
        input_cols = metadata['input_columns']
        output_cols = metadata['output_columns']
        # NOUVEAU : Récupération de la config des contrôles
        control_settings = metadata.get('control_columns', []) 
    else:
        st.error(f"Metadata introuvable : {JSON_PATH}")
        st.stop()

    # 2. Chargement Modèle (inchangé)
    checkpoint = torch.load(MODEL_PATH, map_location=torch.device('cpu'))
    hidden_size = checkpoint.get('hidden_size', 128)
    model = LSTMModel(len(input_cols), hidden_size, len(output_cols))
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    # 3. Chargement Scalers (inchangé)
    scaler_X = joblib.load(SCALER_X_PATH)
    scaler_y = joblib.load(SCALER_Y_PATH)
    
    # On retourne aussi control_settings
    return model, scaler_X, scaler_y, input_cols, output_cols, control_settings

# Chargement
model, scaler_X, scaler_y, input_cols, output_cols, control_settings = load_components()

# --- INITIALISATION DU MPC DYNAMIQUE ---
# On passe control_settings au constructeur
mpc = BioreactorMPC(model, scaler_X, scaler_y, input_cols, output_cols, control_settings)

# ==========================================
# 2. MOTEUR 3D (VISUALISATION)
# ==========================================
def get_cylinder_mesh(radius, height, z_offset=0, color='blue', opacity=0.8, resolution=12):
    theta = np.linspace(0, 2*np.pi, resolution)
    z = np.linspace(0, height, 2) + z_offset
    theta_grid, z_grid = np.meshgrid(theta, z)
    x_grid = radius * np.cos(theta_grid)
    y_grid = radius * np.sin(theta_grid)
    lateral = go.Surface(x=x_grid, y=y_grid, z=z_grid, colorscale=[[0, color], [1, color]], 
                          showscale=False, opacity=opacity, hoverinfo='skip')
    top_cap = go.Scatter3d(x=x_grid[1], y=y_grid[1], z=z_grid[1], mode='lines', 
                           line=dict(color=color, width=2), hoverinfo='skip')
    return lateral, top_cap

def render_3d_bioreactor(vol, max_vol, rpm, fg, biomass, step_idx):
    fill_ratio = min(0.95, max(0.1, vol / max_vol))
    tank_height = 10
    liquid_height = tank_height * fill_ratio
    radius = 3
    
    # Couleur liquide (Jaune -> Rouge selon Biomasse)
    biomass_norm = min(1.0, max(0.0, biomass / 18.0))
    r = int(255 - (biomass_norm * 116)) 
    g = int(255 - (biomass_norm * 255)) 
    b = 0
    liquid_color = f'rgb({r}, {g}, {b})'
    
    fig = go.Figure()

    # Cuve (Structure)
    theta = np.linspace(0, 2*np.pi, 16)
    xc = radius * np.cos(theta)
    yc = radius * np.sin(theta)
    for h in [0, tank_height]:
        fig.add_trace(go.Scatter3d(x=xc, y=yc, z=[h]*16, mode='lines', line=dict(color='lightgrey', width=3), hoverinfo='skip'))
    for ang in [0, np.pi/2, np.pi, 3*np.pi/2]:
        fig.add_trace(go.Scatter3d(x=[radius*np.cos(ang)]*2, y=[radius*np.sin(ang)]*2, z=[0, tank_height], 
                                   mode='lines', line=dict(color='lightgrey', width=2), hoverinfo='skip'))

    # Liquide
    liq_surf, liq_top = get_cylinder_mesh(radius=radius*0.95, height=liquid_height, 
                                          color=liquid_color, opacity=0.7)
    fig.add_trace(liq_surf)
    fig.add_trace(liq_top)

    # Agitateur
    angle = (step_idx * rpm * 0.8) % 360
    rad_angle = np.deg2rad(angle)
    fig.add_trace(go.Scatter3d(x=[0,0], y=[0,0], z=[0, tank_height+0.5], mode='lines', 
                               line=dict(color='black', width=4), hoverinfo='skip'))
    blade_len = radius * 0.8
    bx = [blade_len * np.cos(rad_angle), -blade_len * np.cos(rad_angle)]
    by = [blade_len * np.sin(rad_angle), -blade_len * np.sin(rad_angle)]
    fig.add_trace(go.Scatter3d(x=bx, y=by, z=[1, 1], mode='lines', 
                               line=dict(color='black', width=8), hoverinfo='skip'))

    # Bulles
    if fg > 25:
        num_bubbles = 10 
        bx = (np.random.rand(num_bubbles) - 0.5) * 2 * radius * 0.7
        by = (np.random.rand(num_bubbles) - 0.5) * 2 * radius * 0.7
        bz = np.random.rand(num_bubbles) * liquid_height
        fig.add_trace(go.Scatter3d(x=bx, y=by, z=bz, mode='markers', 
                                   marker=dict(size=3, color='white', opacity=0.5), hoverinfo='skip'))

    fig.update_layout(
        scene=dict(
            xaxis=dict(visible=False, range=[-4, 4]),
            yaxis=dict(visible=False, range=[-4, 4]),
            zaxis=dict(visible=False, range=[0, 12]),
            aspectmode='manual', aspectratio=dict(x=1, y=1, z=1.5),
            camera=dict(eye=dict(x=1.5, y=1.5, z=0.5))
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=350,
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# ==========================================
# 3. INTERFACE STREAMLIT
# ==========================================

if os.path.exists("logo.png"):
    st.image("logo.png", width=300)

st.title("Digital Twin & Contrôle MPC")

# Sidebar
st.sidebar.header("Simulation Parameters")
target_penicillin = st.sidebar.slider("Target Penicilline (g/L)", 0.5, 5.0, 3.5)
sim_steps = st.sidebar.slider("Duration Simulation (h)", 50, 200, 100)
replay_speed = st.sidebar.slider("Speed Replay (s)", 0.02, 0.5, 0.1)

col1, col2 = st.sidebar.columns(2)
start_btn = col1.button("Compute", type="primary")

if 'simulation_movie' not in st.session_state:
    st.session_state['simulation_movie'] = None

replay_btn = False
if st.session_state['simulation_movie'] is not None:
    replay_btn = col2.button("Replay")

# Layout Principal
main_col, side_col = st.columns([0.65, 0.35]) 

with main_col:
    m1, m2, m3, m4 = st.columns(4)
    metric_p = m1.empty()
    metric_biomass = m2.empty()
    metric_v = m3.empty()
    metric_step = m4.empty()
    
    progress_container = st.empty()
    chart_placeholder = st.empty()

with side_col:
    st.markdown("### Vue 3D")
    reactor_placeholder = st.empty()

# --- PHASE 1 : CALCUL ---
if start_btn:
    progress_container.info("MPC is thinking... Initializing physics...")
    progress_bar = progress_container.progress(0)
    
    data_source_path = 'indpensim-notebook/Mendeley_data/100_Batches_IndPenSim_V3.csv'
    if not os.path.exists(data_source_path):
        st.error(f"Données introuvables: {data_source_path}")
        st.stop()

    data_source = pd.read_csv(data_source_path)
    data_source = data_source.dropna(subset=output_cols).reset_index(drop=True)
    data_source[output_cols] = data_source[output_cols].ffill()
    
    idx_start = np.random.randint(50, 1000)
    raw_seq_df = data_source[input_cols].iloc[idx_start : idx_start + seq_length]
    
    movie = []
    # Init history
    for i in range(len(raw_seq_df)):
        movie.append(raw_seq_df.iloc[i].to_dict())
        
    current_seq_tensor = torch.tensor(scaler_X.transform(raw_seq_df), dtype=torch.float32).unsqueeze(0)
    
    idx_vol = mpc.idx['Vessel Volume(V:L)']
    idx_sugar = mpc.idx['Sugar feed rate(Fs:L/h)']
    
    start_out = len(input_cols) - len(output_cols)

    for step in range(sim_steps):
        progress_bar.progress((step + 1) / sim_steps)
        
        # 1. Optimisation MPC (Appel au module externe)
        best_controls_scaled = mpc.optimize(current_seq_tensor[0].numpy(), horizon=5, steps=10)
        
        # 2. Mise à jour des Inputs
        last_row_scaled = current_seq_tensor[0, -1, :].numpy().copy()
        for i, c_idx in enumerate(mpc.ctrl_indices):
            last_row_scaled[c_idx] = best_controls_scaled[i]
            
        # 3. Simulation "Physique"
        row_df_scaled = pd.DataFrame([last_row_scaled], columns=input_cols)
        row_unscaled = scaler_X.inverse_transform(row_df_scaled)[0]
        fs_val = row_unscaled[idx_sugar]
        row_unscaled[idx_vol] += (fs_val + 10) * 1.0 - 5.0 
        
        # Re-scaling
        row_df_unscaled = pd.DataFrame([row_unscaled], columns=input_cols)
        new_row_scaled = scaler_X.transform(row_df_unscaled)[0]
        
        # 4. Prédiction du Modèle
        with torch.no_grad():
            temp_seq = current_seq_tensor.clone()
            temp_seq[0, -1, :] = torch.tensor(new_row_scaled)
            pred_out_scaled = model(temp_seq).numpy()[0]
        
        # Injection des prédictions
        new_row_scaled[start_out:] = pred_out_scaled
        
        # 5. Sauvegarde
        final_row_df_scaled = pd.DataFrame([new_row_scaled], columns=input_cols)
        final_row_unscaled = scaler_X.inverse_transform(final_row_df_scaled)[0]
        snapshot = dict(zip(input_cols, final_row_unscaled))
        snapshot['step_idx'] = step
        movie.append(snapshot)
        
        # Update sequence
        new_tensor = torch.tensor(new_row_scaled, dtype=torch.float32).unsqueeze(0).unsqueeze(0)
        current_seq_tensor = torch.cat((current_seq_tensor[:, 1:, :], new_tensor), dim=1)
        
        if snapshot['Penicillin concentration(P:g/L)'] >= target_penicillin:
            break
            
    st.session_state['simulation_movie'] = movie
    st.rerun()

# --- PHASE 2 : REPLAY ---
if st.session_state['simulation_movie'] is not None:
    
    movie = st.session_state['simulation_movie']
    full_df = pd.DataFrame(movie)
    start_replay = 30
    
    progress_container.empty()
    
    for i in range(start_replay, len(full_df)):
        row = full_df.iloc[i]
        
        # Metrics
        curr_p = row['Penicillin concentration(P:g/L)']
        curr_b = row['Offline Biomass concentratio(X_offline:X(g L^{-1}))']
        curr_vol = row['Vessel Volume(V:L)']
        
        metric_p.metric("Pénicilline", f"{curr_p:.2f}", delta=f"{curr_p - target_penicillin:.2f}")
        metric_biomass.metric("Biomasse", f"{curr_b:.2f}")
        metric_v.metric("Volume", f"{curr_vol:.0f} L")
        metric_step.metric("Step", f"{i}")
        
        # Vue 3D
        vis_rpm = row['Agitator RPM(RPM:RPM)']
        vis_fg = row['Aeration rate(Fg:L/h)']
        fig_3d = render_3d_bioreactor(curr_vol, 100000.0, vis_rpm, vis_fg, curr_b, i)
        reactor_placeholder.plotly_chart(fig_3d, use_container_width=True)
        
        # Graphiques
        plot_df = full_df.iloc[max(0, i-50):i+1]
        font_style = dict(color="#00FFCC")

        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.3, 0.3, 0.2, 0.2],
                            subplot_titles=("Biologie (P & X)", "Alimentation (Sucre, Air, Acide, Base)", "Température", "Volume"))
        
        fig.add_trace(go.Scatter(y=plot_df['Penicillin concentration(P:g/L)'], name='Pénicilline', line=dict(color='#2ecc71', width=3)), row=1, col=1)
        fig.add_trace(go.Scatter(y=plot_df['Offline Biomass concentratio(X_offline:X(g L^{-1}))'], name='Biomasse', line=dict(color='#8e44ad', dash='dot')), row=1, col=1)
        fig.add_hline(y=target_penicillin, line_dash="dash", line_color="red", row=1, col=1)
        
        fig.add_trace(go.Scatter(y=plot_df['Sugar feed rate(Fs:L/h)'], name='Sucre (Fs)', line=dict(color='#e67e22')), row=2, col=1)
        fig.add_trace(go.Scatter(y=plot_df['Aeration rate(Fg:L/h)'], name='Air (Fg)', line=dict(color='#3498db')), row=2, col=1)
        fig.add_trace(go.Scatter(y=plot_df['Acid flow rate(Fa:L/h)'], name='Acide (Fa)', line=dict(color='#e74c3c', dash='dot')), row=2, col=1)
        fig.add_trace(go.Scatter(y=plot_df['Base flow rate(Fb:L/h)'], name='Base (Fb)', line=dict(color='#9b59b6', dash='dot')), row=2, col=1)
        
        fig.add_trace(go.Scatter(y=plot_df['Temperature(T:K)'], name='Température (K)', line=dict(color='#d35400')), row=3, col=1)
        fig.add_trace(go.Scatter(y=plot_df['Vessel Volume(V:L)'], name='Volume', line=dict(color='gray')), row=4, col=1)
        
        fig.update_layout(height=800, margin=dict(t=20, b=20, l=10, r=10), showlegend=True,
                          font=font_style, title_font=font_style, legend_font=font_style,
                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        
        chart_placeholder.plotly_chart(fig, use_container_width=True)
        time.sleep(replay_speed)
        
    st.success("Fin de la simulation.")