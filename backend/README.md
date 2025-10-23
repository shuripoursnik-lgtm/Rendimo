# Backend Rendimo - Proxy DVF API

API FastAPI déployée sur Railway pour contourner le blocage 403 de l'API DVF.

## 🚀 Déploiement Railway

### 1. Créer un compte Railway
- Aller sur [railway.app](https://railway.app)
- Se connecter avec GitHub

### 2. Déployer depuis GitHub
```bash
# Dans le terminal Railway CLI (ou via l'interface web)
railway login
railway init
railway up
```

### 3. Configuration automatique
Railway détecte automatiquement :
- `requirements.txt` → installation Python
- `main.py` → point d'entrée FastAPI
- Port 8000 → exposition automatique

### 4. URL publique
Railway génère une URL comme : `https://rendimo-dvf-proxy.up.railway.app`

## 🧪 Tests locaux

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur
python main.py

# Tester dans un navigateur
http://localhost:8000
http://localhost:8000/test
http://localhost:8000/health
```

### Test POST avec Python
```python
import requests

url = "http://localhost:8000/api/prices"
data = {
    "city": "Paris",
    "postal_code": "75001",
    "property_type": "apartment",
    "months_back": 24
}

response = requests.post(url, json=data)
print(response.json())
```

## 📡 Endpoints

### `GET /`
Documentation de l'API

### `GET /health`
Vérifier l'état du service et connexion DVF

### `GET /test`
Tester l'API DVF avec un exemple (Paris)

### `POST /api/prices`
Récupérer les prix locaux DVF

**Body JSON :**
```json
{
  "city": "Lyon",
  "postal_code": "69001",
  "property_type": "apartment",
  "surface_min": 50,
  "surface_max": 100,
  "months_back": 24
}
```

**Réponse :**
```json
{
  "success": true,
  "median_price": 5450.0,
  "avg_price": 5623.5,
  "min_price": 4200.0,
  "max_price": 7800.0,
  "sample_count": 45,
  "source": "DVF 24 mois (45 transactions)",
  "city": "Lyon",
  "postal_code": "69001",
  "property_type": "apartment"
}
```

## 🔧 Intégration dans Streamlit

Modifier `api/price_api.py` pour appeler le backend Railway au lieu de l'API DVF directe :

```python
# Dans PriceAPI.__init__
self.backend_url = os.getenv("RAILWAY_BACKEND_URL", "https://rendimo-dvf-proxy.up.railway.app")

# Dans get_local_prices()
response = requests.post(
    f"{self.backend_url}/api/prices",
    json={
        "city": city,
        "postal_code": postal_code,
        "property_type": property_type,
        "months_back": 24
    }
)
```

## 💰 Tarification Railway

- **Gratuit** : 500h/mois (~20 jours)
- **Hobby** : 5$/mois pour usage illimité
- Idle après 30min d'inactivité → redémarre automatiquement

## 🔒 Sécurité

En production, limiter CORS :
```python
allow_origins=["https://votre-app-streamlit.com"]
```

## 📝 Logs

```bash
railway logs
```
