import torch
import torch.optim as optim
import pandas as pd
import numpy as np
import torch.nn as nn
import gc  # <--- AJOUT IMPORT

class BioreactorMPC:
    def __init__(self, model, scaler_X, scaler_y, input_cols, output_cols, control_settings):
        self.model = model
        self.input_cols = input_cols
        self.target_idx_in_output = 0 
        print("INIT MPC")
        
        try:
            self.device = next(model.parameters()).device
        except StopIteration:
            self.device = torch.device('cpu')

        self.idx = {name: i for i, name in enumerate(input_cols)}
        
        self.ctrl_config = []
        for setting in control_settings:
            col_name = setting['name']
            if col_name in self.idx:
                self.ctrl_config.append({
                    'idx': self.idx[col_name],
                    'min': setting['min'],
                    'max': setting['max']
                })
        
        self.ctrl_indices = [c['idx'] for c in self.ctrl_config]
        
        dummy_min = pd.DataFrame([scaler_X.mean_], columns=input_cols)
        dummy_max = pd.DataFrame([scaler_X.mean_], columns=input_cols)
        
        for c in self.ctrl_config:
            dummy_min.iloc[0, c['idx']] = c['min']
            dummy_max.iloc[0, c['idx']] = c['max']
        
        self.min_t = torch.tensor(scaler_X.transform(dummy_min)[0, self.ctrl_indices], dtype=torch.float32).to(self.device)
        self.max_t = torch.tensor(scaler_X.transform(dummy_max)[0, self.ctrl_indices], dtype=torch.float32).to(self.device)
        
        self.start_out_idx = len(input_cols) - len(output_cols)

    def optimize(self, current_seq_np, horizon=5, steps=10):
        print("OPTIMIZE CALLED")
        # 1. Mode Train pour gradients
        was_training = self.model.training
        self.model.train()
        
        # 2. Freeze Dropout pour stabilité
        for module in self.model.modules():
            if isinstance(module, nn.Dropout):
                module.eval()

        # Init variables pour le bloc finally
        optimizer = None
        loss = None
        u_future = None

        try:
            seq = torch.tensor(current_seq_np, dtype=torch.float32, device=self.device).unsqueeze(0)
            u_future = torch.zeros(horizon, len(self.ctrl_indices), device=self.device, requires_grad=True)
            
            optimizer = optim.Adam([u_future], lr=0.1)
            
            for _ in range(steps):
                optimizer.zero_grad()
                curr = seq.clone()
                rewards = []
                
                for t in range(horizon):
                    pred = self.model(curr)
                    rewards.append(pred[0, self.target_idx_in_output]) 
                    
                    last_in = curr[0, -1, :].clone()
                    for i, c_idx in enumerate(self.ctrl_indices):
                        last_in[c_idx] = u_future[t, i]
                    
                    last_in[self.start_out_idx:] = pred[0]
                    curr = torch.cat((curr[:, 1:, :], last_in.view(1, 1, -1)), dim=1)
                
                loss = -torch.mean(torch.stack(rewards)) + 0.1 * torch.sum((u_future[1:] - u_future[:-1])**2)
                loss.backward()
                optimizer.step()
                
                with torch.no_grad():
                    for i in range(len(self.ctrl_indices)):
                        u_future[:, i].clamp_(self.min_t[i], self.max_t[i])
            
            result = u_future.detach().cpu().numpy()[0, :]
            return result

        finally:
            # 3. Restauration & Nettoyage Interne
            self.model.train(was_training)
            
            # Nettoyage des graphes de calcul intermédiaires
            del u_future, optimizer, loss
            if self.device.type == 'cuda':
                torch.cuda.empty_cache()
            gc.collect()