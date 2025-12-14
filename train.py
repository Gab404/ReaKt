import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader, random_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
import matplotlib.pyplot as plt
import joblib
import os

data = pd.read_csv('indpensim-notebook/Mendeley_data/100_Batches_IndPenSim_V3.csv')

process_cols = [
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

output_cols = [
    'Penicillin concentration(P:g/L)',
    'Offline Penicillin concentration(P_offline:P(g L^{-1}))',
    'Offline Biomass concentratio(X_offline:X(g L^{-1}))',
    'NH_3 concentration off-line(NH3_offline:NH3 (g L^{-1}))'
]


# garder uniquement les lignes où les sorties existent au moins une fois
data = data.dropna(subset=output_cols).reset_index(drop=True)

# rendre les sorties disponibles à chaque pas de temps
data[output_cols] = data[output_cols].ffill()

input_cols = process_cols + output_cols

scaler_X = StandardScaler()
scaler_y = StandardScaler()

X_scaled = scaler_X.fit_transform(data[input_cols])
y_scaled = scaler_y.fit_transform(data[output_cols])

sequence_length = 60
X_seq, y_seq = [], []

for i in range(len(data) - sequence_length - 1):
    X_seq.append(X_scaled[i:i+sequence_length])
    y_seq.append(y_scaled[i+sequence_length])  # SORTIES à t+1

X_seq = np.array(X_seq, dtype=np.float32)
y_seq = np.array(y_seq, dtype=np.float32)

print("X_seq:", X_seq.shape)
print("y_seq:", y_seq.shape)

class BioreactorDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X)
        self.y = torch.tensor(y)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

dataset = BioreactorDataset(X_seq, y_seq)

train_size = int(0.7 * len(dataset))
val_size = int(0.15 * len(dataset))
test_size = len(dataset) - train_size - val_size

train_ds, val_ds, test_ds = random_split(dataset, [train_size, val_size, test_size])

train_loader = DataLoader(train_ds, batch_size=32, shuffle=True)
val_loader = DataLoader(val_ds, batch_size=32)
test_loader = DataLoader(test_ds, batch_size=32)

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

model = LSTMModel(X_seq.shape[2], 128, len(output_cols))
criterion = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

num_epochs = 20
train_losses, val_losses = [], []

for epoch in range(num_epochs):
    model.train()
    train_loss = 0

    for Xb, yb in train_loader:
        optimizer.zero_grad()
        loss = criterion(model(Xb), yb)
        loss.backward()
        optimizer.step()
        train_loss += loss.item()

    train_loss /= len(train_loader)

    model.eval()
    val_loss = 0
    with torch.no_grad():
        for Xb, yb in val_loader:
            val_loss += criterion(model(Xb), yb).item()

    val_loss /= len(val_loader)

    train_losses.append(train_loss)
    val_losses.append(val_loss)

    print(f"Epoch {epoch+1} | Train {train_loss:.5f} | Val {val_loss:.5f}")

model.eval()
y_pred, y_true = [], []

with torch.no_grad():
    for Xb, yb in test_loader:
        y_pred.append(model(Xb).numpy())
        y_true.append(yb.numpy())

y_pred = scaler_y.inverse_transform(np.vstack(y_pred))
y_true = scaler_y.inverse_transform(np.vstack(y_true))

rmse = np.sqrt(mean_squared_error(y_true, y_pred))
r2 = r2_score(y_true, y_pred)

print(f"RMSE (global): {rmse:.3f}")
print(f"R² (global): {r2:.4f}")


plt.plot(train_losses, label="Train")
plt.plot(val_losses, label="Validation")
plt.legend()
plt.xlabel("Epoch")
plt.ylabel("MSE")
plt.title("LSTM multi-output t+1")
plt.show()


os.makedirs("saved_model", exist_ok=True)

torch.save({
    "model_state_dict": model.state_dict(),
    "input_cols": input_cols,
    "output_cols": output_cols,
    "sequence_length": sequence_length
}, "saved_model/lstm_dynamics.pt")

joblib.dump(scaler_X, "saved_model/scaler_X.pkl")
joblib.dump(scaler_y, "saved_model/scaler_y.pkl")

print("✅ Modèle dynamique multi-output sauvegardé")

num_points = 300  # nombre de points affichés (évite les graphes illisibles)
time_axis = np.arange(num_points)

fig, axes = plt.subplots(len(output_cols), 1, figsize=(10, 12), sharex=True)

for i, col in enumerate(output_cols):
    axes[i].plot(time_axis, y_true[:num_points, i], label="Réel", linewidth=2)
    axes[i].plot(time_axis, y_pred[:num_points, i], label="Prédit", linestyle="--")
    axes[i].set_ylabel(col)
    axes[i].grid(True)
    axes[i].legend()

axes[-1].set_xlabel("Index temporel (test set)")
plt.suptitle("Prédictions LSTM vs valeurs réelles (test set)", fontsize=14)
plt.tight_layout()
plt.show()