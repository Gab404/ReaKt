import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
import joblib

# ==========================================
# 1. DÉFINITION DE L'ARCHITECTURE (Identique à l'entraînement)
# ==========================================
class LSTMModel(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.dropout = nn.Dropout(0.2)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :]
        out = self.dropout(out)
        return self.fc(out)

# ==========================================
# 2. CHARGEMENT DU MODÈLE ET DES SCALERS
# ==========================================
print("Chargement des fichiers...")

# Chemins (à adapter si nécessaire)
MODEL_PATH = "saved_model/lstm_dynamics.pt"
SCALER_X_PATH = "saved_model/scaler_X.pkl"
SCALER_Y_PATH = "saved_model/scaler_y.pkl"

# Charger les infos sauvegardées
checkpoint = torch.load(MODEL_PATH)
input_cols = checkpoint['input_cols']
output_cols = checkpoint['output_cols']
seq_length = checkpoint['sequence_length']

# Recharger les scalers
scaler_X = joblib.load(SCALER_X_PATH)
scaler_y = joblib.load(SCALER_Y_PATH)

# Instancier et charger le modèle
model = LSTMModel(len(input_cols), 128, len(output_cols))
model.load_state_dict(checkpoint['model_state_dict'])
model.eval() # Mode évaluation (figé)

print("✅ Modèle chargé avec succès.")

# ==========================================
# 3. CLASSE MPC AVEC CONTRAINTES PHYSIQUES
# ==========================================
class BioreactorMPC:
    def __init__(self, model, scaler_X, scaler_y, input_cols, output_cols):
        self.model = model
        self.scaler_X = scaler_X
        self.scaler_y = scaler_y
        self.input_cols = input_cols
        self.output_cols = output_cols
        
        # Mapping des colonnes pour accès rapide par nom
        self.idx = {name: i for i, name in enumerate(input_cols)}
        
        # Indices des variables à contrôler
        self.ctrl_vars = {
            'Aeration rate(Fg:L/h)':       {'idx': self.idx['Aeration rate(Fg:L/h)'],       'min': 20.0,  'max': 100.0},
            'Sugar feed rate(Fs:L/h)':     {'idx': self.idx['Sugar feed rate(Fs:L/h)'],     'min': 0.0,   'max': 150.0},
            'Acid flow rate(Fa:L/h)':      {'idx': self.idx['Acid flow rate(Fa:L/h)'],      'min': 0.0,   'max': 15.0}, # Max approx d'après tes stats
            'Base flow rate(Fb:L/h)':      {'idx': self.idx['Base flow rate(Fb:L/h)'],      'min': 0.0,   'max': 225.0},
            'Temperature(T:K)':            {'idx': self.idx['Temperature(T:K)'],            'min': 293.0, 'max': 303.0} # Ex: 20°C - 30°C
        }
        
        self.control_indices = [v['idx'] for v in self.ctrl_vars.values()]
        
        # Limites scalées (pour le clamping dans l'optimiseur)
        # On crée des vecteurs dummy pour transformer les min/max bruts en valeurs scalées
        self.min_vals_scaled = {}
        self.max_vals_scaled = {}
        
        dummy_min = np.zeros((1, len(input_cols)))
        dummy_max = np.zeros((1, len(input_cols)))
        
        # On remplit avec les valeurs moyennes du scaler pour ne pas fausser, sauf pour nos controls
        dummy_min[:] = scaler_X.mean_
        dummy_max[:] = scaler_X.mean_
        
        for name, config in self.ctrl_vars.items():
            dummy_min[0, config['idx']] = config['min']
            dummy_max[0, config['idx']] = config['max']
            
        scaled_mins = scaler_X.transform(dummy_min)[0]
        scaled_maxs = scaler_X.transform(dummy_max)[0]
        
        self.control_mins_tensor = torch.tensor([scaled_mins[i] for i in self.control_indices], dtype=torch.float32)
        self.control_maxs_tensor = torch.tensor([scaled_maxs[i] for i in self.control_indices], dtype=torch.float32)
        
        # Index de la Pénicilline (Cible) et du Volume (Contrainte physique)
        self.target_idx = 0 # 'Penicillin concentration(P:g/L)' est le 1er output
        self.vol_idx = self.idx['Vessel Volume(V:L)']
        
        # Index des flux influençant le volume (Fs, Fa, Fb, Fw)
        # Note: Fw (Water) n'est pas optimisé ici mais doit être compté s'il change le volume.
        self.flow_indices = [
            self.idx['Sugar feed rate(Fs:L/h)'],
            self.idx['Acid flow rate(Fa:L/h)'],
            self.idx['Base flow rate(Fb:L/h)'],
            self.idx['Water for injection/dilution(Fw:L/h)']
        ]

    def optimize(self, current_sequence_scaled, horizon=10, steps=50, lr=0.1):
        """
        current_sequence_scaled: (seq_length, n_features) - Numpy array scalé
        """
        # Tensorisation
        seq = torch.tensor(current_sequence_scaled, dtype=torch.float32).unsqueeze(0) # (1, 60, feat)
        
        # Initialisation des contrôles futurs (start with 0 -> moyenne)
        u_future = torch.zeros(horizon, len(self.control_indices), requires_grad=True)
        optimizer = optim.Adam([u_future], lr=lr)
        
        best_u = None
        best_reward = -float('inf')
        
        # Index où commencent les sorties dans le vecteur d'entrée input_cols
        # input_cols = process + outputs. Donc les outputs sont à la fin.
        start_output_idx = len(self.input_cols) - len(self.output_cols)

        for step in range(steps):
            optimizer.zero_grad()
            
            curr_seq = seq.clone()
            trajectory_penicillin = []
            
            # --- Simulation sur l'horizon ---
            for t in range(horizon):
                # 1. Prédiction LSTM
                pred = self.model(curr_seq) # (1, n_outputs)
                trajectory_penicillin.append(pred[0, self.target_idx])
                
                # 2. Préparer l'entrée t+1 basée sur t
                last_input = curr_seq[0, -1, :].clone()
                
                # A. Appliquer les contrôles optimisés (u_future)
                for i, ctrl_idx in enumerate(self.control_indices):
                    last_input[ctrl_idx] = u_future[t, i]
                
                # B. Mise à jour physique du VOLUME (Bilan de masse simplifié)
                # Volume(t+1) = Volume(t) + Somme(Flux entrants) * dt - Evaporation
                # Attention : Tout est scalé ici. C'est complexe de faire l'équation physique exacte sur des données scalées.
                # APPROXIMATION ROBUSTE POUR LE MPC : 
                # On laisse le LSTM prédire le volume s'il est dans les outputs, SINON on le laisse constant 
                # ou on le met à jour approximativement si on dé-scale.
                # ICI : 'Vessel Volume' est une entrée, pas une sortie du LSTM. On doit l'estimer.
                # Pour simplifier dans ce script "prêt à l'emploi", on va supposer que le volume varie peu 
                # sur 10h ou suit la tendance précédente, car dé-scaler/re-scaler dans la boucle de gradient casse le gradient.
                # On laisse la valeur précédente (hold).
                
                # C. Réinjecter les prédictions (Autoregression)
                # Les sorties du modèle (P, P_off, X_off, NH3_off) remplacent les valeurs dans input
                last_input[start_output_idx:] = pred[0]
                
                # D. Slide window
                new_input = last_input.unsqueeze(0).unsqueeze(0)
                curr_seq = torch.cat((curr_seq[:, 1:, :], new_input), dim=1)
            
            # --- Fonction de Coût ---
            # On veut maximiser la Pénicilline finale
            final_yield = trajectory_penicillin[-1]
            
            # Pénalité si on change les vannes trop violemment (lissage)
            smoothness = torch.sum((u_future[1:] - u_future[:-1])**2)
            
            loss = -final_yield + 0.1 * smoothness
            loss.backward()
            optimizer.step()
            
            # --- CLAMPING (Respect des contraintes physiques) ---
            with torch.no_grad():
                for i in range(len(self.control_indices)):
                     u_future[:, i].clamp_(self.control_mins_tensor[i], self.control_maxs_tensor[i])
            
            if final_yield.item() > best_reward:
                best_reward = final_yield.item()
                best_u = u_future.detach().clone()
                
        return best_u

