# 🚀 Guide de Démarrage Rapide - IndPenSim V2

## ✅ Votre environnement est prêt !

Toutes les dépendances Python sont installées et tous les fichiers sont présents.

---

## 📋 Méthodes d'Exécution

### Méthode 1 : Double-clic (Le plus simple) 🖱️

**Windows :**
1. Double-cliquez sur `RUN_SIMULATION.bat`
2. Attendez la fin de la simulation
3. Les fichiers seront générés automatiquement

### Méthode 2 : Ligne de commande 💻

**Ouvrez PowerShell ou CMD dans ce dossier et tapez :**

```bash
python Generate_Production_Batch_data_V4.py
```

### Méthode 3 : Depuis VS Code 🔵

1. Ouvrez le fichier `Generate_Production_Batch_data_V4.py`
2. Appuyez sur `F5` ou cliquez sur "Run Python File"
3. Ou clic droit → "Run Python File in Terminal"

---

## 📊 Ce que fait la simulation

Par défaut, le script génère **2 batches** de fermentation :

1. **Batch 01** : Fonctionnement normal (pas de faute)
   - Contrôle par recette (Sequential Batch Control)
   - Durée variable
   - Avec enregistrement Raman

2. **Batch 02** : Avec faute
   - Contrôle par opérateur
   - Durée fixe
   - Avec contrôle PAA par Raman

### Durée estimée
- ⏱️ **~5-15 minutes** selon votre ordinateur
- Les graphiques s'affichent à la fin

---

## 📁 Fichiers générés

Après l'exécution, vous trouverez :

```
📄 IndPenSim_V2_export_V7.csv              ← Données temporelles complètes
📄 IndPenSim_V2_export_V7_Statistics.csv   ← Statistiques de production
📦 IndPenSim_V2_export_V7.pkl             ← Données Python (pickle)
```

### Contenu des fichiers CSV

**Données temporelles** (export_V7.csv) :
- Time (h) : Temps en heures
- DO2 : Oxygène dissous (%)
- P : Concentration en pénicilline (g/L)
- V : Volume (L)
- T : Température (K)
- pH : pH du milieu
- Fg : Débit d'air (L/min)
- RPM : Vitesse d'agitation (rpm)
- Et bien d'autres variables...

**Statistiques** (export_V7_Statistics.csv) :
- Pénicilline récoltée pendant le batch (kg)
- Pénicilline en fin de batch (kg)
- Rendement total (kg)
- Indicateur de faute (0/1)

---

## ⚙️ Configuration

### Modifier le nombre de batches

Éditez `Generate_Production_Batch_data_V4.py` ligne 51 :

```python
# Pour générer 1 seul batch normal
batch_run_flags['Batch_fault_order_reference'] = np.array([0])
batch_run_flags['Control_strategy'] = np.array([1])
batch_run_flags['Batch_length'] = np.array([1])
batch_run_flags['Raman_spec'] = np.array([0])

# Pour générer 5 batches
batch_run_flags['Batch_fault_order_reference'] = np.array([0, 0, 1, 0, 1])
# etc.
```

### Types de fautes disponibles

Dans `fctrl_indpensim.py`, plusieurs types de fautes sont simulés :
- `1` : Faute d'aération
- `2` : Faute de pression
- `3` : Faute d'alimentation en substrat
- `4` : Faute de débit de base
- `5` : Faute de débit de refroidissement
- `6` : Fautes multiples
- `7` : Erreur capteur température
- `8` : Erreur capteur pH

---

## 📈 Visualisation des résultats

Les graphiques s'affichent automatiquement à la fin :
- Profils de concentration (Substrat, Pénicilline, Biomasse)
- Température et pH
- Oxygène dissous
- Débits (air, substrat, acide/base)
- Spectres Raman (si activé)

Pour fermer les graphiques : Fermez les fenêtres matplotlib

---

## 🐛 Dépannage

### La simulation est très lente
➜ Réduisez le nombre de batches ou augmentez le pas de temps

### Erreur "ModuleNotFoundError"
➜ Réexécutez `python check_environment.py` pour identifier le problème

### Les graphiques ne s'affichent pas
➜ Vérifiez que matplotlib est bien installé : `pip install matplotlib`

### Erreur lors de la génération CSV
➜ Vérifiez que pandas est installé : `pip install pandas`

---

## 📚 Documentation complète

Pour plus de détails, consultez :
- 📖 `README_EXECUTION.md` : Documentation technique complète
- 🔍 `check_environment.py` : Vérification de l'environnement

---

## 📞 Références

**Publications scientifiques :**
- Goldrick et al. (2015) - "The Development of an Industrial Scale Fed-Batch Fermentation Simulation", *Journal of Biotechnology*
- Goldrick et al. (2018) - "Modern day control challenges for industrial-scale fermentation processes", *Computers and Chemical Engineering*

**Contact original :**
- Stephen Goldrick
- s.goldrick@ucl.ac.uk
- University College London

---

## ✨ Bon courage avec votre simulation !

Des questions ? Consultez le `README_EXECUTION.md` pour plus de détails techniques.
