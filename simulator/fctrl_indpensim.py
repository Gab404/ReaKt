import numpy as np
from scipy.interpolate import interp1d
import numpy as np
from PIDSimple3 import pid_simple_3

# --- FONCTION PRINCIPALE DE CONTRÔLE ---

def fctrl_indpensim(X, Xd, k, h, T, Ctrl_flags):
    """
    Calcule les variables manipulées (u) pour contrôler IndPenSim.
    
    Args:
        X: Données du batch (Dictionnaire)
        Xd: Données industrielles / Perturbations
        k: Index de l'échantillon actuel (0-based)
        h: Période d'échantillonnage
        T: Durée totale
        Ctrl_flags: Flags de configuration
    
    Returns:
        u: Dictionnaire des variables manipulées
        X: Données mises à jour (pour PRBS noise history)
    """
    
    # Initialisation de la structure de sortie u
    u = {}
    
    # --- 1. pH CONTROLLER ---
    
    # Fault injection (pH sensor)
    pH_sensor_error = 0
    if Ctrl_flags['Faults'] == 8:
        # Ramp function interpolation
        ramp_x = np.array([0, 200, 800, 1750])
        ramp_y = np.array([0, 0, 0.1, 0.1])
        
        # Création de la fonction d'interpolation
        # fill_value='extrapolate' permet de gérer les cas hors bornes
        interp_func = interp1d(ramp_x, ramp_y, kind='linear', fill_value='extrapolate')
        
        # k correspond à l'index temporel, supposons que t = k * h ou k est l'unité arbitraire du code MATLAB (qui semble utiliser k comme 'temps' interpolé sur 1:1750 ?)
        # Le code MATLAB interpol sur 1:1:1750. Si k dépasse, il extrapole.
        pH_sensor_error = float(interp_func(k))
        u['Fault_ref'] = 1
    
    pH_sp = Ctrl_flags['pH_sp']
    
    # Récupération des valeurs historiques de pH
    # Conversion H+ vers pH (-log10)
    # Gestion des indices (k=0 en Python <=> k=1 en MATLAB)
    
    if k == 0 or k == 1:
        curr_ph_val = -np.log10(X['pH']['y'][0])
        prev_ph_val = curr_ph_val
        prev2_ph_val = curr_ph_val
    elif k == 2:
        curr_ph_val = -np.log10(X['pH']['y'][1]) # k-1
        prev_ph_val = -np.log10(X['pH']['y'][0]) # k-2
        prev2_ph_val = prev_ph_val
    else:
        curr_ph_val = -np.log10(X['pH']['y'][k-1])
        prev_ph_val = -np.log10(X['pH']['y'][k-2])
        prev2_ph_val = -np.log10(X['pH']['y'][k-3])

    # Calcul des erreurs
    ph_err = pH_sp - curr_ph_val + pH_sensor_error
    ph_err1 = pH_sp - prev_ph_val + pH_sensor_error
    
    # Historique pour le PID (pv, pv1, pv2)
    ph = curr_ph_val
    ph1 = prev_ph_val
    ph2 = prev2_ph_val

    # Logique de contrôle pH
    Fb = 0
    Fa = 0
    ph_on_off = 0
    
    if ph_err >= -0.05:
        # pH trop bas, ajout de base (Fb)
        ph_on_off = 1
        prev_Fb = X['Fb']['y'][0] if k == 0 else X['Fb']['y'][k-1]
        
        # APPEL PID
        Fb = pid_simple_3(prev_Fb, ph_err, ph_err1, ph, ph1, ph2, 0, 225, 8e-2, 4.0e-05, 8, h)
        Fa = 0
        
    elif ph_err <= -0.05:
        # pH trop haut, ajout d'acide (Fa)
        ph_on_off = 1
        prev_Fa = X['Fa']['y'][0] if k == 0 else X['Fa']['y'][k-1]
        
        # APPEL PID
        Fa = pid_simple_3(prev_Fa, ph_err, ph_err1, ph, ph1, ph2, 0, 225, 8e-2, 12.5, 0.125, h)
        
        prev_Fb = X['Fb']['y'][0] if k == 0 else X['Fb']['y'][k-1]
        Fb = prev_Fb * 0.5 # Réduction progressive de la base
        
    else:
        # Zone morte
        ph_on_off = 0
        Fb = 0
        Fa = 0

    # --- 2. TEMPERATURE CONTROLLER ---
    
    T_sensor_error = 0
    if Ctrl_flags['Faults'] == 7:
        ramp_x_t = np.array([0, 200, 800, 1750])
        ramp_y_t = np.array([0, 0, 0.4, 0.4])
        interp_func_t = interp1d(ramp_x_t, ramp_y_t, kind='linear', fill_value='extrapolate')
        T_sensor_error = float(interp_func_t(k))
        u['Fault_ref'] = 1

    T_sp = Ctrl_flags['T_sp']
    
    # Historique Température
    if k == 0 or k == 1:
        curr_T = X['T']['y'][0]
        prev_T = curr_T
        prev2_T = curr_T
    elif k == 2:
        curr_T = X['T']['y'][1]
        prev_T = X['T']['y'][0]
        prev2_T = prev_T
    else:
        curr_T = X['T']['y'][k-1]
        prev_T = X['T']['y'][k-2]
        prev2_T = X['T']['y'][k-3]

    temp_err = T_sp - curr_T + T_sensor_error
    temp_err1 = T_sp - prev_T + T_sensor_error
    
    temp = curr_T
    temp1 = prev_T
    temp2 = prev2_T
    
    Fc = 0
    Fh = 0
    temp_on_off = 0
    
    if temp_err <= 0.05:
        # Trop chaud -> Refroidissement (Fc)
        temp_on_off = 0
        prev_Fc = X['Fc']['y'][0] if k == 0 else X['Fc']['y'][k-1]
        
        Fc = pid_simple_3(prev_Fc, temp_err, temp_err1, temp, temp1, temp2, 0, 1.5e3, -300, 1.6, 0.005, h)
        
        if k > 0:
            Fh = X['Fh']['y'][k-1] * 0.1
        else:
            Fh = 0
            
    else:
        # Trop froid -> Chauffage (Fh)
        temp_on_off = 1
        # Note: Le code MATLAB utilise X.Fc.y pour initialiser Fh ?? (Copier/Coller probable dans l'original)
        # Je garde la logique MATLAB : PIDSimple3(X.Fc.y...)
        prev_ref = X['Fc']['y'][0] if k == 0 else X['Fc']['y'][k-1]
        
        Fh = pid_simple_3(prev_ref, temp_err, temp_err1, temp, temp1, temp2, 0, 1.5e3, 50, 0.050, 1, h)
        
        Fc = 0
        if k > 0:
            Fc = X['Fc']['y'][k-1] * 0.3

    # Numerical stability
    if Fc < 1e-4: Fc = 1e-4
    if Fh < 1e-4: Fh = 1e-4

    # --- 3. SEQUENTIAL BATCH CONTROL (SBC) ---
    
    # Init variables
    Foil = 0
    F_discharge = 0
    pressure = 0
    Fpaa = 0
    Fw = 0
    viscosity = 4 # Default
    Fg = 0
    Fs = 0
    
    if Ctrl_flags['SBC'] == 1:
        # Operator Controlled (Read from Xd)
        Foil = Xd['Foil']['y'][k]
        F_discharge = Xd['F_discharge_cal']['y'][k]
        pressure = Xd['pressure']['y'][k]
        Fpaa = Xd['Fpaa']['y'][k]
        Fw = Xd['Fw']['y'][k]
        viscosity = Xd['viscosity']['y'][k]
        Fg = Xd['Fg']['y'][k]
        Fs = Xd['Fs']['y'][k]
        
    elif Ctrl_flags['SBC'] == 0:
        # Recipe Driven
        viscosity = 4
        
        # Helper for recipes
        def get_recipe_value(k, recipe_times, recipe_values):
            for i, time_limit in enumerate(recipe_times):
                if k <= time_limit:
                    return recipe_values[i]
            return recipe_values[-1]

        # SBC - Fs (Substrate)
        Recipe_Fs = [15, 60, 80, 100, 120, 140, 160, 180, 200, 220, 240, 260, 280, 300, 320, 340, 360, 380, 400, 800, 1750]
        Recipe_Fs_sp = [8, 15, 30, 75, 150, 30, 37, 43, 47, 51, 57, 61, 65, 72, 76, 80, 84, 90, 116, 90, 80]
        Fs = get_recipe_value(k, Recipe_Fs, Recipe_Fs_sp)
        
        # PRBS Logic for Fs
        if Ctrl_flags['PRBS'] == 1:
            if k > 500 and (k % 100 == 0):
                # np.random.randint(low, high) -> [low, high[
                random_number = np.random.randint(1, 4) # 1, 2, or 3
                noise_factor = 15
                if random_number == 1:
                    random_noise = 0
                elif random_number == 2:
                    random_noise = noise_factor
                else:
                    random_noise = -noise_factor
                
                # Stockage du bruit dans X (Il faut s'assurer que la clé existe)
                if 'PRBS_noise_addition' not in X:
                    # Initialisation si besoin (selon taille du vecteur t)
                    # Mais X est souvent pré-initialisé. On suppose qu'on peut écrire à l'index k.
                    pass # On suppose que create_batch a fait le job ou que c'est une liste dynamique
                
                # Attention : X['PRBS_noise_addition'] est un array numpy pré-alloué ?
                # Dans indpensim.py, create_batch ne crée pas PRBS_noise_addition explicitement.
                # On va l'ajouter dynamiquement si nécessaire ou écrire dedans si existe
                if 'PRBS_noise_addition' not in X:
                     X['PRBS_noise_addition'] = np.zeros(int(T/h)+100) # Buffer
                
                X['PRBS_noise_addition'][k] = random_noise
            else:
                if 'PRBS_noise_addition' in X:
                    X['PRBS_noise_addition'][k] = X['PRBS_noise_addition'][k-1] if k > 0 else 0
            
            if k > 475:
                 Fs = X['Fs']['y'][k-1]
            
            if k > 500 and (k % 100 == 0):
                Fs = X['Fs']['y'][k-1] + X['PRBS_noise_addition'][k] # .end en Matlab -> k ici
                
        else:
             if 'PRBS_noise_addition' not in X:
                 X['PRBS_noise_addition'] = np.zeros(int(T/h)+100)
             X['PRBS_noise_addition'][k] = 0

        # SBC - Foil
        Recipe_Foil = [20, 80, 280, 300, 320, 340, 360, 380, 400, 1750]
        Recipe_Foil_sp = [22, 30, 35, 34, 33, 32, 31, 30, 29, 23]
        Foil = get_recipe_value(k, Recipe_Foil, Recipe_Foil_sp)

        # SBC - Fg (Aeration)
        Recipe_Fg = [40, 100, 200, 450, 1000, 1250, 1750]
        Recipe_Fg_sp = [30, 42, 55, 60, 75, 65, 60]
        Fg = get_recipe_value(k, Recipe_Fg, Recipe_Fg_sp)
        
        # SBC - Pressure
        Recipe_pres = [62.5, 125, 150, 200, 500, 750, 1000, 1750]
        Recipe_pres_sp = [0.6, 0.7, 0.8, 0.9, 1.1, 1, 0.9, 0.9]
        pressure = get_recipe_value(k, Recipe_pres, Recipe_pres_sp)

        # SBC - Discharge
        Recipe_discharge = [500, 510, 650, 660, 750, 760, 850, 860, 950, 960, 1050, 1060, 1150, 1160, 1250, 1260, 1350, 1360, 1750]
        Recipe_discharge_sp = [0, 4000, 0, 4000, 0, 4000, 0, 4000, 0, 4000, 0, 4000, 0, 4000, 0, 4000, 0, 4000, 0, 0]
        # Note: MATLAB: F_discharge = -Recipe_sp (negative?) ou Recipe_sp(end) positive
        # Le code MATLAB ligne 240: F_discharge = -Recipe_discharge_sp(SQ);
        val_discharge = get_recipe_value(k, Recipe_discharge, Recipe_discharge_sp)
        F_discharge = -val_discharge if k <= Recipe_discharge[-1] else val_discharge # Logique floue dans l'original, je suis la ligne 240

        # SBC - Fw (Water)
        Recipe_water = [250, 375, 750, 800, 850, 1000, 1250, 1350, 1750]
        Recipe_water_sp = [0, 500, 100, 0, 400, 150, 250, 0, 100]
        Fw = get_recipe_value(k, Recipe_water, Recipe_water_sp)
        
        # SBC - F_PAA
        Recipe_PAA = [25, 200, 1000, 1500, 1750]
        Recipe_PAA_sp = [5, 0, 10, 4, 0]
        Fpaa = get_recipe_value(k, Recipe_PAA, Recipe_PAA_sp)
        
        # PRBS for PAA
        if Ctrl_flags['PRBS'] == 1:
            if k > 500 and (k % 100 == 0):
                random_number = np.random.randint(1, 4)
                noise_factor = 1
                if random_number == 1: random_noise = 0
                elif random_number == 2: random_noise = noise_factor
                else: random_noise = -noise_factor
                X['PRBS_noise_addition'][k] = random_noise
                
            if k > 475:
                Fpaa = X['Fpaa']['y'][k-1]
                
            if k > 500 and (k % 100 == 0):
                Fpaa = X['Fpaa']['y'][k-1] + X['PRBS_noise_addition'][k]
        
        # NH3 Shots
        u['NH3_shots'] = 0 # Default if not operator

    # --- 4. PROCESS FAULTS ---
    
    fault_active = 0
    f_code = Ctrl_flags['Faults']
    
    # 1 - Aeration Fault
    if f_code == 1 or f_code == 6:
        if (100 <= k <= 120) or (500 <= k <= 550):
            Fg = 20
            fault_active = 1
            
    # 2 - Pressure Fault
    if f_code == 2 or f_code == 6:
        if (500 <= k <= 520) or (1000 <= k <= 1200):
            pressure = 2
            fault_active = 1

    # 3 - Substrate Feed Fault
    if f_code == 3 or f_code == 6:
        if (100 <= k <= 150):
            Fs = 2
            fault_active = 1
        if (380 <= k <= 460) or (1000 <= k <= 1070):
            Fs = 20
            fault_active = 1

    # 4 - Base Flowrate Fault
    if f_code == 4 or f_code == 6:
        if (400 <= k <= 420):
            Fb = 5
            fault_active = 1
        if (700 <= k <= 800):
            Fb = 10
            fault_active = 1
            
    # 5 - Coolant Flowrate Fault
    if f_code == 5 or f_code == 6:
        if (350 <= k <= 450):
            Fc = 2
            fault_active = 1
        if (1200 <= k <= 1350):
            Fc = 10
            fault_active = 1
            
    # --- 5. RAMAN CONTROL (PAA) ---
    
    if Ctrl_flags['Raman_spec'] == 2:
        PAA_sp = 1200
        
        if k == 0 or k == 1:
            PAA_err = PAA_sp - X['PAA']['y'][0]
            PAA_err1 = PAA_err
        else:
            PAA_err = PAA_sp - X['PAA']['y'][k-1]
            PAA_err1 = PAA_sp - X['PAA']['y'][k-2]
            
        time_elapsed = k * h
        if time_elapsed >= 10: # > 10 hours logic (approximated from k*h < 10 else)
            # Use prediction history
            # Note: X.PAA_pred must exist in X. Add check?
            if 'PAA_pred' in X:
                if k == 0 or k == 1:
                    pred_temp = X['PAA_pred']['y'][0]
                    pred_temp1 = pred_temp
                    pred_temp2 = pred_temp
                elif k == 2:
                    pred_temp = X['PAA_pred']['y'][1]
                    pred_temp1 = X['PAA_pred']['y'][0]
                    pred_temp2 = pred_temp1
                else:
                    pred_temp = X['PAA_pred']['y'][k-2] # Code matlab k-2
                    pred_temp1 = X['PAA_pred']['y'][k-3]
                    pred_temp2 = X['PAA_pred']['y'][k-4]
                
                prev_Fpaa = X['Fpaa']['y'][0] if k == 0 else X['Fpaa']['y'][k-1]
                Fpaa = pid_simple_3(prev_Fpaa, PAA_err, PAA_err1, pred_temp, pred_temp1, pred_temp2, 0, 150, 0.1, 0.50, 0, h)

    # --- 6. OUTPUT CONSTRUCTION ---
    
    u['Fg'] = Fg
    u['RPM'] = 100
    u['Fs'] = Fs
    u['Fa'] = Fa
    u['Fb'] = Fb
    u['Fc'] = Fc
    u['Fh'] = Fh
    u['d1'] = ph_on_off
    u['tfl'] = temp_on_off
    u['Fw'] = Fw
    u['pressure'] = pressure
    u['viscosity'] = viscosity
    u['Fremoved'] = F_discharge
    u['Fpaa'] = Fpaa
    u['Foil'] = Foil
    
    if 'NH3_shots' in Xd:
         u['NH3_shots'] = Xd['NH3_shots']['y'][k]
    else:
         u['NH3_shots'] = 0
         
    # Fault reference logic
    if 'Fault_ref' not in u:
        u['Fault_ref'] = fault_active
    else:
        # Si déjà set par les capteurs pH/Temp
        if fault_active == 1:
            u['Fault_ref'] = 1

    return u, X