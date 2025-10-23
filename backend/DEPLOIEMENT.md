# 🚀 Guide de déploiement Railway - Backend Rendimo

## Étape 1 : Créer un compte Railway

1. Aller sur **https://railway.app**
2. Cliquer sur **"Start a New Project"**
3. Se connecter avec **GitHub**

## Étape 2 : Déployer le backend

### Option A : Via l'interface web (recommandé)

1. Sur Railway, cliquer **"+ New Project"**
2. Sélectionner **"Deploy from GitHub repo"**
3. Autoriser Railway à accéder à votre repo GitHub
4. Choisir le repo **Rendimo**
5. Railway détectera automatiquement :
   - `backend/requirements.txt` → Installation Python
   - `backend/main.py` → Point d'entrée FastAPI
   - Configuration automatique du port

### Option B : Via Railway CLI

```bash
# Installer Railway CLI
npm i -g @railway/cli

# Login
railway login

# Dans le dossier backend/
cd backend
railway init
railway up
```

## Étape 3 : Configuration Railway

1. Dans le projet Railway, aller dans **Settings**
2. **Root Directory** : Définir sur `backend`
3. **Start Command** : Vérifier `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Generate Domain** : Cliquer pour obtenir une URL publique
   - Exemple : `rendimo-backend-production.up.railway.app`

## Étape 4 : Récupérer l'URL publique

1. Dans Railway, onglet **Settings** → **Networking**
2. Copier l'URL générée (ex: `https://rendimo-backend-production.up.railway.app`)
3. Tester dans un navigateur :
   - `https://VOTRE-URL.up.railway.app/` → Documentation
   - `https://VOTRE-URL.up.railway.app/health` → Status
   - `https://VOTRE-URL.up.railway.app/test` → Test DVF

## Étape 5 : Intégrer dans Streamlit

### Créer un fichier `.env` dans la racine du projet :

```env
RAILWAY_BACKEND_URL=https://rendimo-backend-production.up.railway.app
```

### Modifier `api/price_api.py` :

Ajouter au début de la classe `PriceAPI.__init__()` :

```python
import os
from dotenv import load_dotenv

load_dotenv()

self.use_railway = os.getenv("RAILWAY_BACKEND_URL")
self.railway_url = os.getenv("RAILWAY_BACKEND_URL")
```

Modifier la méthode `get_local_prices()` :

```python
def get_local_prices(self, city: str, postal_code: str, property_type: str = "apartment"):
    """Obtenir les prix locaux avec Railway backend si disponible"""
    
    # Si Railway est configuré, utiliser le backend
    if self.use_railway and self.railway_url:
        try:
            response = requests.post(
                f"{self.railway_url}/api/prices",
                json={
                    "city": city,
                    "postal_code": postal_code,
                    "property_type": property_type,
                    "months_back": 24
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return {
                        "median_price": data["median_price"],
                        "avg_price": data["avg_price"],
                        "min_price": data["min_price"],
                        "max_price": data["max_price"],
                        "sample_count": data["sample_count"],
                        "source": data["source"]
                    }
        except Exception as e:
            logger.warning(f"Railway backend indisponible: {e}")
    
    # Fallback sur prix de référence
    return self._get_reference_price(city, property_type)
```

## Étape 6 : Tester l'intégration

```bash
# Lancer Streamlit
streamlit run app.py
```

Vérifier dans les logs que les prix proviennent de **"DVF 24 mois"** au lieu de **"Prix de référence"**

## 💰 Tarification Railway

- **Hobby Plan (gratuit)** : 500h/mois (~20 jours)
- Le backend s'endort après **30min** d'inactivité
- Redémarre automatiquement à la prochaine requête (cold start ~5-10s)
- Pour une utilisation intensive : **Developer Plan** à 5$/mois

## 🔧 Maintenance

### Voir les logs
```bash
railway logs
```

### Redéployer après modification
```bash
# Commit GitHub → Railway redéploie automatiquement
git add backend/
git commit -m "update: backend improvements"
git push
```

### Variables d'environnement
Dans Railway Settings → Variables, ajouter si besoin :
- `PYTHON_VERSION=3.12`
- `LOG_LEVEL=INFO`

## 🎉 Succès !

Une fois déployé, votre app accèdera aux **vraies données DVF** sans erreur 403 ! 🚀
