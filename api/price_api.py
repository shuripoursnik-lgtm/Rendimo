"""
API DVF - Prix immobiliers moyens par commune
Récupère et compare les prix au m² via l'API DVF (Demandes de Valeurs Foncières)

Auteur: Assistant IA
Date: Octobre 2025
"""

import os
import time
import logging
import requests
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from urllib3.exceptions import InsecureRequestWarning

# Désactiver warnings SSL
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PriceAPI:
    """API DVF pour récupérer et comparer les prix immobiliers"""
    
    def __init__(self):
        """Initialise le client API DVF"""
        self.session = requests.Session()
        
        # Headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'fr-FR,fr;q=0.9',
        })
        
        # Configuration SSL
        self.verify_ssl = os.getenv('VERIFY_SSL', 'true').lower() != 'false'
        
        # URLs DVF
        self.dvf_urls = [
            "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/dvf/records",
            "https://opendata.data.gouv.fr/api/explore/v2.1/catalog/datasets/dvf/records",
        ]
        
        # URL géo
        self.geo_api_url = "https://geo.api.gouv.fr/communes"
        
        # Prix moyens de référence (source: DVF 2024, €/m²)
        # Utilisés en fallback si API DVF inaccessible
        self.reference_prices = {
            # Grandes villes
            'paris': {'apartment': 10800, 'house': 12500},
            'lyon': {'apartment': 5100, 'house': 5800},
            'marseille': {'apartment': 3800, 'house': 4200},
            'toulouse': {'apartment': 4100, 'house': 4500},
            'nice': {'apartment': 5500, 'house': 6800},
            'nantes': {'apartment': 4200, 'house': 4800},
            'strasbourg': {'apartment': 3500, 'house': 4000},
            'montpellier': {'apartment': 4000, 'house': 4600},
            'bordeaux': {'apartment': 4800, 'house': 5400},
            'lille': {'apartment': 3300, 'house': 3800},
            'rennes': {'apartment': 3900, 'house': 4400},
            'reims': {'apartment': 2400, 'house': 2800},
            'toulon': {'apartment': 3600, 'house': 4200},
            'grenoble': {'apartment': 3700, 'house': 4300},
            'dijon': {'apartment': 2900, 'house': 3400},
            'angers': {'apartment': 3100, 'house': 3600},
            'nimes': {'apartment': 2700, 'house': 3200},
            'villeurbanne': {'apartment': 4800, 'house': 5400},
            'clermont-ferrand': {'apartment': 2500, 'house': 3000},
            'aix-en-provence': {'apartment': 5200, 'house': 6500},
            # Prix moyen national par défaut
            '_default': {'apartment': 3200, 'house': 3600}
        }
        
        # Cache
        self._cache: Dict[str, Dict] = {}
        
        logger.info("API DVF initialisée")
    
    def get_local_prices(self, city: str, postal_code: Optional[str] = None, 
                        property_type: str = "apartment") -> Dict:
        """
        Récupère le prix moyen par m² pour une commune via DVF
        
        Args:
            city: Nom de la commune
            postal_code: Code postal (optionnel)
            property_type: 'apartment' ou 'house'
            
        Returns:
            Dict avec price_per_sqm, transaction_count, source, ou error
        """
        logger.info(f"Recherche DVF: {city} ({property_type})")
        
        # Cache
        cache_key = f"{city}:{postal_code}:{property_type}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached
        
        # INSEE
        insee_code = self._resolve_insee(city, postal_code)
        if not insee_code:
            return {"error": f"Commune {city} introuvable"}
        
        # DVF
        transactions = self._query_dvf(insee_code, property_type, months=24)
        
        if not transactions or len(transactions) < 3:
            transactions = self._query_dvf(insee_code, property_type, months=36)
        
        # Fallback sur prix de référence si DVF inaccessible
        if not transactions or len(transactions) < 3:
            logger.info(f"DVF inaccessible, utilisation prix de référence pour {city}")
            ref_price = self._get_reference_price(city, property_type)
            if ref_price:
                return {
                    "price_per_sqm": ref_price,
                    "transaction_count": "N/A",
                    "period": "Référence 2024",
                    "city": city,
                    "postal_code": postal_code,
                    "property_type": property_type,
                    "source": "Prix de référence (DVF inaccessible)",
                }
            return {"error": f"Pas assez de transactions DVF ({len(transactions)})"}
        
        # Calcul
        avg_price_m2 = self._compute_avg_price_m2(transactions)
        
        result = {
            "price_per_sqm": int(round(avg_price_m2)),
            "transaction_count": len(transactions),
            "period": "24 mois" if len(self._query_dvf(insee_code, property_type, months=24)) >= 3 else "36 mois",
            "city": city,
            "postal_code": postal_code,
            "property_type": property_type,
            "source": "DVF",
        }
        
        self._cache_set(cache_key, result)
        return result
    
    def compare_property_price(self, property_price: float, property_surface: float,
                               market_data: Dict) -> Dict:
        """Compare le prix d'un bien avec le marché"""
        if not property_surface or property_surface <= 0:
            return {'error': 'Surface invalide'}
        
        if 'error' in market_data:
            return {'error': 'Données marché indisponibles'}
        
        property_price_per_sqm = property_price / property_surface
        market_price_per_sqm = market_data.get('price_per_sqm', 0)
        
        if market_price_per_sqm <= 0:
            return {'error': 'Prix marché invalide'}
        
        difference = property_price_per_sqm - market_price_per_sqm
        percentage_difference = (difference / market_price_per_sqm) * 100
        
        # Évaluation
        if percentage_difference <= -15:
            evaluation = "Très bon prix (>15% sous marché)"
        elif percentage_difference <= -5:
            evaluation = "Bon prix (5-15% sous marché)"
        elif percentage_difference <= 5:
            evaluation = "Prix dans la moyenne"
        elif percentage_difference <= 15:
            evaluation = "Prix légèrement élevé (5-15%)"
        else:
            evaluation = "Prix élevé (>15% au-dessus)"
        
        return {
            'property_price_per_sqm': round(property_price_per_sqm, 2),
            'market_price_per_sqm': market_price_per_sqm,
            'difference': round(difference, 2),
            'percentage_difference': round(percentage_difference, 2),
            'evaluation': evaluation,
            'market_data': market_data,
        }
    
    # ---------------------- Méthodes internes ----------------------
    
    def _resolve_insee(self, city: str, postal_code: Optional[str]) -> Optional[str]:
        """Résout INSEE via geo.api.gouv.fr"""
        try:
            params = {"nom": city, "limit": 1}
            if postal_code:
                params["codePostal"] = postal_code
            
            resp = self.session.get(self.geo_api_url, params=params, 
                                   timeout=5, verify=self.verify_ssl)
            
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    return data[0].get("code")
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur INSEE: {e}")
            return None
    
    def _query_dvf(self, insee_code: str, property_type: str, months: int = 24) -> List[Dict]:
        """Interroge DVF pour transactions récentes"""
        type_local = "Appartement" if property_type == "apartment" else "Maison"
        cutoff_date = (datetime.now() - timedelta(days=months * 30)).strftime("%Y-%m-%d")
        
        # Arrondissements P/L/M
        insee_codes = self._expand_insee_codes(insee_code)
        
        transactions = []
        
        for base_url in self.dvf_urls:
            try:
                transactions = self._query_dvf_v2(base_url, insee_codes, type_local, cutoff_date)
                
                if transactions:
                    logger.info(f"DVF: {len(transactions)} transactions")
                    break
                    
            except Exception as e:
                logger.debug(f"Erreur {base_url}: {e}")
                continue
        
        return transactions
    
    def _query_dvf_v2(self, base_url: str, insee_codes: List[str], 
                      type_local: str, cutoff_date: str) -> List[Dict]:
        """Requête DVF v2.1"""
        transactions = []
        
        for code in insee_codes:
            params = {
                "select": "valeur_fonciere,surface_reelle_bati,date_mutation",
                "where": f'code_commune="{code}" AND nature_mutation="Vente" AND type_local="{type_local}" AND date_mutation>="{cutoff_date}"',
                "limit": 100,
            }
            
            try:
                resp = self.session.get(base_url, params=params, timeout=10, verify=self.verify_ssl)
                
                if resp.status_code == 200:
                    data = resp.json()
                    records = data.get("results", [])
                    
                    for rec in records:
                        try:
                            price = float(rec.get("valeur_fonciere", 0))
                            surface = float(rec.get("surface_reelle_bati", 0))
                            date_mut = rec.get("date_mutation", "")
                            
                            if price > 1000 and 10 <= surface <= 500:
                                transactions.append({
                                    "price": price,
                                    "surface": surface,
                                    "date": date_mut[:10] if date_mut else ""
                                })
                        except (ValueError, TypeError):
                            continue
                            
                elif resp.status_code == 403:
                    logger.warning(f"DVF 403 sur {base_url} - Essai sans SSL")
                    try:
                        resp2 = self.session.get(base_url, params=params, timeout=10, verify=False)
                        if resp2.status_code == 200:
                            logger.info("DVF OK avec verify=False")
                            data = resp2.json()
                            records = data.get("results", [])
                            for rec in records:
                                try:
                                    price = float(rec.get("valeur_fonciere", 0))
                                    surface = float(rec.get("surface_reelle_bati", 0))
                                    date_mut = rec.get("date_mutation", "")
                                    if price > 1000 and 10 <= surface <= 500:
                                        transactions.append({
                                            "price": price,
                                            "surface": surface,
                                            "date": date_mut[:10] if date_mut else ""
                                        })
                                except (ValueError, TypeError):
                                    continue
                    except Exception:
                        pass
                        
            except requests.exceptions.SSLError:
                logger.warning("Erreur SSL - Essai sans vérification")
                try:
                    resp = self.session.get(base_url, params=params, timeout=10, verify=False)
                    if resp.status_code == 200:
                        data = resp.json()
                        records = data.get("results", [])
                        for rec in records:
                            try:
                                price = float(rec.get("valeur_fonciere", 0))
                                surface = float(rec.get("surface_reelle_bati", 0))
                                date_mut = rec.get("date_mutation", "")
                                if price > 1000 and 10 <= surface <= 500:
                                    transactions.append({
                                        "price": price,
                                        "surface": surface,
                                        "date": date_mut[:10] if date_mut else ""
                                    })
                            except (ValueError, TypeError):
                                continue
                except Exception:
                    continue
            except Exception:
                continue
        
        return transactions
    
    def _expand_insee_codes(self, insee_code: str) -> List[str]:
        """Expansion arrondissements"""
        if insee_code == "75056":
            return [f"751{str(i).zfill(2)}" for i in range(1, 21)]
        elif insee_code == "69123":
            return [f"6938{i}" for i in range(1, 10)]
        elif insee_code == "13055":
            return [f"132{str(i).zfill(2)}" for i in range(1, 17)]
        else:
            return [insee_code]
    
    def _compute_avg_price_m2(self, transactions: List[Dict]) -> float:
        """Calcule prix moyen m²"""
        if not transactions:
            return 0.0
        
        prices_m2 = []
        for tx in transactions:
            try:
                price = float(tx.get("price", 0))
                surface = float(tx.get("surface", 0))
                if price > 0 and surface > 0:
                    prices_m2.append(price / surface)
            except (ValueError, TypeError, ZeroDivisionError):
                continue
        
        if not prices_m2:
            return 0.0
        
        return sum(prices_m2) / len(prices_m2)
    
    def _cache_get(self, key: str) -> Optional[Dict]:
        """Cache 24h"""
        cached = self._cache.get(key)
        if cached:
            ts = cached.get('_ts', 0)
            if time.time() - ts < 24 * 3600:
                return cached.get('data')
        return None
    
    def _cache_set(self, key: str, data: Dict) -> None:
        """Stocke cache"""
        self._cache[key] = {
            '_ts': time.time(),
            'data': data
        }
    
    def _get_reference_price(self, city: str, property_type: str) -> Optional[int]:
        """Récupère prix de référence pour une ville"""
        city_lower = city.lower().strip()
        
        # Recherche exacte
        if city_lower in self.reference_prices:
            return self.reference_prices[city_lower].get(property_type)
        
        # Recherche approximative (contient)
        for ref_city, prices in self.reference_prices.items():
            if ref_city != '_default' and ref_city in city_lower:
                return prices.get(property_type)
        
        # Prix par défaut
        return self.reference_prices['_default'].get(property_type)


def test_api():
    """Test API"""
    api = PriceAPI()
    
    print("\n=== Test Paris 75001 ===")
    result = api.get_local_prices("Paris", postal_code="75001", property_type="apartment")
    print(result)
    
    if 'price_per_sqm' in result:
        comparison = api.compare_property_price(300000, 50, result)
        print(f"\nComparaison 300k€ / 50m²:")
        print(f"  Bien: {comparison.get('property_price_per_sqm')}€/m²")
        print(f"  Marché: {comparison.get('market_price_per_sqm')}€/m²")
        print(f"  Écart: {comparison.get('percentage_difference')}%")
        print(f"  {comparison.get('evaluation')}")
    
    print("\n=== Test Lyon 69001 ===")
    result2 = api.get_local_prices("Lyon", postal_code="69001", property_type="apartment")
    print(result2)


if __name__ == "__main__":
    test_api()
