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

import numpy as np
import pickle
import matplotlib.pyplot as plt
from indpensim_run import indpensim_run
from generate_batch_records import generate_batch_records
from IndPenSim_QbD_Figure_properties import get_figure_properties

def main():
    # Configuration flags
    data_generation_flag = 2  # 1 - Generate data for a fixed time interval
                              # 2 - Generate Fixed number of batches (generate Normal and Fault batches)
    operational_days = 336
    bioreactor_turn_around_time = 3
    
    # Initialize batch run flags dictionary
    batch_run_flags = {}
    
    if data_generation_flag == 1:
        # Select number of batches to generate
        production_phase_in_years = 0.2  # Selecting a Production phase in year (1 year = 365 days)
        max_theoritical_number_of_batches = round((production_phase_in_years * operational_days) / 11)
        num_of_batches = max_theoritical_number_of_batches
        
        batch_run_flags['Batch_fault_order_reference'] = np.zeros(num_of_batches, dtype=int)
        batch_run_flags['Control_strategy'] = np.ones(num_of_batches, dtype=int)  # 0 - Recipe driven (SBC)
                                                                                  # 1 - Operator controller batches
        batch_run_flags['Batch_length'] = np.ones(num_of_batches, dtype=int)  # 0 - Fixed Batch length
                                                                              # 1 - Uneven batch length
        batch_run_flags['Raman_spec'] = np.zeros(num_of_batches, dtype=int)  # 0 - Don't Record Raman data
                                                                             # 1 - Record Raman Data
                                                                             # 2 - Use Raman data to control PAA
    else:
        batch_run_flags['Batch_fault_order_reference'] = np.array([0, 1])  # Fault reference
        batch_run_flags['Control_strategy'] = np.array([0, 1])  # 0 - Recipe driven (SBC)
                                                                # 1 - Operator controller batches
        batch_run_flags['Batch_length'] = np.array([1, 0])  # 0 - Fixed Batch length
                                                            # 1 - Uneven batch length
        batch_run_flags['Raman_spec'] = np.array([1, 2])  # 0 - Don't Record Raman data
                                                          # 1 - Record Raman Data
                                                          # 2 - Use Raman data to control PAA
        
        num_of_batches = len(batch_run_flags['Batch_fault_order_reference'])
        production_phase_in_years = (num_of_batches * (11 + 3)) / operational_days
    
    save_batch_flag = 1  # 1 - save data, 0 - don't save data
    batches_file_name = 'IndPenSim_V2_export_V7'
    generate_batch_flag = 1  # 1 - Generate Batches and Plot figures, 0 - Load data from workspace and plot figures
    
    # Generate batches
    if generate_batch_flag == 1:
        batch_start = 1
        raw_batch_data = {}
        summary_of_campaign = []
        
        for batch_no in range(batch_start, num_of_batches + 1):
            mat_file_name = f'Batch_{batch_no:02d}'
            print(f'\n=== Generating {mat_file_name} ===')
            
            Xref = indpensim_run(batch_no, batch_run_flags)
            raw_batch_data[mat_file_name] = Xref
            
            # Summary statistics
            stats_row = [
                raw_batch_data[mat_file_name]['Stats']['Penicllin_harvested_during_batch'],
                raw_batch_data[mat_file_name]['Stats']['Penicllin_harvested_end_of_batch'],
                raw_batch_data[mat_file_name]['Stats']['Penicllin_yield_total'],
                raw_batch_data[mat_file_name]['Fg']['t'][-1] / 24
            ]
            summary_of_campaign.append(stats_row)
            
            # Check if we've exceeded the production phase duration
            summary_of_batch_lengths = np.sum(np.ceil([row[3] for row in summary_of_campaign])) + \
                                     batch_no * bioreactor_turn_around_time
            
            if summary_of_batch_lengths > production_phase_in_years * operational_days:
                num_of_batches = batch_no
                break
        
        # Generate batch records and CSV files
        print('\n=== Generating Batch Records ===')
        batch_records = generate_batch_records(raw_batch_data, batches_file_name, batch_run_flags)
        
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
        
        # Plotting
        print('\n=== Generating Plots ===')
        # MODIFICATION ICI: On passe aussi batch_run_flags pour avoir les infos des légendes
        plot_batches(batch_records, batch_start, num_of_batches, batch_run_flags)
        
        print('\n=== Simulation Complete ===')
        print(f'Total batches generated: {num_of_batches}')
        print(f'Production phase duration: {production_phase_in_years:.2f} years')

def plot_batches(batch_records, batch_start, num_of_batches, batch_run_flags):
    """Affiche les variables des batches dans des figures contenant 4 graphiques chacune"""

    variable_mapping = {
        # ... (votre mapping reste identique)
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
    all_vars = [v for v in batch_records[first_batch_key].keys() if v not in ['Stats', 'Raman_Spec']]

    # Nombre de graphiques par figure
    n_cols = 2
    n_rows = 2
    vars_per_fig = n_cols * n_rows

    # Découper la liste des variables en groupes de 4
    for i in range(0, len(all_vars), vars_per_fig):
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, 10))
        fig.patch.set_facecolor('white')
        axes_flat = axes.flatten() # Pour itérer facilement sur les 4 subplots
        
        any_plot_in_fig = False

        for j in range(vars_per_fig):
            ax = axes_flat[j]
            if (i + j) < len(all_vars):
                var_name = all_vars[i + j]
                has_data = False

                # Boucle sur les batches pour la variable en cours
                for batch_no in range(batch_start, num_of_batches + 1):
                    mat_file_name = f'Batch_{batch_no:02d}'
                    
                    if mat_file_name in batch_records and var_name in batch_records[mat_file_name]:
                        batch_var = batch_records[mat_file_name][var_name]
                        if 't' in batch_var and 'y' in batch_var:
                            has_data = True
                            any_plot_in_fig = True
                            
                            # Logique de label (Identique à votre code)
                            idx = batch_no - 1
                            fault_id = batch_run_flags['Batch_fault_order_reference'][idx] if idx < len(batch_run_flags['Batch_fault_order_reference']) else 0
                            fault_str = "Normal" if fault_id == 0 else f"Faute {fault_id}"
                            ctrl_id = batch_run_flags['Control_strategy'][idx] if idx < len(batch_run_flags['Control_strategy']) else 0
                            ctrl_str = "SBC" if ctrl_id == 0 else "Opérateur"
                            
                            label = f'B{batch_no}: {fault_str}' # Version courte pour la légende
                            
                            ax.plot(batch_var['t'], batch_var['y'], 
                                    color=props['cmap'](idx), 
                                    linewidth=1.5, label=label)
                
                if has_data:
                    title = variable_mapping.get(var_name, var_name)
                    ax.set_title(title, fontsize=10, fontweight='bold')
                    ax.grid(True, alpha=0.3)
                    # On n'affiche la légende que si nécessaire (peut être encombrant à 4)
                    if j == 0: # Exemple: uniquement sur le premier subplot de chaque figure
                         ax.legend(loc='best', fontsize=7, ncol=2)
                else:
                    ax.axis('off') # Cache le subplot s'il n'y a pas de données
            else:
                ax.axis('off') # Cache les subplots vides (ex: 2 variables sur les 4 slots)

        if any_plot_in_fig:
            plt.tight_layout()
        else:
            plt.close(fig)

    plt.show()

if __name__ == '__main__':
    main()