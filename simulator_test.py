import streamlit as st
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
import joblib
import time
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 1. CONFIGURATION & CACHING
# ==========================================
st.set_page_config(page_title="Simulateur Bioréacteur MPC - Replay", layout="wide")

# --- AJOUT CSS POUR COULEUR #00FFCC ---
st.markdown("""
    <style>
    /* Titres et textes globaux */
    h1, h2, h3, h4, h5, h6, p, li, span {
        color: #00FFCC !important;
    }
    /* Métriques (Chiffres et Labels) */
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
        color: #00FFCC !important;
    }
    /* Markdown et textes divers */
    .stMarkdown, .stText {
        color: #00FFCC !important;
    }
    /* Petites corrections pour la sidebar pour garder la lisibilité */
    .css-1d391kg {
        color: #00FFCC !important;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_components():
    MODEL_PATH = "saved_model/lstm_dynamics.pt"
    # Chargement robuste
    checkpoint = torch.load(MODEL_PATH, map_location=torch.device('cpu'))
    
    input_cols = checkpoint['input_cols']
    output_cols = checkpoint['output_cols']
    seq_length = checkpoint['sequence_length']

    class LSTMModel(nn.Module):
        def __init__(self, input_size, hidden_size, output_size):
            super().__init__()
            self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
            self.dropout = nn.Dropout(0.2)
            self.fc = nn.Linear(hidden_size, output_size)
        def forward(self, x):
            out, _ = self.lstm(x)
            return self.fc(self.dropout(out[:, -1, :]))

    model = LSTMModel(len(input_cols), 128, len(output_cols))
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    scaler_X = joblib.load("saved_model/scaler_X.pkl")
    scaler_y = joblib.load("saved_model/scaler_y.pkl")
    
    return model, scaler_X, scaler_y, input_cols, output_cols, seq_length

model, scaler_X, scaler_y, input_cols, output_cols, seq_length = load_components()

# ==========================================
# 2. LOGIQUE DU MPC
# ==========================================
class BioreactorMPC:
    def __init__(self, model, scaler_X, scaler_y, input_cols, output_cols):
        self.model = model
        self.input_cols = input_cols
        self.idx = {name: i for i, name in enumerate(input_cols)}
        
        self.ctrl_config = [
            {'idx': self.idx['Aeration rate(Fg:L/h)'], 'min': 20.0, 'max': 100.0},
            {'idx': self.idx['Sugar feed rate(Fs:L/h)'], 'min': 0.0, 'max': 150.0},
            {'idx': self.idx['Acid flow rate(Fa:L/h)'], 'min': 0.0, 'max': 15.0},
            {'idx': self.idx['Base flow rate(Fb:L/h)'], 'min': 0.0, 'max': 225.0},
            {'idx': self.idx['Temperature(T:K)'], 'min': 293.0, 'max': 303.0}
        ]
        self.ctrl_indices = [c['idx'] for c in self.ctrl_config]
        
        dummy_min = pd.DataFrame([scaler_X.mean_], columns=input_cols)
        dummy_max = pd.DataFrame([scaler_X.mean_], columns=input_cols)
        for c in self.ctrl_config:
            dummy_min.iloc[0, c['idx']] = c['min']
            dummy_max.iloc[0, c['idx']] = c['max']
        
        self.min_t = torch.tensor(scaler_X.transform(dummy_min)[0, self.ctrl_indices], dtype=torch.float32)
        self.max_t = torch.tensor(scaler_X.transform(dummy_max)[0, self.ctrl_indices], dtype=torch.float32)

    def optimize(self, current_seq_np, horizon=5, steps=10):
        seq = torch.tensor(current_seq_np, dtype=torch.float32).unsqueeze(0)
        u_future = torch.zeros(horizon, len(self.ctrl_indices), requires_grad=True)
        optimizer = optim.Adam([u_future], lr=0.1)
        start_out = len(self.input_cols) - 4 
        
        for _ in range(steps):
            optimizer.zero_grad()
            curr = seq.clone()
            rewards = []
            for t in range(horizon):
                pred = self.model(curr)
                rewards.append(pred[0, 0])
                last_in = curr[0, -1, :].clone()
                for i, c_idx in enumerate(self.ctrl_indices):
                    last_in[c_idx] = u_future[t, i]
                last_in[start_out:] = pred[0]
                curr = torch.cat((curr[:, 1:, :], last_in.view(1, 1, -1)), dim=1)
            
            loss = -torch.mean(torch.stack(rewards)) + 0.1 * torch.sum((u_future[1:] - u_future[:-1])**2)
            loss.backward()
            optimizer.step()
            with torch.no_grad():
                for i in range(len(self.ctrl_indices)):
                    u_future[:, i].clamp_(self.min_t[i], self.max_t[i])
        return u_future.detach().numpy()[0, :]

mpc = BioreactorMPC(model, scaler_X, scaler_y, input_cols, output_cols)

# ==========================================
# 3. MOTEUR 3D (OPTIMISÉ)
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

    # Cuve
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
# 4. INTERFACE
# ==========================================

# --- AJOUT DU LOGO ICI ---
if os.path.exists("logo.png"):
    st.image("logo.png", width=300)
else:
    # Petit message si le fichier manque, pour ne pas casser le layout
    st.warning("⚠️ Fichier 'logo.png' introuvable.")

st.title("Digital Twin & Contrôle MPC")

# Sidebar
st.sidebar.header("Simulation Parameters")
target_penicillin = st.sidebar.slider("Target Penicilline (g/L)", 0.5, 5.0, 3.5)
sim_steps = st.sidebar.slider("Duration Simulation (h)", 50, 200, 100)
replay_speed = st.sidebar.slider("Speed Replay (s)", 0.02, 0.5, 0.1)

col1, col2 = st.sidebar.columns(2)
start_btn = col1.button("Compute", type="primary")

# Gestion Session
if 'simulation_movie' not in st.session_state:
    st.session_state['simulation_movie'] = None

replay_btn = False
if st.session_state['simulation_movie'] is not None:
    replay_btn = col2.button("Replay")

# Layout
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
    progress_container.info("MPC is thinking...")
    progress_bar = progress_container.progress(0)
    
    data_source = pd.read_csv('indpensim-notebook/Mendeley_data/100_Batches_IndPenSim_V3.csv')
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
    
    for step in range(sim_steps):
        progress_bar.progress((step + 1) / sim_steps)
        
        # MPC
        best_controls_scaled = mpc.optimize(current_seq_tensor[0].numpy(), horizon=5, steps=10)
        
        # Update Inputs
        last_row_scaled = current_seq_tensor[0, -1, :].numpy().copy()
        for i, c_idx in enumerate(mpc.ctrl_indices):
            last_row_scaled[c_idx] = best_controls_scaled[i]
            
        # Physics
        row_df_scaled = pd.DataFrame([last_row_scaled], columns=input_cols)
        row_unscaled = scaler_X.inverse_transform(row_df_scaled)[0]
        fs_val = row_unscaled[idx_sugar]
        row_unscaled[idx_vol] += (fs_val + 10) * 1.0 - 5.0 
        
        row_df_unscaled = pd.DataFrame([row_unscaled], columns=input_cols)
        new_row_scaled = scaler_X.transform(row_df_unscaled)[0]
        
        # LSTM Prediction
        with torch.no_grad():
            temp_seq = current_seq_tensor.clone()
            temp_seq[0, -1, :] = torch.tensor(new_row_scaled)
            pred_out_scaled = model(temp_seq).numpy()[0]
        start_out = len(input_cols) - 4
        new_row_scaled[start_out:] = pred_out_scaled
        
        # Save Frame
        final_row_df_scaled = pd.DataFrame([new_row_scaled], columns=input_cols)
        final_row_unscaled = scaler_X.inverse_transform(final_row_df_scaled)[0]
        snapshot = dict(zip(input_cols, final_row_unscaled))
        snapshot['step_idx'] = step
        movie.append(snapshot)
        
        # Next tensor
        new_tensor = torch.tensor(new_row_scaled, dtype=torch.float32).unsqueeze(0).unsqueeze(0)
        current_seq_tensor = torch.cat((current_seq_tensor[:, 1:, :], new_tensor), dim=1)
        
        if snapshot['Penicillin concentration(P:g/L)'] >= target_penicillin:
            break
            
    st.session_state['simulation_movie'] = movie
    st.rerun()

# --- PHASE 2 : REPLAY ---
if replay_btn or (st.session_state['simulation_movie'] is not None and not start_btn):
    pass

if st.session_state['simulation_movie'] is not None:
    
    movie = st.session_state['simulation_movie']
    full_df = pd.DataFrame(movie)
    start_replay = 30
    
    progress_container.empty()
    
    for i in range(start_replay, len(full_df)):
        row = full_df.iloc[i]
        
        # 1. Update Metrics
        curr_p = row['Penicillin concentration(P:g/L)']
        curr_b = row['Offline Biomass concentratio(X_offline:X(g L^{-1}))']
        curr_vol = row['Vessel Volume(V:L)']
        
        metric_p.metric("Pénicilline", f"{curr_p:.2f}", delta=f"{curr_p - target_penicillin:.2f}")
        metric_biomass.metric("Biomasse", f"{curr_b:.2f}")
        metric_v.metric("Volume", f"{curr_vol:.0f} L")
        metric_step.metric("Step", f"{i}")
        
        # 2. Update 3D
        vis_rpm = row['Agitator RPM(RPM:RPM)']
        vis_fg = row['Aeration rate(Fg:L/h)']
        
        fig_3d = render_3d_bioreactor(curr_vol, 100000.0, vis_rpm, vis_fg, curr_b, i)
        reactor_placeholder.plotly_chart(fig_3d, use_container_width=True)
        
        # 3. Update Graphs
        plot_df = full_df.iloc[max(0, i-50):i+1]
        
        # PARAMETRE DE COULEUR DU TEXTE POUR PLOTLY (#00FFCC)
        font_style = dict(color="#00FFCC")

        fig = make_subplots(
            rows=4, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.08,
            row_heights=[0.3, 0.3, 0.2, 0.2],
            subplot_titles=("Biologie (P & X)", "Alimentation (Sucre, Air, Acide, Base)", "Température", "Volume")
        )
        
        # GRAPH 1 : Biologie
        fig.add_trace(go.Scatter(y=plot_df['Penicillin concentration(P:g/L)'], name='Pénicilline', line=dict(color='#2ecc71', width=3)), row=1, col=1)
        fig.add_trace(go.Scatter(y=plot_df['Offline Biomass concentratio(X_offline:X(g L^{-1}))'], name='Biomasse', line=dict(color='#8e44ad', dash='dot')), row=1, col=1)
        fig.add_hline(y=target_penicillin, line_dash="dash", line_color="red", row=1, col=1)
        
        # GRAPH 2 : Flux
        fig.add_trace(go.Scatter(y=plot_df['Sugar feed rate(Fs:L/h)'], name='Sucre (Fs)', line=dict(color='#e67e22')), row=2, col=1)
        fig.add_trace(go.Scatter(y=plot_df['Aeration rate(Fg:L/h)'], name='Air (Fg)', line=dict(color='#3498db')), row=2, col=1)
        fig.add_trace(go.Scatter(y=plot_df['Acid flow rate(Fa:L/h)'], name='Acide (Fa)', line=dict(color='#e74c3c', dash='dot')), row=2, col=1)
        fig.add_trace(go.Scatter(y=plot_df['Base flow rate(Fb:L/h)'], name='Base (Fb)', line=dict(color='#9b59b6', dash='dot')), row=2, col=1)
        
        # GRAPH 3 : Température
        fig.add_trace(go.Scatter(y=plot_df['Temperature(T:K)'], name='Température (K)', line=dict(color='#d35400')), row=3, col=1)
        
        # GRAPH 4 : Volume
        fig.add_trace(go.Scatter(y=plot_df['Vessel Volume(V:L)'], name='Volume', line=dict(color='gray')), row=4, col=1)
        
        # Application de la couleur #00FFCC aux textes du graph
        fig.update_layout(
            height=800, 
            margin=dict(t=20, b=20, l=10, r=10), 
            showlegend=True,
            font=font_style, # Changement de couleur globale du texte Plotly
            title_font=font_style,
            legend_font=font_style
        )
        
        chart_placeholder.plotly_chart(fig, use_container_width=True)
        
        time.sleep(replay_speed)
        
    st.success("Fin de la simulation.")