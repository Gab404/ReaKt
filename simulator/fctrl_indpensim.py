import numpy as np
from scipy.interpolate import interp1d
from PIDSimple3 import pid_simple_3

import sys
import os

# Ajoute le dossier courant (.)
sys.path.append(os.getcwd())

# Ajoute le dossier parent (..)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), './simulator')))

# Maintenant vous pouvez importer vos modules
# import mon_module_parent

# --- IMPORT CONDITIONNEL DU CONTRÔLEUR IA ---
try:
    from ai_controller import AIController
except ImportError:
    print("[WARNING] 'ai_controller.py' non trouvé. Le mode IA sera désactivé.")
    AIController = None

def fctrl_indpensim(X, Xd, k, h, T, Ctrl_flags):
    """
    Calcule les variables manipulées (u) pour contrôler IndPenSim.
    Intègre une logique de switch entre SBC (Recette) et MPC (IA).
    """
    
    # Initialisation de la structure de sortie u
    u = {}
    
    # --- 0. INITIALISATION DE L'IA (Nouveau Bloc) ---
    # On active l'IA si Ctrl_flags['SBC'] == 2 (notre convention pour le Digital Twin)
    # On attend k > 65 pour laisser le batch s'initialiser et éviter les instabilités au démarrage
    use_ai = (Ctrl_flags.get('SBC') == 2) and (k > 65) and (AIController is not None)
    ai_actions = None
    
    if use_ai:
        try:
            # On récupère l'instance unique du contrôleur (chargement lazy)
            controller = AIController.get_instance()
            # On demande à l'IA de calculer les actions basées sur l'état actuel X
            ai_actions = controller.get_action(X, k)
        except Exception as e:
            print(f"[AI FAILED] Erreur à k={k}. Fallback sur la recette. Détail: {e}")
            use_ai = False

    # --- 1. pH CONTROLLER (PID - Toujours Actif pour Stabilité) ---
    # La régulation fine du pH reste gérée par le PID, même en mode IA, sauf si l'IA en décide autrement.
    
    pH_sensor_error = 0
    if Ctrl_flags.get('Faults') == 8:
        ramp_x = np.array([0, 200, 800, 1750])
        ramp_y = np.array([0, 0, 0.1, 0.1])
        interp_func = interp1d(ramp_x, ramp_y, kind='linear', fill_value='extrapolate')
        pH_sensor_error = float(interp_func(k))
        u['Fault_ref'] = 1
    
    pH_sp = Ctrl_flags.get('pH_sp', 6.5)
    
    # Récupération pH historique (Gestion index k)
    if k == 0:
        curr_ph_val = -np.log10(X['pH']['y'][0] + 1e-12)
        prev_ph_val = curr_ph_val
        prev2_ph_val = curr_ph_val
    elif k == 1:
        curr_ph_val = -np.log10(X['pH']['y'][1] + 1e-12)
        prev_ph_val = -np.log10(X['pH']['y'][0] + 1e-12)
        prev2_ph_val = prev_ph_val
    elif k == 2:
        curr_ph_val = -np.log10(X['pH']['y'][2] + 1e-12) # Si k=2, y[2] existe ? Vérifier logique indpensim.py
        # Dans indpensim.py, la boucle est for k in range(N). k est l'index courant à remplir ou qui vient d'être rempli ?
        # Dans step 2 (Get Control Inputs), X a été rempli à k pour les états initiaux ou précédents.
        # Supposons k est l'index courant. On lit k-1.
        curr_ph_val = -np.log10(X['pH']['y'][k-1] + 1e-12) 
        prev_ph_val = -np.log10(X['pH']['y'][k-2] + 1e-12)
        prev2_ph_val = -np.log10(X['pH']['y'][k-2] + 1e-12) # Fallback
    else:
        curr_ph_val = -np.log10(X['pH']['y'][k-1] + 1e-12)
        prev_ph_val = -np.log10(X['pH']['y'][k-2] + 1e-12)
        prev2_ph_val = -np.log10(X['pH']['y'][k-3] + 1e-12)

    ph_err = pH_sp - curr_ph_val + pH_sensor_error
    ph_err1 = pH_sp - prev_ph_val + pH_sensor_error
    
    ph = curr_ph_val; ph1 = prev_ph_val; ph2 = prev2_ph_val
    Fb = 0; Fa = 0; ph_on_off = 0
    
    # PID pH
    if ph_err >= -0.05: # pH trop bas -> Base
        ph_on_off = 1
        prev_Fb = X['Fb']['y'][k-1] if k > 0 else 0
        Fb = pid_simple_3(prev_Fb, ph_err, ph_err1, ph, ph1, ph2, 0, 225, 8e-2, 4.0e-05, 8, h)
    elif ph_err <= -0.05: # pH trop haut -> Acide
        ph_on_off = 1
        prev_Fa = X['Fa']['y'][k-1] if k > 0 else 0
        Fa = pid_simple_3(prev_Fa, ph_err, ph_err1, ph, ph1, ph2, 0, 225, 8e-2, 12.5, 0.125, h)
        if k > 0: Fb = X['Fb']['y'][k-1] * 0.5

    # --- 2. TEMPERATURE CONTROLLER (PID - Toujours Actif) ---
    
    T_sensor_error = 0
    if Ctrl_flags.get('Faults') == 7:
        ramp_x_t = np.array([0, 200, 800, 1750])
        ramp_y_t = np.array([0, 0, 0.4, 0.4])
        interp_func_t = interp1d(ramp_x_t, ramp_y_t, kind='linear', fill_value='extrapolate')
        T_sensor_error = float(interp_func_t(k))
        u['Fault_ref'] = 1

    T_sp = Ctrl_flags.get('T_sp', 298)
    
    # Historique Température
    curr_T = X['T']['y'][k-1] if k > 0 else X['T']['y'][0]
    prev_T = X['T']['y'][k-2] if k > 1 else curr_T
    prev2_T = X['T']['y'][k-3] if k > 2 else prev_T

    temp_err = T_sp - curr_T + T_sensor_error
    temp_err1 = T_sp - prev_T + T_sensor_error
    temp = curr_T; temp1 = prev_T; temp2 = prev2_T
    
    Fc = 0; Fh = 0; temp_on_off = 0
    
    # PID Temp
    if temp_err <= 0.05: # Trop chaud -> Froid
        prev_Fc = X['Fc']['y'][k-1] if k > 0 else 0
        Fc = pid_simple_3(prev_Fc, temp_err, temp_err1, temp, temp1, temp2, 0, 1.5e3, -300, 1.6, 0.005, h)
        if k > 0: Fh = X['Fh']['y'][k-1] * 0.1
    else: # Trop froid -> Chaud
        temp_on_off = 1
        prev_Fh = X['Fc']['y'][k-1] if k > 0 else 0 # Note: code original utilise Fc ici ?? gardé tel quel
        Fh = pid_simple_3(prev_Fh, temp_err, temp_err1, temp, temp1, temp2, 0, 1.5e3, 50, 0.050, 1, h)
        if k > 0: Fc = X['Fc']['y'][k-1] * 0.3

    if Fc < 1e-4: Fc = 1e-4
    if Fh < 1e-4: Fh = 1e-4

    # --- 3. SEQUENTIAL BATCH CONTROL (RECETTE vs IA vs OPERATEUR) ---
    
    # Valeurs par défaut
    Foil = 0; F_discharge = 0; pressure = 0.9; Fpaa = 0; Fw = 0; viscosity = 4
    Fg = 60; Fs = 0; RPM = 100 # RPM par défaut
    
    # >>> LOGIQUE DE DÉCISION DU CONTRÔLEUR <<<
    
    if use_ai and ai_actions:
        # --- MODE 1: INTELLIGENCE ARTIFICIELLE (MPC) ---
        # L'IA prend le dessus et écrase les variables qu'elle contrôle
        
        # Variables principales (Nutriments / Aération)
        if 'Fs' in ai_actions: Fs = ai_actions['Fs']
        if 'Fg' in ai_actions: Fg = ai_actions['Fg']
        if 'Foil' in ai_actions: Foil = ai_actions['Foil']
        if 'Fpaa' in ai_actions: Fpaa = ai_actions['Fpaa']
        if 'Fremoved' in ai_actions: F_discharge = ai_actions['Fremoved']
        
        # Variables secondaires (Optionnelles selon l'entraînement du modèle)
        if 'Fa' in ai_actions: Fa = ai_actions['Fa'] # Si l'IA gère le pH
        if 'Fb' in ai_actions: Fb = ai_actions['Fb']
        if 'Fc' in ai_actions: Fc = ai_actions['Fc'] # Si l'IA gère la Temp
        if 'Fh' in ai_actions: Fh = ai_actions['Fh']
        if 'Fw' in ai_actions: Fw = ai_actions['Fw']
        
        # On garde RPM fixe sauf si l'IA le demande
        if 'RPM' in ai_actions: RPM = ai_actions['RPM']
        
    elif Ctrl_flags.get('SBC') == 1:
        # --- MODE 2: OPERATEUR (Rejeu d'un batch existant Xd) ---
        Foil = Xd['Foil']['y'][k]
        F_discharge = Xd['F_discharge_cal']['y'][k]
        pressure = Xd['pressure']['y'][k]
        Fpaa = Xd['Fpaa']['y'][k]
        Fw = Xd['Fw']['y'][k]
        viscosity = Xd['viscosity']['y'][k]
        Fg = Xd['Fg']['y'][k]
        Fs = Xd['Fs']['y'][k]
        
    else:
        # --- MODE 3: RECETTE STANDARD (Baseline) ---
        # C'est la logique "par défaut" si SBC=0 ou si l'IA échoue
        
        # Helper for recipes
        def get_recipe_value(k, recipe_times, recipe_values):
            for i, time_limit in enumerate(recipe_times):
                if k <= time_limit: return recipe_values[i]
            return recipe_values[-1]

        # Recipe Fs (Sucre)
        Recipe_Fs = [15, 60, 80, 100, 120, 140, 160, 180, 200, 220, 240, 260, 280, 300, 320, 340, 360, 380, 400, 800, 1750]
        Recipe_Fs_sp = [8, 15, 30, 75, 150, 30, 37, 43, 47, 51, 57, 61, 65, 72, 76, 80, 84, 90, 116, 90, 80]
        Fs = get_recipe_value(k, Recipe_Fs, Recipe_Fs_sp)
        
        # PRBS Logic (Bruit pour l'entraînement)
        if Ctrl_flags.get('PRBS') == 1:
            if k > 500 and (k % 100 == 0):
                random_number = np.random.randint(1, 4)
                noise_factor = 15
                random_noise = 0 if random_number == 1 else (noise_factor if random_number == 2 else -noise_factor)
                
                if 'PRBS_noise_addition' not in X: X['PRBS_noise_addition'] = np.zeros(int(T/h)+200)
                X['PRBS_noise_addition'][k] = random_noise
            else:
                if 'PRBS_noise_addition' in X:
                    X['PRBS_noise_addition'][k] = X['PRBS_noise_addition'][k-1] if k > 0 else 0
            
            if k > 475: Fs = X['Fs']['y'][k-1]
            if k > 500 and (k % 100 == 0): Fs = X['Fs']['y'][k-1] + X['PRBS_noise_addition'][k]
        else:
            if 'PRBS_noise_addition' not in X: X['PRBS_noise_addition'] = np.zeros(int(T/h)+200)
            X['PRBS_noise_addition'][k] = 0

        # Recipes Foil, Fg, Pressure, Discharge, Fw, PAA
        Recipe_Foil = [20, 80, 280, 300, 320, 340, 360, 380, 400, 1750]; Recipe_Foil_sp = [22, 30, 35, 34, 33, 32, 31, 30, 29, 23]
        Foil = get_recipe_value(k, Recipe_Foil, Recipe_Foil_sp)

        Recipe_Fg = [40, 100, 200, 450, 1000, 1250, 1750]; Recipe_Fg_sp = [30, 42, 55, 60, 75, 65, 60]
        Fg = get_recipe_value(k, Recipe_Fg, Recipe_Fg_sp)
        
        Recipe_pres = [62.5, 125, 150, 200, 500, 750, 1000, 1750]; Recipe_pres_sp = [0.6, 0.7, 0.8, 0.9, 1.1, 1, 0.9, 0.9]
        pressure = get_recipe_value(k, Recipe_pres, Recipe_pres_sp)

        Recipe_dis = [500, 510, 650, 660, 750, 760, 850, 860, 950, 960, 1050, 1060, 1150, 1160, 1250, 1260, 1350, 1360, 1750]
        Recipe_dis_sp = [0, 4000, 0, 4000, 0, 4000, 0, 4000, 0, 4000, 0, 4000, 0, 4000, 0, 4000, 0, 4000, 0, 0]
        val_dis = get_recipe_value(k, Recipe_dis, Recipe_dis_sp)
        F_discharge = -val_dis if k <= Recipe_dis[-1] else val_dis # Logique du code original

        Recipe_w = [250, 375, 750, 800, 850, 1000, 1250, 1350, 1750]; Recipe_w_sp = [0, 500, 100, 0, 400, 150, 250, 0, 100]
        Fw = get_recipe_value(k, Recipe_w, Recipe_w_sp)
        
        Recipe_PAA = [25, 200, 1000, 1500, 1750]; Recipe_PAA_sp = [5, 0, 10, 4, 0]
        Fpaa = get_recipe_value(k, Recipe_PAA, Recipe_PAA_sp)
        
        # PRBS for PAA
        if Ctrl_flags.get('PRBS') == 1:
            if k > 500 and (k % 100 == 0):
                r_n = np.random.randint(1, 4)
                rn_val = 0 if r_n == 1 else (1 if r_n == 2 else -1)
                X['PRBS_noise_addition'][k] = rn_val # Ecrasement du PRBS précédent si même index ? Attention
            if k > 475: Fpaa = X['Fpaa']['y'][k-1]
            if k > 500 and (k % 100 == 0): Fpaa = X['Fpaa']['y'][k-1] + X['PRBS_noise_addition'][k]

    # --- 4. GESTION DES FAILED SENSORS (FAULT INJECTION) ---
    # Cette logique s'applique APRES la décision (Recette ou IA), pour simuler une panne d'actionneur ou capteur
    # qui forcerait une valeur, peu importe ce que le contrôleur a décidé.
    
    fault_active = 0
    f_code = Ctrl_flags.get('Faults', 0)
    
    if f_code in [1, 6]: # Aeration Fault
        if (100 <= k <= 120) or (500 <= k <= 550):
            Fg = 20
            fault_active = 1
            
    if f_code in [2, 6]: # Pressure Fault
        if (500 <= k <= 520) or (1000 <= k <= 1200):
            pressure = 2
            fault_active = 1

    if f_code in [3, 6]: # Substrate Fault
        if (100 <= k <= 150): Fs = 2; fault_active = 1
        if (380 <= k <= 460) or (1000 <= k <= 1070): Fs = 20; fault_active = 1

    if f_code in [4, 6]: # Base Fault
        if (400 <= k <= 420): Fb = 5; fault_active = 1
        if (700 <= k <= 800): Fb = 10; fault_active = 1
            
    if f_code in [5, 6]: # Coolant Fault
        if (350 <= k <= 450): Fc = 2; fault_active = 1
        if (1200 <= k <= 1350): Fc = 10; fault_active = 1

    # --- 5. CONSTRUCTION FINALE DU DICTIONNAIRE u ---
    
    u['Fg'] = Fg
    u['RPM'] = RPM
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
    
    # NH3 Shots (Souvent 0 sauf action manuelle)
    if 'NH3_shots' in Xd:
         u['NH3_shots'] = Xd['NH3_shots']['y'][k]
    else:
         u['NH3_shots'] = 0
         
    # Fault Reference Logic
    if 'Fault_ref' not in u:
        u['Fault_ref'] = fault_active
    elif fault_active == 1:
        u['Fault_ref'] = 1

    return u, X