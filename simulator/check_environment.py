"""
Script de vérification des dépendances pour IndPenSim V2
Exécutez ce script avant de lancer la simulation principale
"""

import sys

def check_dependencies():
    """Vérifie que toutes les dépendances sont installées"""
    
    dependencies = {
        'numpy': 'Calculs numériques',
        'scipy': 'Intégration ODE et filtres',
        'matplotlib': 'Génération de graphiques',
        'pandas': 'Gestion des données CSV'
    }
    
    missing = []
    installed = []
    
    print("="*60)
    print("Vérification des dépendances IndPenSim V2")
    print("="*60)
    
    for package, description in dependencies.items():
        try:
            __import__(package)
            installed.append(package)
            print(f"✓ {package:15s} - OK ({description})")
        except ImportError:
            missing.append(package)
            print(f"✗ {package:15s} - MANQUANT ({description})")
    
    print("="*60)
    
    if missing:
        print(f"\n⚠️  ATTENTION : {len(missing)} package(s) manquant(s)")
        print("\nPour installer les dépendances manquantes, exécutez :")
        print(f"\n    pip install {' '.join(missing)}\n")
        print("Ou pour tout installer d'un coup :")
        print("\n    pip install numpy scipy matplotlib pandas\n")
        return False
    else:
        print(f"\n✅ Toutes les dépendances sont installées ({len(installed)}/{len(dependencies)})")
        print("\n🚀 Vous pouvez maintenant exécuter :")
        print("    python Generate_Production_Batch_data_V4.py\n")
        return True

def check_files():
    """Vérifie que tous les fichiers nécessaires sont présents"""
    
    required_files = [
        'Generate_Production_Batch_data_V4.py',
        'indpensim_run.py',
        'indpensim.py',
        'indpensim_ode.py',
        'parameter_list.py',
        'fctrl_indpensim.py',
        'PIDSimple3.py',
        'generate_batch_records.py',
        'IndPenSim_QbD_Figure_properties.py'
    ]
    
    import os
    
    print("\n" + "="*60)
    print("Vérification des fichiers du projet")
    print("="*60)
    
    missing_files = []
    present_files = []
    
    for file in required_files:
        if os.path.exists(file):
            present_files.append(file)
            print(f"✓ {file}")
        else:
            missing_files.append(file)
            print(f"✗ {file} - MANQUANT")
    
    print("="*60)
    
    if missing_files:
        print(f"\n⚠️  ATTENTION : {len(missing_files)} fichier(s) manquant(s)")
        print("\nFichiers manquants :")
        for file in missing_files:
            print(f"  - {file}")
        return False
    else:
        print(f"\n✅ Tous les fichiers sont présents ({len(present_files)}/{len(required_files)})")
        return True

def main():
    print("\n" + "="*60)
    print("  VÉRIFICATION DE L'ENVIRONNEMENT IndPenSim V2")
    print("="*60 + "\n")
    
    deps_ok = check_dependencies()
    files_ok = check_files()
    
    print("\n" + "="*60)
    print("RÉSUMÉ")
    print("="*60)
    
    if deps_ok and files_ok:
        print("\n✅ Environnement prêt ! Vous pouvez lancer la simulation.\n")
        print("Commande pour exécuter :")
        print("    python Generate_Production_Batch_data_V4.py\n")
        return 0
    else:
        print("\n⚠️  Veuillez corriger les problèmes ci-dessus avant de continuer.\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
