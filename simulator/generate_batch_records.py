import numpy as np
import pandas as pd
import pickle
import os

def generate_batch_records(raw_batch_data, batches_file_name, batch_run_flags):
    """
    Convertit les données brutes de simulation en un format structuré pour l'exportation (CSV et dictionnaire).
    Nettoie les variables inutiles et formate les données 'offline'.
    """
    
    # 1. Définition des champs à supprimer (identique au MATLAB)
    fields_to_remove = [
        'sc', 'abc', 'a0', 'a1', 'a3', 'a4', 'n0', 'n1', 'n2', 'n3', 'n4', 
        'n5', 'n6', 'n7', 'n8', 'n9', 'nm', 'phi0', 'Culture_age', 'mup', 
        'mux', 'X_CER', 'mu_X_calc', 'mu_P_calc', 'F_discharge_cal', 
        'CO2_d', 'S_pred', 'NH3', 'PAA', 'Viscosity', 'X', 
        'PRBS_noise_addition', 'PAA_pred', 'Stats', 'Fault_ref', 'Raman_Spec'
    ]
    # Note: J'ai ajouté 'Stats', 'Fault_ref' et 'Raman_Spec' à cette liste d'exclusion
    # car ils sont traités séparément ou structurellement différents dans la boucle ci-dessous.

    # Récupérer les clés du premier batch pour identifier les variables disponibles
    first_batch_key = list(raw_batch_data.keys())[0]
    all_variables = list(raw_batch_data[first_batch_key].keys())
    
    # Filtrer les variables à garder pour le fichier CSV principal
    variables_to_export = [v for v in all_variables if v not in fields_to_remove]
    
    # Vérification de la présence de Raman
    has_raman = 'Raman_Spec' in all_variables
    
    # Initialisation des listes pour les DataFrames
    all_batch_data_rows = []
    all_batch_stats_rows = []
    
    print("Génération des enregistrements et fichiers CSV...")

    # 2. Boucle principale : Agrégation des données pour le CSV
    num_of_batches = len(raw_batch_data)
    
    for i in range(1, num_of_batches + 1):
        batch_ref = f'Batch_{i:02d}'
        current_batch = raw_batch_data[batch_ref]
        
        # Récupération du temps (t)
        # On suppose que la première variable exportable a le bon vecteur temps
        # Sinon on prend 'Fg' ou une variable standard
        ref_var = variables_to_export[0]
        time_vec = current_batch[ref_var]['t']
        
        # Création d'un DataFrame temporaire pour ce batch
        df_batch = pd.DataFrame({'Time (h)': time_vec})
        
        # Ajout des variables dynamiques (Concentrations, Volumes, etc.)
        for var_name in variables_to_export:
            if var_name in current_batch:
                # Vérifier que c'est bien un dictionnaire avec les bonnes clés
                if isinstance(current_batch[var_name], dict) and 'y' in current_batch[var_name]:
                    # On récupère les données
                    data_y = current_batch[var_name]['y']
                    
                    # Création de l'en-tête "Nom (Clé:Unité)" avec gestion des clés manquantes
                    if 'name' in current_batch[var_name] and 'yUnit' in current_batch[var_name]:
                        header_name = f"{current_batch[var_name]['name']} ({var_name}:{current_batch[var_name]['yUnit']})"
                    else:
                        # Utiliser seulement le nom de variable si les métadonnées manquent
                        header_name = var_name
                    
                    # Vérification de la taille (au cas où)
                    if len(data_y) == len(time_vec):
                        df_batch[header_name] = data_y
                    else:
                        # Gestion basique si les tailles diffèrent (ex: interpolation ou skip)
                        pass

        # Gestion des fautes (Fault flag)
        if 'Fault_ref' in current_batch:
             # Si la somme des fautes > 0, on marque tout le batch ou instantané ?
             # Le code MATLAB met des 1 partout si sum > 0
             if np.sum(current_batch['Fault_ref']['y']) > 0:
                 batch_fault_col = np.ones(len(time_vec))
                 fault_stat = 1
             else:
                 batch_fault_col = np.zeros(len(time_vec))
                 fault_stat = 0
        else:
             batch_fault_col = np.zeros(len(time_vec))
             fault_stat = 0
             
        df_batch['Fault flag'] = batch_fault_col
        df_batch['Batch ID'] = i

        # Gestion Raman
        if has_raman and 'Raman_Spec' in current_batch:
            raman_intensity = current_batch['Raman_Spec']['Intensity']
            raman_wavelengths = current_batch['Raman_Spec']['Wavelength']
            
            # En MATLAB, Raman est souvent statique (1 spectre par batch à la fin) ou dynamique.
            # Le code MATLAB original fait: [DF, Raman_Intensity'] (Transpose).
            # Cela suggère que Raman est ici une ligne qui est répétée ou ajoutée bizarrement.
            # HYPOTHÈSE: Ici on va supposer que c'est un dataset temporel complexe,
            # mais pour simplifier selon le code MATLAB v2, on ne l'ajoute souvent qu'à la fin ou pas au CSV temporel.
            # Le code MATLAB semble coller les intensités comme des colonnes.
            
            # Simplification pour Python : On ajoute les colonnes Raman
            # Attention : Si Raman est 1D (1 spectre par batch), on le duplique pour chaque pas de temps ? 
            # Le code MATLAB semble faire ça : ones(size)*Intensity'
            
            # Pour éviter de créer des fichiers CSV de 4Go, je recommande de NE PAS mettre le Raman complet
            # dans le CSV temporel si c'est un spectre complet à chaque pas de temps.
            # Mais je suis la logique MATLAB :
            if len(raman_intensity.shape) == 1:
                for idx, w in enumerate(raman_wavelengths):
                    col_name = f"Raman_{w:.2f}"
                    df_batch[col_name] = raman_intensity[idx]

        # Stockage des données temporelles
        all_batch_data_rows.append(df_batch)
        
        # Gestion des Statistiques
        # MATLAB: [-Harvested, End, Yield] (Le moins devant Harvested est étrange mais copié)
        stats = current_batch['Stats']
        stat_row = {
            'Batch ref': i,
            'Penicllin_harvested_during_batch(kg)': -stats['Penicllin_harvested_during_batch']/1000,
            'Penicllin_harvested_end_of_batch (kg)': stats['Penicllin_harvested_end_of_batch']/1000,
            'Penicllin_yield_total (kg)': stats['Penicllin_yield_total']/1000,
            'Fault ref(0-NoFault 1-Fault)': fault_stat
        }
        all_batch_stats_rows.append(stat_row)

    # 3. Écriture des fichiers CSV
    
    # Concaténation de tous les batchs
    full_df = pd.concat(all_batch_data_rows, ignore_index=True)
    
    csv_filename = f"{batches_file_name}.csv"
    full_df.to_csv(csv_filename, index=False)
    print(f"Fichier CSV de données sauvegardé : {csv_filename}")
    
    # Sauvegarde des stats
    stats_df = pd.DataFrame(all_batch_stats_rows)
    stats_filename = f"{batches_file_name}_Statistics.csv"
    stats_df.to_csv(stats_filename, index=False)
    print(f"Fichier CSV de statistiques sauvegardé : {stats_filename}")

    # 4. Nettoyage et Structuration Finale (Batch_Records)
    
    batch_records = {}
    
    # Champs Offline à nettoyer (supprimer les NaNs)
    offline_fields = ['PAA_offline', 'P_offline', 'NH3_offline', 'X_offline', 'Viscosity_offline']
    
    for i in range(1, num_of_batches + 1):
        mat_file_name = f'Batch_{i:02d}'
        
        # On copie pour ne pas modifier l'original Raw_Batch_data si on en a besoin plus tard
        # (Bien que le code MATLAB modifie l'original)
        current_record = raw_batch_data[mat_file_name].copy()
        
        # Nettoyage des mesures offline (NaN removal)
        # On utilise PAA_offline comme référence pour les indices valides (comme dans MATLAB)
        if 'PAA_offline' in current_record:
            y_data = current_record['PAA_offline']['y']
            valid_indices = ~np.isnan(y_data)
            
            for field in offline_fields:
                if field in current_record:
                    # Filtrage
                    current_record[field]['y'] = current_record[field]['y'][valid_indices]
                    current_record[field]['t'] = current_record[field]['t'][valid_indices]
        
        # Conversion O2 en pourcentage
        if 'O2' in current_record:
            current_record['O2']['y'] = current_record['O2']['y'] * 100
            
        # Suppression des champs inutiles (défini au début)
        # On recrée un dictionnaire propre
        clean_record = {}
        
        # On garde tout ce qui n'est PAS dans fields_to_remove
        # Sauf Raman et Stats qu'on veut peut-être garder dans le struct final Python (le code MATLAB les supprime via le rmfield field)
        # Le code MATLAB fait: rmfield(Raw..., field). field contient Raman ? Non, field est défini au début.
        
        for key, value in current_record.items():
            if key not in fields_to_remove:
                clean_record[key] = value
        
        # On remet Raman s'il existait (le code MATLAB semble le garder dans le struct final si il n'est pas dans la liste 'field' du rmfield)
        if 'Raman_Spec' in current_record:
             clean_record['Raman_Spec'] = current_record['Raman_Spec']

        batch_records[mat_file_name] = clean_record

    # 5. Sauvegarde Finale (Pickle au lieu de .mat)
    # Le script principal le fait déjà, mais on peut le faire ici aussi si demandé
    # save_file_name = batches_file_name + '.pkl'
    # with open(save_file_name, 'wb') as f:
    #     pickle.dump(batch_records, f)
    
    return batch_records