import pandas as pd
import numpy as np
import torch
import json
import os
from torch.utils.data import Dataset, DataLoader, random_split
from sklearn.preprocessing import StandardScaler

# --- CONFIGURATION DES COLONNES ---
# Toutes les entrées
PROCESS_COLS = [
    'Time (h)', 'Aeration rate(Fg:L/h)', 'Agitator RPM(RPM:RPM)',
    'Sugar feed rate(Fs:L/h)', 'Acid flow rate(Fa:L/h)',
    'Base flow rate(Fb:L/h)', 'Heating/cooling water flow rate(Fc:L/h)',
    'Heating water flow rate(Fh:L/h)', 'Water for injection/dilution(Fw:L/h)',
    'pH(pH:pH)', 'Temperature(T:K)',
    'Dissolved oxygen concentration(DO2:mg/L)',
    'Air head pressure(pressure:bar)', 'Vessel Volume(V:L)',
    'Generated heat(Q:kJ)', 'Oxygen Uptake Rate(OUR:(g min^{-1}))',
    'Carbon evolution rate(CER:g/h)', 'Substrate concentration(S:g/L)'
]

# Les sorties à prédire
OUTPUT_COLS = [
    'Penicillin concentration(P:g/L)',
    'Offline Penicillin concentration(P_offline:P(g L^{-1}))',
    'Offline Biomass concentratio(X_offline:X(g L^{-1}))',
    'NH_3 concentration off-line(NH3_offline:NH3 (g L^{-1}))'
]

# --- NOUVEAU : Liste des paramètres que le MPC a le droit de modifier ---
CONTROL_COLS = [
    'Aeration rate(Fg:L/h)',
    'Sugar feed rate(Fs:L/h)',
    'Acid flow rate(Fa:L/h)',
    'Base flow rate(Fb:L/h)',
    'Temperature(T:K)',
    'Agitator RPM(RPM:RPM)' # Ajouté pour l'exemple
]

# ... (La classe BioreactorDataset reste inchangée) ...
class BioreactorDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)
    def __len__(self): return len(self.X)
    def __getitem__(self, idx): return self.X[idx], self.y[idx]

def load_data(filepath):
    # ... (inchangé) ...
    data = pd.read_csv(filepath)
    data = data.dropna(subset=OUTPUT_COLS).reset_index(drop=True)
    data[OUTPUT_COLS] = data[OUTPUT_COLS].ffill()
    return data

def create_sequences(X_scaled, y_scaled, sequence_length):
    # ... (inchangé) ...
    X_seq, y_seq = [], []
    for i in range(len(X_scaled) - sequence_length - 1):
        X_seq.append(X_scaled[i:i+sequence_length])
        y_seq.append(y_scaled[i+sequence_length]) 
    return np.array(X_seq), np.array(y_seq)

def save_dataset_metadata(df, input_cols, output_cols, control_cols, save_dir):
    """
    Sauvegarde les métadonnées incluant la configuration spécifique 
    pour les contrôles MPC (min/max observés).
    """
    stats = {}
    all_cols = input_cols
    
    # 1. Stats globales
    for col in all_cols:
        stats[col] = {
            "min": float(df[col].min()),
            "max": float(df[col].max()),
            "mean": float(df[col].mean()),
            "std": float(df[col].std())
        }

    # 2. Configuration spécifique MPC (Paramètres modifiables)
    # On extrait les min/max pour définir les bornes physiques par défaut du MPC
    mpc_settings = []
    for col in control_cols:
        if col in input_cols:
            mpc_settings.append({
                "name": col,
                "min": float(df[col].min()), # Borne inf par défaut
                "max": float(df[col].max())  # Borne sup par défaut
            })

    metadata_content = {
        "input_columns": input_cols,
        "output_columns": output_cols,
        "control_columns": mpc_settings, # <--- C'est ici qu'on stocke la config MPC
        "statistics": stats
    }

    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, "dataset_metadata.json")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(metadata_content, f, indent=4)
    
    print(f"📄 Métadonnées (avec config MPC) sauvegardées dans : {file_path}")

def get_dataloaders(filepath, save_dir, sequence_length=60, batch_size=32):
    data = load_data(filepath)
    input_cols = PROCESS_COLS + OUTPUT_COLS
    
    # --- MODIFICATION ICI ---
    # On passe CONTROL_COLS à la fonction de sauvegarde
    save_dataset_metadata(data, input_cols, OUTPUT_COLS, CONTROL_COLS, save_dir)
    
    scaler_X = StandardScaler()
    scaler_y = StandardScaler()
    
    X_scaled = scaler_X.fit_transform(data[input_cols])
    y_scaled = scaler_y.fit_transform(data[OUTPUT_COLS])
    
    X_seq, y_seq = create_sequences(X_scaled, y_scaled, sequence_length)
    
    dataset = BioreactorDataset(X_seq, y_seq)
    train_size = int(0.7 * len(dataset))
    val_size = int(0.15 * len(dataset))
    test_size = len(dataset) - train_size - val_size
    
    train_ds, val_ds, test_ds = random_split(dataset, [train_size, val_size, test_size])
    
    loaders = {
        'train': DataLoader(train_ds, batch_size=batch_size, shuffle=True),
        'val': DataLoader(val_ds, batch_size=batch_size),
        'test': DataLoader(test_ds, batch_size=batch_size)
    }
    
    metadata = {
        'input_cols': input_cols,
        'output_cols': OUTPUT_COLS,
        'input_dim': X_seq.shape[2],
        'output_dim': len(OUTPUT_COLS)
    }
    
    return loaders, scaler_X, scaler_y, metadata