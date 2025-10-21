"""
Module d'intégration des APIs de prix immobiliers
Récupère et compare les prix au m² du marché local

Auteur: Assistant IA
Date: Octobre 2024
"""

import os
import json
import time
import logging
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from statistics import median

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PriceAPI:
    """
    Classe pour intégrer différentes APIs de prix immobiliers
    
    Cette classe permet de récupérer les prix au m² depuis différentes sources :
    - API Data.gouv (DVF - Demandes de Valeurs Foncières)
    - API MeilleursAgents (si clé disponible)
    - API Castorus (si clé disponible)
    """
    
    def __init__(self, meilleurs_agents_key: Optional[str] = None):
        """
        Initialise le client API
        
        Args:
            meilleurs_agents_key (Optional[str]): Clé API MeilleursAgents
        """
        self.meilleurs_agents_key = meilleurs_agents_key
        self.session = requests.Session()
        
        # URLs des APIs
        self.dvf_base_url = "https://apidf-preprod.apur.org/api/dvf/opendata"
        self.data_gouv_url = "https://api.gouv.fr/api/api-dvf.html"
        self.geo_api_url = "https://geo.api.gouv.fr/communes"
        
        # Headers par défaut
        self.session.headers.update({
            'User-Agent': 'Rendimo-Assistant/1.0',
            'Accept': 'application/json'
        })

        # Cache mémoire + disque (24h)
        self._mem_cache: Dict[str, Dict] = {}
        self._cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cache_prices")
        try:
            os.makedirs(self._cache_dir, exist_ok=True)
        except Exception as e:
            logger.debug(f"Impossible de créer le dossier de cache: {e}")
        
        logger.info("Client API de prix immobiliers initialisé")
    
    def get_local_prices(self, 
                        city: str, 
                        postal_code: Optional[str] = None,
                        property_type: str = "apartment") -> Dict:
        """Récupère les prix locaux avec DVF (médiane/p10/p90) si possible, sinon fallback.

        Retourne toujours un dict avec les clés:
        price_per_sqm, min_price, max_price, transaction_count, data_period,
        city, property_type, source, confidence
        """
        logger.info(f"Recherche des prix pour {city} ({property_type})")

        # 0) Normalisation géographique (INSEE)
        insee_code = self._resolve_insee(city, postal_code)
        months = 24

        # 1) DVF avec cache si INSEE connu
        if insee_code:
            cache_key = f"{insee_code}:{property_type}:{months}"
            stats = self._cache_get(cache_key)
            if not stats:
                try:
                    txs = self._query_dvf(insee_code, property_type, months=months)
                except Exception as e:
                    logger.warning(f"Erreur _query_dvf: {e}")
                    txs = []
                try:
                    stats = self._compute_stats(txs)
                except Exception as e:
                    logger.warning(f"Erreur _compute_stats: {e}")
                    stats = {}
                if stats:
                    stats['period_months'] = months
                    self._cache_set(cache_key, stats)
            if stats and stats.get('count', 0) >= 15 and stats.get('median_m2'):
                # Confiance basée sur volume + dispersion
                base_conf = 0.3 if stats['count'] < 15 else (0.6 if stats['count'] <= 50 else 0.8)
                dispersion = 0.0
                if stats.get('median_m2') and stats.get('p90_m2') is not None and stats.get('p10_m2') is not None:
                    denom = stats['median_m2'] or 1
                    dispersion = max(0.0, (stats['p90_m2'] - stats['p10_m2']) / denom)
                adjust = max(0.0, 0.3 - min(0.3, dispersion))  # Plus l'intervalle est étroit, plus l'ajustement est grand
                confidence = round(min(1.0, base_conf + adjust), 2)

                return {
                    "price_per_sqm": int(stats['median_m2']),
                    "min_price": int(stats['p10_m2']) if stats.get('p10_m2') is not None else None,
                    "max_price": int(stats['p90_m2']) if stats.get('p90_m2') is not None else None,
                    "transaction_count": stats.get('count', 0),
                    "data_period": f"{stats.get('period_months', months)} derniers mois",
                    "city": city,
                    "postal_code": postal_code,
                    "property_type": property_type,
                    "source": "DVF (computed)",
                    "confidence": confidence,
                    # Exposer aussi les bornes pour compare_property_price
                    "p10_m2": stats.get('p10_m2'),
                    "p90_m2": stats.get('p90_m2'),
                }

        # 2) Fallback MeilleursAgents si clé fournie
        if self.meilleurs_agents_key:
            try:
                ma = self._get_meilleurs_agents_prices(city, property_type)
                if ma:
                    ma['source'] = 'MeilleursAgents'
                    # Confiance moyenne par défaut
                    ma['confidence'] = 0.6
                    return ma
            except Exception as e:
                logger.warning(f"Erreur MeilleursAgents: {e}")

        # 3) Fallback estimation locale (faible confiance)
        est = self._get_estimated_prices(city, property_type)
        est['source'] = 'Estimation'
        # Normaliser la sortie aux clés demandées
        result = {
            "price_per_sqm": int(est.get('price_per_sqm', 0)) if est.get('price_per_sqm') else 0,
            "min_price": int(est.get('min_price', 0)) if est.get('min_price') else 0,
            "max_price": int(est.get('max_price', 0)) if est.get('max_price') else 0,
            "transaction_count": est.get('transaction_count', 'N/A'),
            "data_period": est.get('data_period', 'Estimation'),
            "city": city,
            "postal_code": postal_code,
            "property_type": property_type,
            "source": est.get('source', 'Estimation'),
            "confidence": 0.3,
        }
        return result

    # ---------------------- Normalisation INSEE ----------------------
    def _resolve_insee(self, city: str, postal_code: Optional[str]) -> Optional[str]:
        """Résout le code INSEE via l'API geo.api.gouv.fr. Ne lève pas d'exception."""
        try:
            params = {"nom": city, "limit": 1}
            if postal_code:
                params = {"nom": city, "codePostal": postal_code, "limit": 1}
            resp = self.session.get(self.geo_api_url, params=params, timeout=5)
            if resp.status_code != 200:
                logger.info(f"INSEE non résolu ({resp.status_code}) pour {city} {postal_code or ''}")
                return None
            data = resp.json()
            if isinstance(data, list) and data:
                code = data[0].get("code")
                if code:
                    return code
            return None
        except requests.exceptions.RequestException as e:
            logger.info(f"Erreur réseau INSEE: {e}")
            return None
        except Exception as e:
            logger.debug(f"Erreur INSEE: {e}")
            return None

    # ---------------------- DVF plugin & stats ----------------------
    def _query_dvf(self, insee_code: str, property_type: str, months: int = 24) -> List[Dict]:
        """Récupère la liste des transactions DVF pour un code INSEE et un type.

        TODO: Brancher ici une vraie API DVF (ETALAB / data.gouv) quand disponible.
        Cette implémentation MVP retourne une liste vide pour ne pas bloquer.
        """
        try:
            # Point d'injection futur:
            # dvf_api_url = os.getenv("DVF_API_URL")
            # if dvf_api_url:
            #     ... appeler l'API, transformer la réponse en liste de dicts standardisés
            return []
        except Exception as e:
            logger.debug(f"_query_dvf error: {e}")
            return []

    def _compute_stats(self, transactions: List[Dict]) -> Dict:
        """Calcule median/p10/p90 sur les prix au m² à partir d'une liste de transactions.

        Chaque transaction est supposée contenir au minimum:
        - price (euros)
        - surface (m² habitables)
        - type (optionnel: 'apartment'|'house')
        - date (optionnelle: 'YYYY-MM-DD')
        """
        try:
            # Filtrage qualité
            prices_m2: List[float] = []
            last_date: Optional[str] = None
            for tx in transactions or []:
                try:
                    price = float(tx.get('price', 0))
                    surface = float(tx.get('surface', 0))
                    if price <= 1000 or surface < 8 or surface > 300:
                        continue
                    # Type si fourni (tolérant)
                    t = tx.get('type')
                    if t and t not in ('apartment', 'house', 'Appartement', 'Maison'):
                        continue
                    prices_m2.append(price / surface)
                    # Date la plus récente
                    d = tx.get('date')
                    if d and (not last_date or d > last_date):
                        last_date = d
                except Exception:
                    continue

            if not prices_m2:
                return {}

            prices_m2.sort()
            count = len(prices_m2)

            def percentile(sorted_list: List[float], p: float) -> float:
                """Calcul de percentile sans numpy (p entre 0 et 100)."""
                if not sorted_list:
                    return 0.0
                k = (len(sorted_list) - 1) * (p / 100.0)
                f = int(k)
                c = min(f + 1, len(sorted_list) - 1)
                if f == c:
                    return sorted_list[int(k)]
                d0 = sorted_list[f] * (c - k)
                d1 = sorted_list[c] * (k - f)
                return d0 + d1

            med = median(prices_m2)
            p10 = percentile(prices_m2, 10)
            p90 = percentile(prices_m2, 90)

            return {
                'median_m2': round(med),
                'p10_m2': round(p10),
                'p90_m2': round(p90),
                'count': count,
                'period_months': None,  # rempli en amont
                'last_tx_date': last_date,
            }
        except Exception as e:
            logger.debug(f"_compute_stats error: {e}")
            return {}

    # ---------------------- Cache 24h ----------------------
    def _cache_get(self, key: str) -> Optional[Dict]:
        """Récupère une entrée de cache si < 24h (mémoire puis disque)."""
        try:
            now = time.time()
            # mémoire
            cached = self._mem_cache.get(key)
            if cached and (now - cached.get('_ts', 0) < 24 * 3600):
                return cached.get('data')
            # disque
            fpath = os.path.join(self._cache_dir, f"{self._safe_key(key)}.json")
            if os.path.exists(fpath):
                with open(fpath, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
                if now - payload.get('_ts', 0) < 24 * 3600:
                    self._mem_cache[key] = payload
                    return payload.get('data')
        except Exception as e:
            logger.debug(f"_cache_get error: {e}")
        return None

    def _cache_set(self, key: str, data: Dict) -> None:
        """Écrit dans le cache (mémoire + disque)."""
        try:
            payload = {'_ts': time.time(), 'data': data}
            self._mem_cache[key] = payload
            fpath = os.path.join(self._cache_dir, f"{self._safe_key(key)}.json")
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.debug(f"_cache_set error: {e}")

    @staticmethod
    def _safe_key(key: str) -> str:
        return key.replace(':', '_').replace('/', '_')
    
    def _get_dvf_prices(self, 
                       city: str, 
                       postal_code: Optional[str],
                       property_type: str) -> Optional[Dict]:
        """
        Récupère les prix depuis l'API DVF (Demandes de Valeurs Foncières)
        
        Args:
            city (str): Nom de la ville
            postal_code (Optional[str]): Code postal
            property_type (str): Type de bien
            
        Returns:
            Optional[Dict]: Données de prix ou None
        """
        try:
            # Construction de la requête pour l'API DVF
            # Note: Cette API peut avoir des limitations ou changer
            
            # URL simplifiée pour DVF
            params = {
                'nom_commune': city.upper(),
                'nature_mutation': 'Vente',
                'type_local': 'Appartement' if property_type == 'apartment' else 'Maison'
            }
            
            if postal_code:
                params['code_postal'] = postal_code
            
            # NOTE: Cette méthode historique est conservée pour compatibilité
            # mais le nouveau flux DVF passe par _resolve_insee/_query_dvf/_compute_stats
            # Ici, on continue de renvoyer une simulation si appelée.
            return self._simulate_dvf_response(city, property_type)
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération DVF: {str(e)}")
            return None
    
    def _simulate_dvf_response(self, city: str, property_type: str) -> Dict:
        """
        Simule une réponse DVF avec des données réalistes
        (En production, cette méthode serait remplacée par de vrais appels API)
        
        Args:
            city (str): Nom de la ville
            property_type (str): Type de bien
            
        Returns:
            Dict: Données simulées
        """
        # Base de données simplifiée des prix par ville
        city_prices = {
            'paris': {'apartment': 10500, 'house': 12000},
            'lyon': {'apartment': 4800, 'house': 5200},
            'marseille': {'apartment': 3200, 'house': 3800},
            'toulouse': {'apartment': 3800, 'house': 4200},
            'nice': {'apartment': 5200, 'house': 6000},
            'nantes': {'apartment': 3600, 'house': 4000},
            'strasbourg': {'apartment': 3200, 'house': 3600},
            'montpellier': {'apartment': 3800, 'house': 4200},
            'bordeaux': {'apartment': 4200, 'house': 4600},
            'lille': {'apartment': 2800, 'house': 3200}
        }
        
        city_lower = city.lower()
        
        # Recherche exacte puis approximative
        price_per_sqm = None
        for city_key, prices in city_prices.items():
            if city_key in city_lower or city_lower in city_key:
                price_per_sqm = prices.get(property_type, prices['apartment'])
                break
        
        # Prix par défaut si ville non trouvée
        if price_per_sqm is None:
            if 'paris' in city_lower:
                price_per_sqm = 10500 if property_type == 'apartment' else 12000
            else:
                # Prix moyen national
                price_per_sqm = 3200 if property_type == 'apartment' else 3600
        
        # Variation de ±10% pour simuler la réalité
        import random
        variation = random.uniform(0.9, 1.1)
        price_per_sqm = int(price_per_sqm * variation)
        
        return {
            'price_per_sqm': price_per_sqm,
            'min_price': int(price_per_sqm * 0.8),
            'max_price': int(price_per_sqm * 1.2),
            'transaction_count': random.randint(50, 300),
            'data_period': '12 derniers mois',
            'city': city,
            'property_type': property_type
        }
    
    def _get_meilleurs_agents_prices(self, city: str, property_type: str) -> Optional[Dict]:
        """
        Récupère les prix depuis l'API MeilleursAgents
        
        Args:
            city (str): Nom de la ville
            property_type (str): Type de bien
            
        Returns:
            Optional[Dict]: Données de prix ou None
        """
        if not self.meilleurs_agents_key:
            return None
        
        try:
            # URL de l'API MeilleursAgents (exemple)
            url = "https://api.meilleursagents.com/v1/prices/search"
            
            headers = {
                'Authorization': f'Bearer {self.meilleurs_agents_key}',
                'Content-Type': 'application/json'
            }
            
            params = {
                'city': city,
                'property_type': property_type,
                'transaction_type': 'sale'
            }
            
            response = self.session.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Traitement de la réponse (structure dépendante de l'API réelle)
            if data and 'price_per_sqm' in data:
                return {
                    'price_per_sqm': data['price_per_sqm'],
                    'min_price': data.get('min_price'),
                    'max_price': data.get('max_price'),
                    'transaction_count': data.get('transaction_count'),
                    'data_period': data.get('period', '12 derniers mois'),
                    'city': city,
                    'property_type': property_type
                }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur API MeilleursAgents: {str(e)}")
        except Exception as e:
            logger.error(f"Erreur lors du traitement MeilleursAgents: {str(e)}")
        
        return None
    
    def _get_estimated_prices(self, city: str, property_type: str) -> Dict:
        """
        Fournit des estimations de prix basées sur des données moyennes
        
        Args:
            city (str): Nom de la ville
            property_type (str): Type de bien
            
        Returns:
            Dict: Estimations de prix
        """
        # Estimations basées sur la taille de la ville et la région
        city_lower = city.lower()
        
        # Classification des villes
        major_cities = ['paris', 'lyon', 'marseille', 'toulouse', 'nice', 'nantes', 'strasbourg', 'montpellier', 'bordeaux', 'lille']
        
        if any(major_city in city_lower for major_city in major_cities):
            base_price = 4500 if property_type == 'apartment' else 5000
            category = "Grande ville"
        else:
            # Estimation pour ville moyenne/petite
            base_price = 2800 if property_type == 'apartment' else 3200
            category = "Ville moyenne"
        
        # Ajustements régionaux approximatifs
        if 'paris' in city_lower or 'neuilly' in city_lower or 'boulogne' in city_lower:
            base_price *= 2.5
        elif any(region in city_lower for region in ['lyon', 'nice', 'cannes', 'antibes']):
            base_price *= 1.3
        
        return {
            'price_per_sqm': base_price,
            'min_price': int(base_price * 0.8),
            'max_price': int(base_price * 1.2),
            'transaction_count': 'N/A',
            'data_period': 'Estimation moyenne',
            'city': city,
            'property_type': property_type,
            'category': category,
            'reliability': 'Estimation'
        }
    
    def compare_property_price(self, 
                              property_price: float,
                              property_surface: float,
                              market_data: Dict) -> Dict:
        """
        Compare le prix d'un bien avec le marché local
        
        Args:
            property_price (float): Prix du bien
            property_surface (float): Surface du bien
            market_data (Dict): Données du marché local
            
        Returns:
            Dict: Résultats de la comparaison
        """
        if not property_surface or property_surface <= 0:
            return {'error': 'Surface invalide'}
        
        property_price_per_sqm = property_price / property_surface
        market_price_per_sqm = market_data.get('price_per_sqm', 0)
        
        if market_price_per_sqm <= 0:
            return {'error': 'Données de marché invalides'}
        
        # Calcul de la différence
        difference = property_price_per_sqm - market_price_per_sqm
        percentage_difference = (difference / market_price_per_sqm) * 100
        
        # Évaluation
        if percentage_difference <= -15:
            evaluation = "Très bon prix (>15% sous le marché)"
            score = "Excellent"
        elif percentage_difference <= -5:
            evaluation = "Bon prix (5-15% sous le marché)"
            score = "Bon"
        elif percentage_difference <= 5:
            evaluation = "Prix dans la moyenne (±5%)"
            score = "Correct"
        elif percentage_difference <= 15:
            evaluation = "Prix un peu élevé (5-15% au-dessus)"
            score = "Élevé"
        else:
            evaluation = "Prix très élevé (>15% au-dessus)"
            score = "Très élevé"
        
        # Position relative par rapport à l'intervalle inter-déciles si dispo
        p10 = market_data.get('p10_m2')
        p90 = market_data.get('p90_m2')
        relative_position = None
        if isinstance(p10, (int, float)) and isinstance(p90, (int, float)) and p10 and p90:
            if property_price_per_sqm < p10:
                relative_position = "Très sous le marché"
            elif property_price_per_sqm > p90:
                relative_position = "Très au-dessus du marché"
            else:
                relative_position = "Dans l’intervalle inter-déciles"

        return {
            'property_price_per_sqm': property_price_per_sqm,
            'market_price_per_sqm': market_price_per_sqm,
            'difference': difference,
            'percentage_difference': percentage_difference,
            'evaluation': evaluation,
            'score': score,
            'market_data': market_data,
            'relative_position': relative_position
        }
    
    def get_historical_trends(self, city: str, period_months: int = 12) -> Dict:
        """
        Récupère les tendances historiques des prix (simulation)
        
        Args:
            city (str): Nom de la ville
            period_months (int): Période en mois
            
        Returns:
            Dict: Données de tendance
        """
        # Pour ce MVP, on simule des tendances
        import random
        
        # Génération d'une tendance simulée
        monthly_changes = []
        current_change = 0
        
        for month in range(period_months):
            # Simulation d'une variation mensuelle réaliste
            change = random.uniform(-0.5, 0.8)  # Entre -0.5% et +0.8% par mois
            current_change += change
            monthly_changes.append(round(current_change, 2))
        
        # Calcul de la tendance générale
        total_change = monthly_changes[-1] if monthly_changes else 0
        
        if total_change > 5:
            trend = "Hausse forte"
        elif total_change > 2:
            trend = "Hausse modérée"
        elif total_change > -2:
            trend = "Stabilité"
        elif total_change > -5:
            trend = "Baisse modérée"
        else:
            trend = "Baisse forte"
        
        return {
            'city': city,
            'period_months': period_months,
            'total_change_percent': total_change,
            'trend': trend,
            'monthly_changes': monthly_changes,
            'last_update': datetime.now().strftime('%Y-%m-%d')
        }
    
    def get_neighborhood_analysis(self, city: str, postal_code: Optional[str] = None) -> Dict:
        """
        Analyse du quartier et des commodités (simulation)
        
        Args:
            city (str): Nom de la ville
            postal_code (Optional[str]): Code postal
            
        Returns:
            Dict: Analyse du quartier
        """
        # Simulation d'une analyse de quartier
        import random
        
        # Scores aléatoires mais cohérents
        scores = {
            'transport': random.randint(6, 9),
            'commerces': random.randint(5, 9),
            'ecoles': random.randint(6, 9),
            'securite': random.randint(6, 8),
            'pollution': random.randint(4, 8),
            'espaces_verts': random.randint(4, 8)
        }
        
        # Score global
        global_score = sum(scores.values()) / len(scores)
        
        # Appréciation
        if global_score >= 8:
            appreciation = "Excellent quartier"
        elif global_score >= 7:
            appreciation = "Très bon quartier"
        elif global_score >= 6:
            appreciation = "Bon quartier"
        else:
            appreciation = "Quartier moyen"
        
        return {
            'city': city,
            'postal_code': postal_code,
            'scores': scores,
            'global_score': round(global_score, 1),
            'appreciation': appreciation,
            'transport_note': "Métro/Bus à proximité" if scores['transport'] >= 7 else "Transport limité",
            'analysis_date': datetime.now().strftime('%Y-%m-%d')
        }

# Fonction utilitaire pour tester le module
def test_price_api():
    """Fonction de test pour l'API de prix"""
    api = PriceAPI()
    
    print("Test de l'API de prix immobiliers...")
    
    # Test de récupération des prix
    city = "Lyon"
    property_type = "apartment"
    
    print(f"Recherche des prix pour {city} ({property_type})")
    
    market_data = api.get_local_prices(city, property_type=property_type)
    print(f"Prix au m²: {market_data.get('price_per_sqm', 'N/A')}€")
    print(f"Source: {market_data.get('source', 'N/A')}")
    print(f"Confiance: {market_data.get('confidence', 'N/A')}")
    if 'p10_m2' in market_data:
        print(f"P10: {market_data.get('p10_m2')}€ | P90: {market_data.get('p90_m2')}€")
    
    # Test de comparaison
    property_price = 200000
    property_surface = 50
    
    comparison = api.compare_property_price(property_price, property_surface, market_data)
    print(f"\nComparaison:")
    print(f"Prix du bien: {comparison.get('property_price_per_sqm', 0):.0f}€/m²")
    print(f"Prix marché: {comparison.get('market_price_per_sqm', 0):.0f}€/m²")
    print(f"Évaluation: {comparison.get('evaluation', 'N/A')}")
    
    # Test DVF indisponible => fallback estimations
    city2 = "Surgères"
    md2 = api.get_local_prices(city2, postal_code="17700", property_type="house")
    print(f"\n[{city2}] Prix: {md2.get('price_per_sqm')}€, Source: {md2.get('source')}, Confiance: {md2.get('confidence')}")

    # Test des tendances
    trends = api.get_historical_trends(city)
    print(f"\nTendance sur 12 mois: {trends.get('trend', 'N/A')} ({trends.get('total_change_percent', 0):+.1f}%)")

if __name__ == "__main__":
    test_price_api()