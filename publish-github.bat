@echo off
echo ========================================
echo    RENDIMO V1 - PUBLICATION GITHUB
echo ========================================
echo.

REM Ajouter Git au PATH
set PATH=%PATH%;C:\Program Files\Git\bin

echo ✅ Repository local prêt !
echo    Commit: d961ee8
echo    Fichiers: 17
echo.

echo 🌐 ÉTAPES MANUELLES REQUISES :
echo.
echo 1. Allez sur https://github.com
echo 2. Cliquez sur "New repository"
echo 3. Nom: rendimo-v1
echo 4. Description: Application Streamlit pour l'analyse immobilière LeBonCoin
echo 5. NE PAS initialiser avec README/gitignore/licence
echo 6. Cliquez "Create repository"
echo.
echo 7. Copiez l'URL du repository (ex: https://github.com/USERNAME/rendimo-v1.git)
echo.

set /p repo_url="Collez l'URL de votre repository GitHub: "

echo.
echo 🚀 Connexion et upload vers GitHub...
echo.

git remote add origin %repo_url%
if %errorlevel% neq 0 (
    echo ⚠️  Remote origin existe déjà, on le remplace...
    git remote remove origin
    git remote add origin %repo_url%
)

git branch -M main
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo           ✅ SUCCÈS !
    echo ========================================
    echo.
    echo 🎉 Rendimo V1 est maintenant sur GitHub !
    echo 🌐 URL: %repo_url%
    echo.
    echo 📋 Le repository contient :
    echo    ✅ Interface Streamlit simplifiée
    echo    ✅ Scraper LeBonCoin moderne
    echo    ✅ Chatbot IA Groq
    echo    ✅ Documentation complète
    echo    ✅ Configuration sécurisée
    echo.
    echo 🔒 SÉCURITÉ : Votre fichier .env n'est PAS uploadé
    echo             (c'est normal et sécurisé)
    echo.
) else (
    echo.
    echo ❌ ERREUR lors de l'upload !
    echo.
    echo Vérifiez :
    echo - L'URL du repository
    echo - Vos droits d'accès GitHub
    echo - Votre connexion internet
    echo.
)

pause