# Guide d'Exécution - IndPenSim V2

## Comment Exécuter le Code

### Commande Simple
Pour exécuter la simulation complète, lancez :

```bash
python Generate_Production_Batch_data_V4.py
```

### Alternative avec Python Configuré
Si vous avez plusieurs versions de Python :

```bash
python3 Generate_Production_Batch_data_V4.py
```

## Dépendances Requises

Le code nécessite les packages Python suivants :

```bash
pip install numpy scipy matplotlib pandas
```

## Structure du Projet

```
Generate_Production_Batch_data_V4.py  <-- FICHIER PRINCIPAL (main)
│
├── indpensim_run.py                  <-- Initialisation des simulations
│   ├── parameter_list.py             <-- Paramètres du modèle
│   ├── fctrl_indpensim.py           <-- Logique de contrôle
│   │   └── PIDSimple3.py            <-- Contrôleur PID
│   └── indpensim.py                 <-- Moteur de simulation
│       └── indpensim_ode.py         <-- Équations différentielles
│
├── generate_batch_records.py        <-- Génération des fichiers CSV
└── IndPenSim_QbD_Figure_properties.py  <-- Propriétés graphiques
```

## Problèmes Actuels à Corriger

### ⚠️ ATTENTION - Fonctions Stubs à Remplacer

Plusieurs fichiers contiennent des **stubs** (fonctions placeholders) qui doivent être remplacés par les vrais imports :

#### 1. Dans `indpensim_run.py` (Lignes 14-26)
**À REMPLACER :**
```python
def parameter_list(x0, alpha_kla, N_conc_paa, PAA_c):
    """Stub pour Parameter_list.m"""
    return {'alpha_kla': alpha_kla, 'some_param': 1.0}

def fctrl_indpensim(t, x, par, ctrl_flags):
    """Stub pour fctrl_indpensim.m (Logique de contrôle)"""
    pass

def indpensim_core(control_func, x_interp, x0, h, T, integration_method, par, ctrl_flags):
    """Stub pour indpensim.m"""
    # ...simulation factice...
```

**PAR :**
```python
from parameter_list import parameter_list
from fctrl_indpensim import fctrl_indpensim
from indpensim import indpensim as indpensim_core
```

#### 2. Dans `fctrl_indpensim.py` (Lignes 3-36)
**À REMPLACER :**
```python
def pid_simple_3(...):
    """Implémentation basique d'un PID..."""
    # ... code approximatif ...
```

**PAR :**
```python
from PIDSimple3 import pid_simple_3
```

#### 3. Dans `indpensim.py` (Lignes 46-49)
**À REMPLACER :**
```python
def indpensim_ode_placeholder(t, y, u, p):
    """Placeholder en attendant le vrai fichier ODE"""
    return np.zeros_like(y)
```

**PAR :**
```python
from indpensim_ode import indpensim_ode
```

ET remplacer tous les appels à `indpensim_ode_placeholder` par `indpensim_ode`.

## Configuration de la Simulation

### Mode de Génération de Données
Dans `Generate_Production_Batch_data_V4.py`, ligne 29 :

- `data_generation_flag = 1` : Génère des données pour un intervalle de temps fixe
- `data_generation_flag = 2` : Génère un nombre fixe de batches (Normal + Fautes)

### Paramètres de Batch
Par défaut (mode 2) :
- 2 batches générés
- Batch 1 : Normal (pas de faute, contrôle recette)
- Batch 2 : Avec faute (faute=1, contrôle opérateur)

### Fichiers de Sortie
- `IndPenSim_V2_export_V7.csv` : Données temporelles de tous les batches
- `IndPenSim_V2_export_V7_Statistics.csv` : Statistiques de production
- `IndPenSim_V2_export_V7.pkl` : Données Python sérialisées (pickle)

## Étapes pour Faire Fonctionner le Code

### Option 1 : Exécution Rapide (Test)
Le code actuel peut s'exécuter avec les stubs, mais produira des **données factices**.

```bash
python Generate_Production_Batch_data_V4.py
```

### Option 2 : Correction Complète (Recommandé)
1. **Remplacer les imports stubs** (voir section ci-dessus)
2. **Vérifier les dépendances** :
   ```bash
   pip install numpy scipy matplotlib pandas
   ```
3. **Exécuter** :
   ```bash
   python Generate_Production_Batch_data_V4.py
   ```

## Debugging

### Si vous avez une erreur d'import :
```python
ModuleNotFoundError: No module named 'numpy'
```
➜ Installez la dépendance : `pip install numpy`

### Si vous avez une erreur de fonction manquante :
```python
AttributeError: 'dict' object has no attribute 'Stats'
```
➜ Vérifiez que les stubs ont été remplacés par les vraies fonctions

### Si la simulation prend trop de temps :
➜ Réduisez le nombre de batches dans `data_generation_flag = 2` :
```python
batch_run_flags['Batch_fault_order_reference'] = np.array([0])  # 1 seul batch
```

## Notes Supplémentaires

- **Durée de simulation** : ~5-10 minutes par batch (dépend de votre ordinateur)
- **Mémoire requise** : ~500 MB RAM
- **Plots** : Les graphiques s'affichent à la fin de la simulation
- **Format MATLAB** : Les fichiers `.m` originaux ont été convertis en `.py`

## Support

Pour toute question sur la simulation IndPenSim, référez-vous aux publications :
- Goldrick et al. (2015) - Journal of Biotechnology
- Goldrick et al. (2018) - Computers and Chemical Engineering
