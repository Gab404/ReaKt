import torch
import joblib
import os
import json
import numpy as np
import pandas as pd
from lstm.model import LSTMModel
from mpc import BioreactorMPC

class AIController:
    _instance = None
    
    @classmethod
    def get_instance(cls, model_dir='./saved_model'):
        if cls._instance is None:
            cls._instance = cls(model_dir)
        return cls._instance

    def __init__(self, model_dir):
        print("--- [AI] Loading Digital Twin Model... ---")
        
        # 1. Config
        meta_path = os.path.join(model_dir, "dataset_metadata.json")
        with open(meta_path, 'r') as f:
            self.meta = json.load(f)
            
        self.input_cols = self.meta['input_columns']
        self.output_cols = self.meta['output_columns']
        self.control_cols = self.meta.get('control_columns', [])
        
        # 2. Scalers
        self.scaler_X = joblib.load(os.path.join(model_dir, "scaler_X.pkl"))
        self.scaler_y = joblib.load(os.path.join(model_dir, "scaler_y.pkl"))
        
        # 3. Model
        model_path = os.path.join(model_dir, "lstm_dynamics.pt")
        checkpoint = torch.load(model_path, map_location='cpu')
        
        self.model = LSTMModel(len(self.input_cols), checkpoint['hidden_size'], len(self.output_cols))
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()
        
        # 4. MPC
        self.mpc = BioreactorMPC(self.model, self.scaler_X, self.scaler_y, 
                                 self.input_cols, self.output_cols, self.control_cols)
        
        # Mapping: Variables courtes (simu) -> Variables longues (modèle)
        self.key_mapping = {
            'S': 'Substrate concentration(S:g/L)',
            'DO2': 'Dissolved oxygen concentration(DO2:mg/L)',
            'P': 'Penicillin concentration(P:g/L)',
            'V': 'Vessel Volume(V:L)',
            'Wt': 'Vessel Weight(Wt:Kg)',
            'pH': 'pH(pH:pH)',
            'T': 'Temperature(T:K)',
            'Q': 'Generated heat(Q:kJ)',
            'pressure': 'Air head pressure(pressure:bar)',
            'OUR': 'Oxygen Uptake Rate(OUR:(g min^{-1}))',
            'CER': 'Carbon evolution rate(CER:g/h)',
            'Fg': 'Aeration rate(Fg:L/h)',
            'Fs': 'Sugar feed rate(Fs:L/h)',
            'Fa': 'Acid flow rate(Fa:L/h)',
            'Fb': 'Base flow rate(Fb:L/h)',
            'Fc': 'Heating/cooling water flow rate(Fc:L/h)',
            'Fh': 'Heating water flow rate(Fh:L/h)',
            'Fw': 'Water for injection/dilution(Fw:L/h)',
            'Foil': 'Oil flow(Foil:L/hr)',
            'Fpaa': 'PAA flow(Fpaa:PAA flow (L/h))',
            'Fremoved': 'Dumped broth flow(Fremoved:L/h)',
            'NH3_offline': 'NH_3 concentration off-line(NH3_offline:NH3 (g L^{-1}))',
            'Viscosity_offline': 'Viscosity(Viscosity_offline:centPoise)',
            'PAA_offline': 'PAA concentration offline(PAA_offline:PAA (g L^{-1}))',
            'P_offline': 'Offline Penicillin concentration(P_offline:P(g L^{-1}))',
            'X_offline': 'Offline Biomass concentratio(X_offline:X(g L^{-1}))',
            'Time': 'Time (h)'
        }
        self.reverse_mapping = {v: k for k, v in self.key_mapping.items()}

    def get_action(self, X_history, k, seq_len=60):
        try:
            # 1. Extraction (Fenêtre glissante)
            idx_start = max(0, k - seq_len + 1)
            idx_end = k + 1
            
            data_dict = {}
            for model_col in self.input_cols:
                if model_col in self.reverse_mapping:
                    short_name = self.reverse_mapping[model_col]
                    
                    if short_name == 'Time':
                        data_dict[model_col] = np.arange(idx_end - idx_start) * 0.2
                    elif short_name in X_history:
                        series = X_history[short_name]['y'][idx_start:idx_end]
                        if len(series) < seq_len:
                            pad_width = seq_len - len(series)
                            series = np.pad(series, (pad_width, 0), mode='edge')
                        data_dict[model_col] = series
                    else:
                        data_dict[model_col] = np.zeros(seq_len)
            
            df = pd.DataFrame(data_dict)
            
            # 2. Scaling & MPC
            X_scaled = self.scaler_X.transform(df)
            best_controls_scaled = self.mpc.optimize(X_scaled, horizon=5, steps=5)
            
            # 3. Dé-scaling (Action immédiate t+1)
            last_row_scaled = X_scaled[-1, :].copy()
            action_scaled = best_controls_scaled[0, :]
            
            for i, c_idx in enumerate(self.mpc.ctrl_indices):
                last_row_scaled[c_idx] = action_scaled[i]
                
            action_physical_vector = self.scaler_X.inverse_transform(last_row_scaled.reshape(1, -1))[0]
            
            # 4. Packaging
            response = {}
            for col_name, val in zip(self.input_cols, action_physical_vector):
                # Check if it is a control var
                is_control = False
                for c in self.control_cols:
                    if c['name'] == col_name:
                        is_control = True
                        break
                
                if is_control and col_name in self.reverse_mapping:
                    short_name = self.reverse_mapping[col_name]
                    response[short_name] = max(0.0, float(val))
                    
            return response

        except Exception as e:
            print(f"[AI ERROR] {e}")
            return None