# ==========================================
# 4. EXÉCUTION DU MPC
# ==========================================

# Initialisation du contrôleur
mpc = BioreactorMPC(model, scaler_X, scaler_y, input_cols, output_cols)

# --- Simulation d'une donnée temps réel ---
# On prend une séquence aléatoire valide du dataset d'entraînement pour l'exemple
# Dans la réalité, ce serait : data_live = system.get_last_60_points()
data = pd.read_csv('indpensim-notebook/Mendeley_data/100_Batches_IndPenSim_V3.csv') # Re-load pour l'exemple
data = data.dropna(subset=output_cols).reset_index(drop=True)
data[output_cols] = data[output_cols].ffill()
input_data = data[input_cols].values
input_data_scaled = scaler_X.transform(input_data)

# Prenons une séquence au milieu d'un batch
current_idx = 1000 
current_sequence = input_data_scaled[current_idx : current_idx + seq_length]

print(f"\n--- Démarrage de l'optimisation MPC à t={current_idx} ---")
horizon_h = 5 # Optimiser sur 5 heures
optimal_controls_scaled = mpc.optimize(current_sequence, horizon=horizon_h, steps=50)

# ==========================================
# 5. AFFICHAGE DES RÉSULTATS (DÉ-SCALÉS)
# ==========================================

# On doit dé-scaler pour avoir les vraies valeurs (L/h, RPM, etc.)
# Création d'une matrice dummy pour l'inverse transform
res_array = np.zeros((horizon_h, len(input_cols)))
# On remplit avec les moyennes pour le "bruit de fond"
res_array[:] = scaler_X.mean_ 

# On insère nos contrôles optimisés
opt_ctrl_np = optimal_controls_scaled.numpy()
for i, ctrl_idx in enumerate(mpc.control_indices):
    res_array[:, ctrl_idx] = opt_ctrl_np[:, i]

# Inverse transform
res_unscaled = scaler_X.inverse_transform(res_array)

# Extraction des colonnes intéressantes
df_result = pd.DataFrame(res_unscaled[:, mpc.control_indices], columns=mpc.ctrl_vars.keys())
df_result.index.name = "Heure Future (+t)"

print("\n📋 STRATÉGIE DE CONTRÔLE OPTIMISÉE :")
print(df_result.round(2))

print("\n👉 Prochaine action immédiate (t+1) à envoyer aux automates :")
next_action = df_result.iloc[0]
for name, val in next_action.items():
    print(f" - {name} : {val:.2f}")