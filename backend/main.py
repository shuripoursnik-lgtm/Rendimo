"""
Backend FastAPI pour Rendimo
Proxy pour contourner le blocage 403 de l'API DVF

Déploiement : Railway (https://railway.app)
URL de test : https://api.data.gouv.fr/api/explore/v2.1/catalog/datasets/dvf/records
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import requests
from datetime import datetime, timedelta
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Rendimo DVF Proxy API",
    description="Proxy pour accéder aux données DVF depuis Railway",
    version="1.0.0"
)

# CORS pour permettre les appels depuis Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier le domaine Streamlit
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# URL de base de l'API DVF (essayer plusieurs domaines)
DVF_API_URLS = [
    "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/dvf",
    "https://api.data.gouv.fr/api/explore/v2.1/catalog/datasets/dvf",
    "https://opendata.data.gouv.fr/api/explore/v2.1/catalog/datasets/dvf"
]
DVF_API_BASE = DVF_API_URLS[0]  # Par défaut


class PriceQuery(BaseModel):
    """Modèle pour la requête de prix"""
    city: str
    postal_code: str
    property_type: str  # "apartment" ou "house"
    surface_min: Optional[float] = None
    surface_max: Optional[float] = None
    months_back: int = 24


@app.get("/")
async def root():
    """Endpoint racine avec documentation"""
    return {
        "service": "Rendimo DVF Proxy API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "/api/prices": "POST - Récupérer les prix locaux DVF",
            "/health": "GET - Vérifier l'état du service",
            "/test": "GET - Tester la connexion à l'API DVF"
        }
    }


@app.get("/health")
async def health_check():
    """Vérifier l'état du service"""
    try:
        # Test simple de connexion à l'API DVF
        response = requests.get(
            f"{DVF_API_BASE}/records",
            params={"limit": 1},
            timeout=5
        )
        api_status = "ok" if response.status_code == 200 else f"error_{response.status_code}"
    except Exception as e:
        api_status = f"unreachable: {str(e)}"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "dvf_api": api_status
    }


@app.get("/test")
async def test_dvf_api():
    """Tester la connexion à l'API DVF avec un exemple"""
    try:
        # Exemple : récupérer 5 transactions à Paris
        params = {
            "where": "code_commune='75056'",  # Paris
            "order_by": "date_mutation DESC",
            "limit": 5
        }
        
        response = requests.get(
            f"{DVF_API_BASE}/records",
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "status": "success",
                "api_accessible": True,
                "total_records": data.get("total_count", 0),
                "sample_records": len(data.get("results", [])),
                "example": data.get("results", [])[:2] if data.get("results") else []
            }
        else:
            return {
                "status": "error",
                "api_accessible": False,
                "status_code": response.status_code,
                "message": response.text
            }
    
    except Exception as e:
        logger.error(f"Erreur test DVF : {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/prices")
async def get_local_prices(query: PriceQuery) -> Dict[str, Any]:
    """
    Récupérer les prix locaux depuis l'API DVF
    
    Args:
        query: Paramètres de recherche (ville, code postal, type de bien, etc.)
    
    Returns:
        Données de prix avec statistiques (médiane, min, max, source)
    """
    try:
        logger.info(f"Requête prix pour {query.city} ({query.postal_code})")
        
        # Construire la requête DVF
        date_limit = (datetime.now() - timedelta(days=query.months_back * 30)).strftime("%Y-%m-%d")
        
        # Filtres
        filters = [
            f"code_postal='{query.postal_code}'",
            f"date_mutation>='{date_limit}'"
        ]
        
        # Type de bien
        if query.property_type == "apartment":
            filters.append("type_local='Appartement'")
        elif query.property_type == "house":
            filters.append("type_local='Maison'")
        
        # Surface si spécifiée
        if query.surface_min:
            filters.append(f"surface_reelle_bati>={query.surface_min}")
        if query.surface_max:
            filters.append(f"surface_reelle_bati<={query.surface_max}")
        
        # Requête API
        where_clause = " AND ".join(filters)
        params = {
            "where": where_clause,
            "select": "valeur_fonciere,surface_reelle_bati,date_mutation,code_commune,nom_commune",
            "order_by": "date_mutation DESC",
            "limit": 100  # Limiter pour éviter surcharge
        }
        
        response = requests.get(
            f"{DVF_API_BASE}/records",
            params=params,
            timeout=15
        )
        
        if response.status_code != 200:
            logger.error(f"Erreur API DVF: {response.status_code}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erreur API DVF: {response.text}"
            )
        
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            return {
                "success": False,
                "median_price": None,
                "avg_price": None,
                "min_price": None,
                "max_price": None,
                "sample_count": 0,
                "source": "DVF API (aucune transaction trouvée)",
                "message": f"Aucune transaction trouvée pour {query.city} sur {query.months_back} mois"
            }
        
        # Calculer statistiques
        prices_per_sqm = []
        for record in results:
            valeur = record.get("valeur_fonciere")
            surface = record.get("surface_reelle_bati")
            if valeur and surface and surface > 0:
                prices_per_sqm.append(valeur / surface)
        
        if not prices_per_sqm:
            return {
                "success": False,
                "median_price": None,
                "message": "Données insuffisantes (surfaces manquantes)"
            }
        
        prices_per_sqm.sort()
        median_price = prices_per_sqm[len(prices_per_sqm) // 2]
        avg_price = sum(prices_per_sqm) / len(prices_per_sqm)
        
        return {
            "success": True,
            "median_price": round(median_price, 2),
            "avg_price": round(avg_price, 2),
            "min_price": round(min(prices_per_sqm), 2),
            "max_price": round(max(prices_per_sqm), 2),
            "sample_count": len(prices_per_sqm),
            "source": f"DVF {query.months_back} mois ({len(prices_per_sqm)} transactions)",
            "city": query.city,
            "postal_code": query.postal_code,
            "property_type": query.property_type
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur récupération prix: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    # En local : uvicorn main:app --reload --port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
