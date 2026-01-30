"""
Generate multiple batches for a given Production phase. 
IndPenSim_V2.01 Main file (Converted to Python)
Last editted 9th of July 2019
Objective: Generates batches for analysis

Copyright
Stephen Goldrick Apr 2019 
Contact: s.goldrick@ucl.ac.uk
University College London, The University of Manchester, Newcastle University and Perceptive Engineering
Please reference: "The Development of an Industrial Scale Fed-Batch
Fermentation Simulation", Stepen Goldrick, Andrei Stefen, David Lovett,
Gary Montague, Barry Lennox, Journal of Biotechnology 2015
(https://www.sciencedirect.com/science/article/pii/S0168165614009377)
And also please reference:  
and "Modern day control challenges for industrial-scale fermentation
processes" Goldrick et al. 2018 Computers and Chemical Engineering 
All rights reserved. Copyright (c) The University of Manchester, University College London, Newcastle University and Perceptive Engineering.
"""
"""
Generate multiple batches for a given Production phase. 
IndPenSim_V2.01 Main file (Converted to Python & Updated for AI Twin Experiment)
"""

import numpy as np
import pickle
import matplotlib.pyplot as plt
import argparse  # ### AJOUT 1 : Import de argparse ###

# Import des modules nécessaires
from indpensim_run import indpensim_run
from generate_batch_records import generate_batch_records
from IndPenSim_QbD_Figure_properties import get_figure_properties

def main():
    # ### AJOUT 2 : Configuration du parser d'arguments ###
    parser = argparse.ArgumentParser(description="Simulation IndPenSim avec sélection du dossier de modèle.")
    
    # On définit l'argument --model-dir
    # 'default' permet d'avoir une valeur par défaut si l'utilisateur ne précise rien
    parser.add_argument('--model-dir', 
                        type=str, 
                        default='./saved_model', 
                        help='Chemin vers le dossier contenant les modèles à charger')
    
    # On récupère les arguments
    args = parser.parse_args()

    # --- Configuration flags ---
    data_generation_flag = 2  # 2 - Generate Fixed number of batches
    operational_days = 336
    bioreactor_turn_around_time = 3
    
    # Initialize batch run flags dictionary
    batch_run_flags = {}
    
    if data_generation_flag == 1:
        production_phase_in_years = 0.2 
        max_theoritical_number_of_batches = round((production_phase_in_years * operational_days) / 11)
        num_of_batches = max_theoritical_number_of_batches
        
        batch_run_flags['Batch_fault_order_reference'] = np.zeros(num_of_batches, dtype=int)
        batch_run_flags['Control_strategy'] = np.ones(num_of_batches, dtype=int)
        batch_run_flags['Batch_length'] = np.ones(num_of_batches, dtype=int)
        batch_run_flags['Raman_spec'] = np.zeros(num_of_batches, dtype=int)
    else:
        # Configuration manuelle pour test
        batch_run_flags['Batch_fault_order_reference'] = np.array([0, 1]) 
        batch_run_flags['Control_strategy'] = np.array([0, 1]) 
        batch_run_flags['Batch_length'] = np.array([1, 0]) 
        batch_run_flags['Raman_spec'] = np.array([1, 2]) 
        
        num_of_batches = len(batch_run_flags['Batch_fault_order_reference'])
        production_phase_in_years = (num_of_batches * (11 + 3)) / operational_days
    
    save_batch_flag = 1 
    batches_file_name = 'IndPenSim_V2_export_V7'
    generate_batch_flag = 1 
    
    # Generate batches
    if generate_batch_flag == 1:
        batch_start = 1
        raw_batch_data = {}
        summary_of_campaign = []
        
        # Activer le mode interactif pour voir les plots pendant la boucle
        plt.ion() 
        
        # --- BOUCLE PRINCIPALE DE CAMPAGNE ---
        print("Démarrage de la campagne de production...")
        
        for batch_no in range(batch_start, num_of_batches + 1):
            mat_file_name = f'Batch_{batch_no:02d}'
            print(f'\n=== Processing {mat_file_name} / {num_of_batches} ===')
            
            # --- MODIFICATION TWIN EXPERIMENT ---
            
            # A. RUN BASELINE
            print(f"   > Running Baseline (Recipe)...")
            original_strategy = batch_run_flags['Control_strategy'][batch_no - 1]
            batch_run_flags['Control_strategy'][batch_no - 1] = 0
            X_baseline = indpensim_run(batch_no, batch_run_flags)
            
            # B. RUN AI MPC
            print(f"   > Running AI MPC (Digital Twin)...")
            batch_run_flags['Control_strategy'][batch_no - 1] = 2
            X_ai = indpensim_run(batch_no, batch_run_flags)
            
            # C. COMPARAISON & STOCKAGE
            raw_batch_data[mat_file_name] = X_ai 
            raw_batch_data[f"{mat_file_name}_Baseline"] = X_baseline 
            
            # Restauration stratégie
            batch_run_flags['Control_strategy'][batch_no - 1] = original_strategy

            # Comparaison rapide console
            p_base = X_baseline['Stats']['Penicllin_harvested_end_of_batch']
            p_ai = X_ai['Stats']['Penicllin_harvested_end_of_batch']
            gain = ((p_ai - p_base) / p_base) * 100 if p_base > 0 else 0
            print(f"   >>> Gain IA vs Baseline: {gain:+.2f}% ({p_ai:.0f} vs {p_base:.0f} g)")

            # --- AFFICHAGE DIRECT DANS LA BOUCLE ---
            print(f"   > Affichage courbes {mat_file_name}...")
            plot_comparison(X_baseline, X_ai, batch_no)
            
            # --- FIN MODIFICATION TWIN EXPERIMENT ---
            
            # Summary statistics
            stats_row = [
                raw_batch_data[mat_file_name]['Stats']['Penicllin_harvested_during_batch'],
                raw_batch_data[mat_file_name]['Stats']['Penicllin_harvested_end_of_batch'],
                raw_batch_data[mat_file_name]['Stats']['Penicllin_yield_total'],
                raw_batch_data[mat_file_name]['Fg']['t'][-1] / 24
            ]
            summary_of_campaign.append(stats_row)
            
            # Check duration limit
            summary_of_batch_lengths = np.sum(np.ceil([row[3] for row in summary_of_campaign])) + \
                                     batch_no * bioreactor_turn_around_time
            
            if summary_of_batch_lengths > production_phase_in_years * operational_days:
                print(f"\n--- Production Phase Limit Reached ({production_phase_in_years*operational_days:.1f} days) ---")
                num_of_batches = batch_no
                break
        
        # Désactiver le mode interactif pour que les fenêtres finales restent ouvertes
        plt.ioff()
        
        # Generate records
        print('\n=== Generating Batch Records ===')
        try:
            batch_records = generate_batch_records(raw_batch_data, batches_file_name, batch_run_flags)
        except Exception as e:
            print(f"Warning: generate_batch_records failed ({e}). Skipping CSV export.")
            batch_records = {}
        
        # Save data
        if save_batch_flag == 1:
            save_name = batches_file_name + '.pkl'
            with open(save_name, 'wb') as f:
                pickle.dump({
                    'Batch_Records': batch_records,
                    'Raw_Batch_data': raw_batch_data,
                    'Num_of_Batches': num_of_batches,
                    'Batch_start': batch_start,
                    'Summary_of_campaign': summary_of_campaign
                }, f)
            print(f'\nData saved to: {save_name}')
        
        # Plotting Standard (Tous les batches à la fin)
        print('\n=== Generating Standard Plots (Summary) ===')
        if batch_records:
            print("Generating Summary Plots for all batches (Extended View)...")
            plot_batches(batch_records, batch_start, num_of_batches, batch_run_flags, block=False)
        
        print("\n=== Simulation Complete. Fermez les fenêtres graphiques pour quitter. ===")
        plt.show() # Bloquant final


