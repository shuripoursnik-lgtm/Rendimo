# 📋 Guide de Configuration GitHub

## 🔧 Installation de Git (requis)

1. **Télécharger Git :**
   - Aller sur https://git-scm.com/download/win
   - Télécharger Git pour Windows
   - Installer avec les options par défaut

2. **Redémarrer PowerShell** après installation

## 🚀 Création du Repository GitHub

### Étape 1: Initialiser Git
```bash
git init
git add .
git commit -m "🏠 Premier commit - Rendimo Assistant IA Immobilier"
```

### Étape 2: Créer le repo sur GitHub
1. Aller sur https://github.com
2. Cliquer sur "New repository"
3. Nom: `rendimo-assistant-ia`
4. Description: `🏠 Assistant IA conversationnel pour l'investissement immobilier français`
5. Cocher "Public" ou "Private" selon préférence
6. Ne pas initialiser avec README (on a déjà le nôtre)

### Étape 3: Lier et pousser
```bash
git remote add origin https://github.com/VOTRE_USERNAME/rendimo-assistant-ia.git
git branch -M main
git push -u origin main
```

## 📁 Structure du Repository
```
rendimo-assistant-ia/
├── app.py                    # 🏠 Interface Streamlit principale
├── run_rendimo.bat          # 🚀 Script de lancement
├── requirements.txt         # 📦 Dépendances Python
├── README_SIMPLE.md         # 📖 Documentation
├── api/                     # 🤖 IA et APIs
├── utils/                   # 🔧 Outils de calcul
├── excel_model/             # 📊 Export Excel
└── .gitignore              # 🚫 Fichiers ignorés
```

## 🔑 Variables d'Environnement

Le fichier `.env` contient votre clé Groq et est ignoré par Git pour la sécurité.
Les utilisateurs devront créer leur propre `.env` avec:
```
GROQ_API_KEY=leur_clé_ici
```

## 🎯 Commandes Git Utiles

```bash
# Voir l'état des fichiers
git status

# Ajouter des modifications
git add .
git commit -m "📝 Description des changements"

# Pousser vers GitHub
git push

# Voir l'historique
git log --oneline
```