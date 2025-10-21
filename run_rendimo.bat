@echo off
echo.
echo ========================================
echo          LANCEMENT DE RENDIMO
echo      Assistant IA Immobilier
echo ========================================
echo.

REM Activation de l'environnement virtuel et lancement
cd /d "D:\02 - Agents IA\05 - Rendimo"
.venv\Scripts\python.exe -m streamlit run app.py

echo.
echo Application fermée. Appuyez sur une touche pour continuer...
pause >nul