# 📊 Guide des Graphiques - IndPenSim V2

## 🎨 Légende des Couleurs par Batch

Chaque batch est représenté par une couleur différente sur les graphiques :

### Batch 01 - 🔵 Bleu
**Type :** Batch NORMAL (Sans faute)
- **Contrôle :** Sequential Batch Control (SBC) - Contrôle par recette
- **Durée :** Variable (déterminée par les conditions de fermentation)
- **Raman :** Enregistrement activé
- **Fautes :** Aucune
- **Description :** Représente un batch de production standard avec conditions optimales

### Batch 02 - 🟠 Orange
**Type :** Batch AVEC FAUTE
- **Contrôle :** Contrôle par opérateur (manuel)
- **Durée :** Fixe
- **Raman :** Contrôle PAA par Raman activé
- **Fautes :** Faute de type 1 (voir ci-dessous)
- **Description :** Simule un batch avec défaillances pour tester la robustesse

---

## 📈 Variables Affichées sur les Graphiques

### Variables Principales

1. **P (Pénicilline)** - Concentration en pénicilline (g/L)
   - Variable de sortie principale
   - Objectif : Maximiser la production

2. **DO2 (Oxygène dissous)** - Saturation en oxygène (%)
   - Critique pour la croissance cellulaire
   - Maintenu autour de 40-60%

3. **pH** - Acidité/Basicité du milieu
   - Contrôlé par ajout d'acide/base
   - Consigne typique : 6.5

4. **T (Température)** - Température du bioréacteur (K)
   - Contrôlée par système de refroidissement/chauffage
   - Consigne typique : 298K (25°C)

5. **V (Volume)** - Volume total du bioréacteur (L)
   - Augmente avec l'alimentation en substrat
   - Départ : ~58,000L

6. **S (Substrat)** - Concentration en glucose/nutriments (g/L)
   - Alimenté en continu (fed-batch)
   - Maintenu à faible niveau pour éviter inhibition

### Variables de Contrôle (Débits)

- **Fg** - Débit d'aération (L/min)
- **Fs** - Débit de substrat (L/h)
- **Fa** - Débit d'acide (L/h)
- **Fb** - Débit de base (L/h)
- **Fc** - Débit de refroidissement (L/h)
- **Fh** - Débit de chauffage (L/h)

### Variables de Biomasse

- **X** - Biomasse totale (g/L)
- **a0, a1, a3, a4** - Différentes formes de biomasse (morphologie)

---

## 🔴 Types de Fautes Simulées

Les fautes peuvent être injectées dans les batches pour tester la robustesse :

| Code | Type de Faute | Description |
|------|---------------|-------------|
| 0 | Pas de faute | Fonctionnement normal |
| 1 | Aération | Réduction du débit d'air |
| 2 | Pression | Défaillance du contrôle de pression |
| 3 | Substrat | Problème d'alimentation en glucose |
| 4 | Base | Défaillance de l'ajout de base (pH) |
| 5 | Refroidissement | Problème du système de refroidissement |
| 6 | Multiple | Plusieurs fautes simultanées |
| 7 | Capteur T | Erreur de mesure température |
| 8 | Capteur pH | Erreur de mesure pH |

---

## 📊 Interprétation des Graphiques

### Comparaison Batch Normal vs Batch avec Faute

**Observez ces différences typiques :**

1. **Production de Pénicilline (P)**
   - 🔵 Normal : Courbe croissante stable, atteint ~1.5 g/L
   - 🟠 Avec faute : Production réduite ou irrégulière

2. **Oxygène Dissous (DO2)**
   - 🔵 Normal : Maintenu stable autour de la consigne
   - 🟠 Avec faute : Fluctuations importantes

3. **pH**
   - 🔵 Normal : Contrôle précis autour de 6.5
   - 🟠 Avec faute : Déviations de la consigne

4. **Température (T)**
   - 🔵 Normal : Régulation précise
   - 🟠 Avec faute : Oscillations ou dérives

### Indicateurs de Performance

Sur les graphiques, vous pouvez évaluer :

- ✅ **Qualité du contrôle** : Stabilité des variables contrôlées (pH, T, DO2)
- ✅ **Productivité** : Pente de la courbe de pénicilline
- ✅ **Efficacité** : Ratio production/consommation substrat
- ✅ **Robustesse** : Capacité à gérer les perturbations

---

## 🎯 Utilisation des Graphiques

### Pour l'Analyse

1. **Superposition** : Les courbes sont superposées pour comparaison directe
2. **Légende** : En haut à droite de chaque graphique
3. **Grille** : Aide à la lecture des valeurs
4. **Titre** : Indique la variable mesurée et ses unités

### Pour la Présentation

- Les graphiques sont au format publication
- Taille optimisée pour export
- Couleurs contrastées pour impression N&B
- Légendes complètes et explicites

### Pour l'Export

- **Format PNG** : Enregistrer via `File > Save As` dans matplotlib
- **Format PDF** : Pour publications scientifiques
- **Données CSV** : Pour retraitement dans Excel/Origin

---

## 📝 Notes Techniques

### Échelle de Temps

- **Unité** : Heures (h)
- **Durée typique** : 
  - Batch normal : 110-115h (~4.5 jours)
  - Batch variable : Jusqu'à 120h

### Fréquence d'Échantillonnage

- **Simulation** : Pas de 0.1h (6 minutes)
- **Mesures offline** : Toutes les 12h
- **Mesures online** : Continues

### Performances Attendues

| Métrique | Batch Normal | Batch avec Faute |
|----------|--------------|------------------|
| Pénicilline finale | 1.2-1.5 g/L | 0.5-1.0 g/L |
| Rendement total | 2500-3500 kg | 1000-2000 kg |
| Durée | 110h | 115h |

---

## 🔍 Personnalisation

Pour modifier les couleurs ou légendes, éditez le fichier :
- `Generate_Production_Batch_data_V4.py`
- Fonction : `plot_batches()`
- Dictionnaire : `batch_descriptions`

Exemple :
```python
batch_descriptions = {
    1: 'Votre description Batch 1',
    2: 'Votre description Batch 2',
    # Ajoutez plus de batches si nécessaire
}
```

---

## 📚 Références

Pour plus d'informations sur l'interprétation des résultats :
- Goldrick et al. (2015) - Journal of Biotechnology
- Goldrick et al. (2018) - Computers and Chemical Engineering

---

*Généré par IndPenSim V2 - Industrial Penicillin Fermentation Simulator*
