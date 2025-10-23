@echo off
chcp 65001 >nul
echo ========================================
echo    🧹 NETTOYAGE COMPLET
echo ========================================
echo.

cd /d "%~dp0"

REM Ajouter Git au PATH
set PATH=%PATH%;C:\Program Files\Git\bin

echo 📦 Suppression des fichiers de test...
del /F /Q test_backend_ui.py 2>nul
del /F /Q test-backend-ui.bat 2>nul
del /F /Q test-backend-local.bat 2>nul
del /F /Q push-fix-render.bat 2>nul
del /F /Q BACKEND_PRET.md 2>nul

echo.
echo 📦 Suppression du dossier backend...
rmdir /S /Q backend 2>nul

echo.
echo 📝 Nettoyage .env...
REM Supprimer la ligne RAILWAY_BACKEND_URL du .env
type .env | findstr /V "RAILWAY_BACKEND_URL" > .env.tmp
move /Y .env.tmp .env >nul

echo.
echo 💾 Commit des changements...
git add -A
git commit -m "chore: remove backend and test files (DVF unavailable)"
git push origin main

echo.
echo ========================================
echo          ✅ NETTOYAGE TERMINÉ !
echo ========================================
echo.
echo Fichiers supprimés:
echo - backend/ (dossier complet)
echo - test_backend_ui.py
echo - test-backend-ui.bat
echo - test-backend-local.bat
echo - push-fix-render.bat
echo - BACKEND_PRET.md
echo.
echo L'app Rendimo fonctionne avec les prix de référence ! 🎉
echo.
pause
