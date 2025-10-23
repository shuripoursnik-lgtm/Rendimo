"""
Exemple d'intégration du backend Railway dans price_api.py

Copier ce code dans api/price_api.py pour utiliser le backend Railway
"""

import os
import logging
import requests
from typing import Dict, Optional
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

class PriceAPI:
    def __init__(self):
        """Initialiser l'API avec support Railway"""
        self.logger = logging.getLogger(__name__)
        
        # Configuration Railway
        self.railway_url = os.getenv("RAILWAY_BACKEND_URL")
        self.use_railway = bool(self.railway_url)
        
        if self.use_railway:
            self.logger.info(f"🚀 Backend Railway configuré : {self.railway_url}")
        else:
            self.logger.warning("⚠️ RAILWAY_BACKEND_URL non définie, utilisation des prix de référence")
        
        # Prix de référence (fallback si Railway indisponible)
        self.reference_prices = {
            "Paris": {"apartment": 10800, "house": 8500},
            "Lyon": {"apartment": 5100, "house": 4200},
            # ... autres villes
            "_default": {"apartment": 3200, "house": 3600}
        }
    
    def get_local_prices(
        self,
        city: str,
        postal_code: str,
        property_type: str = "apartment",
        surface_min: Optional[float] = None,
        surface_max: Optional[float] = None
    ) -> Dict[str, any]:
        """
        Obtenir les prix locaux via Railway backend ou fallback
        
        Args:
            city: Nom de la ville
            postal_code: Code postal
            property_type: "apartment" ou "house"
            surface_min: Surface minimale (optionnel)
            surface_max: Surface maximale (optionnel)
        
        Returns:
            Dict avec median_price, avg_price, min_price, max_price, sample_count, source
        """
        
        # 1. Essayer Railway backend si configuré
        if self.use_railway:
            try:
                self.logger.info(f"🔍 Requête Railway pour {city} ({postal_code})")
                
                response = requests.post(
                    f"{self.railway_url}/api/prices",
                    json={
                        "city": city,
                        "postal_code": postal_code,
                        "property_type": property_type,
                        "surface_min": surface_min,
                        "surface_max": surface_max,
                        "months_back": 24
                    },
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("success"):
                        self.logger.info(f"✅ DVF via Railway : {data['sample_count']} transactions")
                        return {
                            "median_price": data["median_price"],
                            "avg_price": data["avg_price"],
                            "min_price": data["min_price"],
                            "max_price": data["max_price"],
                            "sample_count": data["sample_count"],
                            "source": data["source"]
                        }
                    else:
                        self.logger.warning(f"⚠️ Railway OK mais pas de données : {data.get('message')}")
                
                else:
                    self.logger.error(f"❌ Railway erreur {response.status_code}")
            
            except requests.exceptions.Timeout:
                self.logger.warning("⏱️ Railway timeout (cold start ?)")
            except Exception as e:
                self.logger.warning(f"⚠️ Railway indisponible : {e}")
        
        # 2. Fallback sur prix de référence
        self.logger.info(f"📊 Utilisation prix de référence pour {city}")
        return self._get_reference_price(city, property_type)
    
    def _get_reference_price(self, city: str, property_type: str) -> Dict[str, any]:
        """Récupérer prix de référence (fallback)"""
        
        # Chercher prix exact
        if city in self.reference_prices:
            price = self.reference_prices[city].get(
                property_type,
                self.reference_prices[city].get("apartment", 3200)
            )
        else:
            # Chercher par contient (ex: "Paris 15" → "Paris")
            found = False
            for ref_city, prices in self.reference_prices.items():
                if ref_city.lower() in city.lower():
                    price = prices.get(property_type, prices.get("apartment", 3200))
                    found = True
                    break
            
            if not found:
                price = self.reference_prices["_default"].get(property_type, 3200)
        
        return {
            "median_price": price,
            "avg_price": price,
            "min_price": price * 0.8,
            "max_price": price * 1.2,
            "sample_count": 0,
            "source": "Prix de référence (DVF inaccessible)"
        }
    
    def test_railway_connection(self) -> bool:
        """Tester la connexion au backend Railway"""
        if not self.use_railway:
            return False
        
        try:
            response = requests.get(f"{self.railway_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"✅ Railway accessible : {data}")
                return data.get("dvf_api") == "ok"
            return False
        except Exception as e:
            self.logger.error(f"❌ Railway test failed : {e}")
            return False


# Exemple d'utilisation
if __name__ == "__main__":
    api = PriceAPI()
    
    # Tester Railway
    print("Test connexion Railway...")
    if api.test_railway_connection():
        print("✅ Railway + DVF fonctionnels !")
    else:
        print("⚠️ Railway indisponible, fallback actif")
    
    # Tester récupération prix
    print("\nTest prix Paris...")
    prices = api.get_local_prices(
        city="Paris",
        postal_code="75001",
        property_type="apartment"
    )
    print(f"Prix médian : {prices['median_price']}€/m²")
    print(f"Source : {prices['source']}")
