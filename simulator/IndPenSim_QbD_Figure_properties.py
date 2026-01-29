import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np

def get_figure_properties(num_of_batches):
    """
    Retourne un dictionnaire contenant les propriétés graphiques 
    pour reproduire le style du papier IndPenSim QbD.
    """
    props = {}
    
    props['IndPenSim_QbD_paper'] = 1
    
    if props['IndPenSim_QbD_paper'] == 1:
        props['axis_pos'] = 0.95
        props['Font_size_fig1'] = 14
        props['Font_size_fig2'] = 10
        
        # Gestion des couleurs (cmap)
        # MATLAB 'lines' est une colormap discrète. 
        # En Matplotlib, 'tab10' ou 'tab20' sont les équivalents les plus proches.
        if num_of_batches <= 10:
            colormap = plt.get_cmap('tab10')
        elif num_of_batches <= 20:
            colormap = plt.get_cmap('tab20')
        else:
            colormap = plt.get_cmap('viridis')
            
        # On génère une liste de couleurs accessible par index
        props['cmap'] = lambda i: colormap(i % colormap.N)
        
        props['Color_reference'] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        
        # Styles de lignes et marqueurs
        props['plotStyle'] = ['-.', ':', '-', '--', '-', '-.']
        props['plot_LS'] = props['plotStyle'][0]
        
        # 'none' en MATLAB -> 'None' ou None en Python
        props['MarkerStyle'] = ['None', 'None', 'None', 'None', '>', 'o']
        
        props['Temp_Marker_size'] = 6
        props['Line_width_fig'] = 2
        props['legend_font_size'] = 6
        props['Marker_spread'] = 40
        
        # Configuration globale de Matplotlib (équivalent de set(0, ...))
        # 'normal' en MATLAB signifie une fenêtre flottante standard.
        plt.rcParams['figure.figsize'] = (10, 6) # Taille par défaut raisonnable
        plt.rcParams['font.size'] = props['Font_size_fig1']
        plt.rcParams['lines.linewidth'] = props['Line_width_fig']
        
        # Propriétés MVDA (Multivariate Data Analysis)
        props['MVDA_legend_font'] = 28
        props['MVDA_Font_size_fig'] = 28
        props['MVDA_line_width_border'] = 3
        props['MVDA_line_width_fig'] = 3
        props['MVDA_export_paper'] = 0
        props['MVDA_line_width_gscatter'] = 2
        props['MVDA_Font_size_fig_gscatter'] = 12

    return props