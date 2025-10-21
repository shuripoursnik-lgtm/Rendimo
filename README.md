# Rendimo V1 🏠

Application Streamlit simplifiée pour l'extraction et l'analyse de données immobilières depuis LeBonCoin.

## 🎯 Fonctionnalités

- **Extraction automatique** depuis les URLs LeBonCoin
- **Saisie manuelle** de propriétés immobilières  
- **Chatbot IA** pour l'analyse des biens (Groq AI)
- **Interface épurée** avec 2 onglets seulement
- **Calculs de rentabilité** de base

## 🚀 Installation

1. **Cloner le repository**
```bash
git clone https://github.com/[USERNAME]/rendimo-v1.git
cd rendimo-v1
```

2. **Créer l'environnement virtuel**
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configurer les variables d'environnement**
```bash
cp .env.example .env
# Éditer .env avec votre clé API Groq
```

## 🏃‍♂️ Démarrage rapide

```bash
streamlit run app.py
```

L'application sera accessible sur `http://localhost:8501`

## 📁 Structure du projet

```
rendimo-v1/
├── app.py                 # Interface principale Streamlit
├── requirements.txt       # Dépendances Python
├── .env.example          # Variables d'environnement
├── utils/
│   ├── scraper.py        # Extraction LeBonCoin
│   ├── calculator.py     # Calculs immobiliers
│   └── __init__.py
└── api/
    ├── ai_assistant.py   # Chatbot IA
    └── __init__.py
```

## 🛠️ Technologies

- **Streamlit** - Interface web
- **BeautifulSoup** - Web scraping
- **Groq AI** - Chatbot intelligent
- **Pandas** - Manipulation de données
- **Requests** - Requêtes HTTP

## 📋 Utilisation

### Onglet "URL LeBonCoin"
1. Coller l'URL d'une annonce LeBonCoin
2. Cliquer sur "Analyser"
3. Consulter les données extraites

### Onglet "Saisie manuelle"
1. Remplir les champs du formulaire
2. Cliquer sur "Calculer"
3. Voir l'analyse de rentabilité

### Chatbot IA
- Poser des questions sur les biens analysés
- Obtenir des conseils d'investissement
- Analyser la rentabilité

## 🔧 Configuration

### Variables d'environnement (.env)
```env
GROQ_API_KEY=votre_cle_groq_ici
```

### Obtenir une clé Groq
1. Aller sur [Groq Console](https://console.groq.com/)
2. Créer un compte gratuit
3. Générer une clé API
4. L'ajouter dans `.env`

## 🐛 Dépannage

### Erreur 403 lors du scraping
- Normal, LeBonCoin bloque parfois les robots
- L'application effectue plusieurs tentatives automatiquement
- Utiliser la saisie manuelle en cas d'échec

### Module non trouvé
```bash
pip install -r requirements.txt
```

## 📄 Licence

MIT License - voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

⭐ Si ce projet vous aide, n'hésitez pas à lui donner une étoile !