def plot_comparison(X_base, X_ai, batch_no):
    """
    Affiche une comparaison directe Baseline (Bleu) vs IA (Rouge).
    """
    try:
        t_base = X_base['P']['t']
        t_ai = X_ai['P']['t']
        
        fig, axes = plt.subplots(2, 3, figsize=(15, 8))
        fig.suptitle(f'Batch {batch_no}: Baseline (Blue) vs AI MPC (Red)', fontsize=14)
        
        # Penicillin
        ax = axes[0, 0]
        ax.plot(t_base, X_base['P']['y'], 'b--', label='Baseline')
        ax.plot(t_ai, X_ai['P']['y'], 'r-', label='AI MPC')
        ax.set_title('Penicillin (P)')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Biomass
        ax = axes[0, 1]
        ax.plot(t_base, X_base['X']['y'], 'b--')
        ax.plot(t_ai, X_ai['X']['y'], 'r-')
        ax.set_title('Biomass (X)')
        ax.grid(True, alpha=0.3)
        
        # Substrate
        ax = axes[0, 2]
        ax.plot(t_base, X_base['S']['y'], 'b--')
        ax.plot(t_ai, X_ai['S']['y'], 'r-')
        ax.set_title('Substrate (S)')
        ax.grid(True, alpha=0.3)

        # Actions de contrôle (Fs)
        ax = axes[1, 0]
        ax.plot(t_base, X_base['Fs']['y'], 'b--')
        ax.plot(t_ai, X_ai['Fs']['y'], 'r-')
        ax.set_title('Sugar Feed (Fs)')
        ax.grid(True, alpha=0.3)

        # Actions de contrôle (Fg)
        ax = axes[1, 1]
        ax.plot(t_base, X_base['Fg']['y'], 'b--')
        ax.plot(t_ai, X_ai['Fg']['y'], 'r-')
        ax.set_title('Aeration (Fg)')
        ax.grid(True, alpha=0.3)
        
        # Volume
        ax = axes[1, 2]
        ax.plot(t_base, X_base['V']['y'], 'b--')
        ax.plot(t_ai, X_ai['V']['y'], 'r-')
        ax.set_title('Volume (V)')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Astuce importante : pause pour laisser le temps au moteur graphique d'afficher
        plt.draw()
        plt.pause(3) # Pause de 3 secondes pour admirer le résultat du batch
        
    except Exception as e:
        print(f"Error plotting comparison: {e}")

