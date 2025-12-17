import torch
import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt
import joblib
import os
import argparse
from sklearn.metrics import mean_squared_error, r2_score
from model import LSTMModel
from preprocess import get_dataloaders

DEFAULT_DATA_PATH = 'indpensim-notebook/Mendeley_data/100_Batches_IndPenSim_V3.csv'
SEQUENCE_LENGTH = 60
HIDDEN_SIZE = 128
LEARNING_RATE = 1e-3

def parse_arguments():
    parser = argparse.ArgumentParser(description="Script d'entraînement pour le modèle LSTM Bioreactor")
    
    parser.add_argument('--path-to-dataset', type=str, default=DEFAULT_DATA_PATH, 
                        help='Chemin vers le fichier CSV de données')
    
    parser.add_argument('--save-dir', type=str, default='saved_model', 
                        help='Dossier où sauvegarder le modèle et les scalers')
    
    parser.add_argument('--epoch', type=int, default=20, 
                        help="Nombre d'époques d'entraînement")
    
    parser.add_argument('--batch-size', type=int, default=32, 
                        help='Taille du batch pour les dataloaders')

    return parser.parse_args()

def train_step(model, loader, criterion, optimizer):
    model.train()
    total_loss = 0
    for Xb, yb in loader:
        optimizer.zero_grad()
        output = model(Xb)
        loss = criterion(output, yb)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    return total_loss / len(loader)

def evaluate_step(model, loader, criterion):
    model.eval()
    total_loss = 0
    with torch.no_grad():
        for Xb, yb in loader:
            output = model(Xb)
            loss = criterion(output, yb)
            total_loss += loss.item()
    return total_loss / len(loader)

def main():
    args = parse_arguments()
    
    print(f"--- Configuration ---")
    print(f"Dataset   : {args.path_to_dataset}")
    print(f"Save Dir  : {args.save_dir}")
    print(f"Epochs    : {args.epoch}")
    print(f"Batch Size: {args.batch_size}")
    print(f"---------------------")

    print("Loading and data preprocessing...")
    try:
        loaders, scaler_X, scaler_y, meta = get_dataloaders(
            args.path_to_dataset, 
            args.save_dir,
            SEQUENCE_LENGTH, 
            args.batch_size
        )
    except FileNotFoundError:
        print(f"ERREUR : Le fichier {args.path_to_dataset} est introuvable.")
        return

    model = LSTMModel(input_size=meta['input_dim'], 
                      hidden_size=HIDDEN_SIZE, 
                      output_size=meta['output_dim'])
    
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    
    print("Start training...")
    train_losses, val_losses = [], []
    
    for epoch in range(args.epoch):
        train_loss = train_step(model, loaders['train'], criterion, optimizer)
        val_loss = evaluate_step(model, loaders['val'], criterion)
        
        train_losses.append(train_loss)
        val_losses.append(val_loss)
        
        print(f"Epoch {epoch+1}/{args.epoch} | Train Loss: {train_loss:.5f} | Val Loss: {val_loss:.5f}")

    print("\nEvaluation on the test dataset...")
    model.eval()
    y_pred, y_true = [], []
    
    with torch.no_grad():
        for Xb, yb in loaders['test']:
            y_pred.append(model(Xb).numpy())
            y_true.append(yb.numpy())
            
    y_pred = scaler_y.inverse_transform(np.vstack(y_pred))
    y_true = scaler_y.inverse_transform(np.vstack(y_true))
    
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    
    print(f"RMSE (global): {rmse:.3f}")
    print(f"R² (global): {r2:.4f}")

    plt.figure(figsize=(10, 5))
    plt.plot(train_losses, label="Train")
    plt.plot(val_losses, label="Validation")
    plt.legend()
    plt.xlabel("Epoch")
    plt.ylabel("MSE")
    plt.title("Training Loss")
    plt.show()

    num_points = 300
    time_axis = np.arange(num_points)
    fig, axes = plt.subplots(meta['output_dim'], 1, figsize=(10, 12), sharex=True)
    
    for i, col in enumerate(meta['output_cols']):
        axes[i].plot(time_axis, y_true[:num_points, i], label="Réel", linewidth=2)
        axes[i].plot(time_axis, y_pred[:num_points, i], label="Prédit", linestyle="--")
        axes[i].set_ylabel(col)
        axes[i].grid(True)
        axes[i].legend()
    
    axes[-1].set_xlabel("Index temporel (test set)")
    plt.suptitle("Predicitions vs Ground Truth (Test Set)", fontsize=14)
    plt.tight_layout()
    plt.show()

    os.makedirs(args.save_dir, exist_ok=True)
    
    torch.save({
        "model_state_dict": model.state_dict(),
        "input_cols": meta['input_cols'],
        "output_cols": meta['output_cols'],
        "sequence_length": SEQUENCE_LENGTH,
        "hidden_size": HIDDEN_SIZE
    }, os.path.join(args.save_dir, "lstm_dynamics.pt"))
    
    joblib.dump(scaler_X, os.path.join(args.save_dir, "scaler_X.pkl"))
    joblib.dump(scaler_y, os.path.join(args.save_dir, "scaler_y.pkl"))
    
    print(f"Model correctly saved in '{args.save_dir}'")

if __name__ == "__main__":
    main()