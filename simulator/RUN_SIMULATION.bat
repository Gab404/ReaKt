@echo off
REM Script de lancement rapide pour IndPenSim V2
REM Double-cliquez sur ce fichier pour lancer la simulation

echo ============================================================
echo   IndPenSim V2 - Simulation de Fermentation
echo ============================================================
echo.

REM Vérification de l'environnement
echo Verification de l'environnement...
python check_environment.py

if %errorlevel% neq 0 (
    echo.
    echo ERREUR: L'environnement n'est pas configure correctement.
    echo Veuillez installer les dependances manquantes.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Demarrage de la simulation...
echo ============================================================
echo.

REM Lancement de la simulation
python Generate_Production_Batch_data_V4.py

if %errorlevel% neq 0 (
    echo.
    echo ERREUR: La simulation a rencontre une erreur.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Simulation terminee avec succes !
echo ============================================================
echo.
echo Les fichiers suivants ont ete generes :
echo   - IndPenSim_V2_export_V7.csv
echo   - IndPenSim_V2_export_V7_Statistics.csv
echo   - IndPenSim_V2_export_V7.pkl
echo.
pause