def plot_batches(batch_records, batch_start, num_of_batches, batch_run_flags, block=False):
    # ... (Votre fonction plot_batches étendue 4x4 reste inchangée ici) ...
    # Assurez-vous simplement qu'elle ne contient pas de plt.show() bloquant
    # sauf si block=True
    variable_mapping = {
        'S': 'Substrate concentration(S:g/L)', 'DO2': 'Dissolved oxygen concentration(DO2:mg/L)',
        'O2': 'Oxygen content in off-gas(O2:%)', 'P': 'Penicillin concentration(P:g/L)',
        'V': 'Vessel Volume(V:L)', 'Wt': 'Vessel Weight(Wt:Kg)', 'pH': 'pH(pH:pH)',
        'T': 'Temperature(T:K)', 'Q': 'Generated heat(Q:kJ)', 'CO2outgas': 'Carbon dioxide content in off-gas(CO2:%)',
        'pressure': 'Air head pressure(pressure:bar)', 'OUR': 'Oxygen Uptake Rate(OUR:(g min^{-1}))',
        'CER': 'Carbon evolution rate(CER:g/h)', 'Fg': 'Aeration rate(Fg:L/h)',
        'RPM': 'Agitator RPM(RPM:RPM)', 'Fs': 'Sugar feed rate(Fs:L/h)',
        'Fa': 'Acid flow rate(Fa:L/h)', 'Fb': 'Base flow rate(Fb:L/h)',
        'Fc': 'Heating/cooling water flow rate(Fc:L/h)', 'Fh': 'Heating water flow rate(Fh:L/h)',
        'Fw': 'Water for injection/dilution(Fw:L/h)', 'Foil': 'Oil flow(Foil:L/hr)',
        'Fpaa': 'PAA flow(Fpaa:PAA flow (L/h))', 'Fremoved': 'Dumped broth flow(Fremoved:L/h)',
        'NH3_offline': 'NH_3 concentration off-line(NH3_offline:NH3 (g L^{-1}))',
        'Viscosity_offline': 'Viscosity(Viscosity_offline:centPoise)',
        'PAA_offline': 'PAA concentration offline(PAA_offline:PAA (g L^{-1}))',
        'P_offline': 'Offline Penicillin concentration(P_offline:P(g L^{-1}))',
        'X_offline': 'Offline Biomass concentratio(X_offline:X(g L^{-1}))'
    }

    props = get_figure_properties(num_of_batches)
    first_batch_key = f'Batch_{batch_start:02d}'
    
    if first_batch_key not in batch_records: return

    all_vars = [v for v in batch_records[first_batch_key].keys() if v not in ['Stats', 'Raman_Spec']]
    n_rows = 4; n_cols = 4; vars_per_fig = n_rows * n_cols

    for i in range(0, len(all_vars), vars_per_fig):
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(20, 12))
        fig.suptitle(f"Batch Data Overview (Variables {i+1}-{min(i+vars_per_fig, len(all_vars))})", fontsize=16)
        fig.patch.set_facecolor('white')
        
        if isinstance(axes, np.ndarray): axes_flat = axes.flatten()
        else: axes_flat = [axes]
            
        any_plot_in_fig = False

        for j in range(vars_per_fig):
            if j < len(axes_flat):
                ax = axes_flat[j]
                if (i + j) < len(all_vars):
                    var_name = all_vars[i + j]
                    has_data = False
                    for batch_no in range(batch_start, num_of_batches + 1):
                        mat_file_name = f'Batch_{batch_no:02d}'
                        if mat_file_name in batch_records and var_name in batch_records[mat_file_name]:
                            batch_var = batch_records[mat_file_name][var_name]
                            if 't' in batch_var and 'y' in batch_var:
                                has_data = True
                                any_plot_in_fig = True
                                idx = batch_no - 1
                                fault_id = batch_run_flags['Batch_fault_order_reference'][idx] if idx < len(batch_run_flags['Batch_fault_order_reference']) else 0
                                fault_str = "Normal" if fault_id == 0 else f"Faute {fault_id}"
                                label = f'B{batch_no}: {fault_str}'
                                ax.plot(batch_var['t'], batch_var['y'], color=props['cmap'](idx), linewidth=1.0, label=label)
                    
                    if has_data:
                        title = variable_mapping.get(var_name, var_name)
                        if len(title) > 30: title = title[:27] + "..."
                        ax.set_title(title, fontsize=8, fontweight='bold')
                        ax.grid(True, alpha=0.3)
                        if j == 0: ax.legend(loc='upper right', fontsize=6, ncol=1)
                    else: ax.axis('off')
                else: ax.axis('off')

        if any_plot_in_fig: plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        else: plt.close(fig)
    
    if block: plt.show()

if __name__ == '__main__':
    main()