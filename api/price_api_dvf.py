"""
API Prix Immobiliers basée sur DVF S1 2025
Utilise la base SQLite générée depuis les données DVF réelles

Auteur: Assistant IA
Date: Octobre 2025
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DVFPriceAPI:
    """API de prix basée sur données DVF S1 2025"""
    
    def __init__(self, use_lite: bool = True):
        """
        Initialise l'API avec la base DVF
        
        Args:
            use_lite: True = version Lite (50 villes), False = version complète
        """
        self.base_dir = Path(__file__).parent.parent / "data"
        
        if use_lite:
            self.db_path = self.base_dir / "dvf_prices_lite.sqlite"
        else:
            self.db_path = self.base_dir / "dvf_prices_full.sqlite"
        
        # Vérifier existence de la base
        if not self.db_path.exists():
            logger.warning(f"⚠️ Base DVF non trouvée : {self.db_path}")
            logger.warning("📥 Utilisez 'python scripts/process_dvf_data.py' pour la créer")
            self.db_path = None
        else:
            logger.info(f"✅ Base DVF chargée : {self.db_path.name}")
    
    def get_price_estimate(self, city: str, postal_code: Optional[str] = None, 
                          property_type: str = "apartment") -> Dict:
        """
        Récupère le prix moyen au m² pour une ville depuis DVF
        
        Args:
            city: Nom de la ville
            postal_code: Code postal (optionnel, améliore la précision)
            property_type: 'apartment', 'house', ou 'other'
            
        Returns:
            dict: {
                'price_per_sqm': float,
                'source': str,
                'reliability_score': int,
                'data_period': str,
                'transaction_count': int
            }
        """
        # Normaliser le type de bien
        if property_type.lower() in ['maison', 'house']:
            prop_type = 'house'
        elif property_type.lower() in ['appartement', 'apartment', 'studio']:
            prop_type = 'apartment'
        else:
            prop_type = 'other'
        
        # Si pas de base DVF, fallback sur prix nationaux
        if not self.db_path:
            return self._get_fallback_price(prop_type)
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Nettoyer le nom de ville
            city_clean = city.strip().title()
            
            # 1. Recherche exacte avec code postal
            if postal_code:
                query = """
                    SELECT price_per_sqm_mean, transaction_count, reliability_score, city
                    FROM price_data
                    WHERE postal_code = ? AND property_type = ?
                    ORDER BY transaction_count DESC
                    LIMIT 1
                """
                cursor.execute(query, (postal_code, prop_type))
                result = cursor.fetchone()
                
                if result:
                    price, count, reliability, real_city = result
                    conn.close()
                    return {
                        'price_per_sqm': int(price),
                        'source': f'DVF S1 2025 - {real_city} ({postal_code})',
                        'reliability_score': int(reliability),
                        'data_period': 'Janvier - Juin 2025',
                        'transaction_count': int(count)
                    }
            
            # 2. Recherche par nom de ville
            query = """
                SELECT price_per_sqm_mean, transaction_count, reliability_score, 
                       city, postal_code
                FROM price_data
                WHERE city LIKE ? AND property_type = ?
                ORDER BY transaction_count DESC
                LIMIT 1
            """
            cursor.execute(query, (f'%{city_clean}%', prop_type))
            result = cursor.fetchone()
            
            if result:
                price, count, reliability, real_city, cp = result
                conn.close()
                return {
                    'price_per_sqm': int(price),
                    'source': f'DVF S1 2025 - {real_city} ({cp})',
                    'reliability_score': int(reliability),
                    'data_period': 'Janvier - Juin 2025',
                    'transaction_count': int(count)
                }
            
            # 3. Fallback national si aucune correspondance
            conn.close()
            return self._get_fallback_price(prop_type, city=city)
            
        except Exception as e:
            logger.error(f"Erreur requête DVF : {e}")
            return self._get_fallback_price(prop_type)
    
    def _get_fallback_price(self, property_type: str, city: str = None) -> Dict:
        """Prix de secours si ville non trouvée dans DVF"""
        prices = {
            'apartment': 3200,
            'house': 3600,
            'other': 3000
        }
        
        source = 'Moyenne nationale DVF 2024'
        if city:
            source = f'Estimation nationale (ville "{city}" non trouvée dans DVF S1 2025)'
        
        return {
            'price_per_sqm': prices.get(property_type, 3200),
            'source': source,
            'reliability_score': 60,
            'data_period': 'Moyenne nationale',
            'transaction_count': 0
        }
    
    def compare_property_price(self, property_price: float, property_surface: float, 
                              market_data: Dict) -> Dict:
        """
        Compare le prix d'un bien avec le marché local
        
        Args:
            property_price: Prix du bien (€)
            property_surface: Surface du bien (m²)
            market_data: Données marché retournées par get_price_estimate()
            
        Returns:
            dict: {
                'property_price_per_sqm': float,
                'market_price_per_sqm': float,
                'percentage_difference': float,
                'score': str
            }
        """
        if property_surface <= 0:
            return {'error': 'Surface invalide'}
        
        property_price_sqm = property_price / property_surface
        market_price_sqm = market_data.get('price_per_sqm', 3200)
        
        # Calcul écart
        diff = ((property_price_sqm - market_price_sqm) / market_price_sqm) * 100
        
        # Score
        if diff < -10:
            score = '🟢 Excellent prix'
        elif diff < 0:
            score = '🟢 Bon prix'
        elif diff < 10:
            score = '🟡 Prix correct'
        elif diff < 20:
            score = '🟠 Légèrement surcoté'
        else:
            score = '🔴 Surcoté'
        
        return {
            'property_price_per_sqm': round(property_price_sqm, 2),
            'market_price_per_sqm': round(market_price_sqm, 2),
            'percentage_difference': round(diff, 1),
            'score': score
        }
    
    def get_database_info(self) -> Dict:
        """Retourne des infos sur la base DVF chargée"""
        if not self.db_path:
            return {'error': 'Aucune base DVF chargée'}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Nombre de villes
            cursor.execute("SELECT COUNT(DISTINCT city) FROM price_data")
            nb_cities = cursor.fetchone()[0]
            
            # Nombre total de lignes
            cursor.execute("SELECT COUNT(*) FROM price_data")
            nb_entries = cursor.fetchone()[0]
            
            # Nombre total de transactions
            cursor.execute("SELECT SUM(transaction_count) FROM price_data")
            nb_transactions = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'database': self.db_path.name,
                'cities': nb_cities,
                'entries': nb_entries,
                'total_transactions': nb_transactions,
                'period': 'Janvier - Juin 2025'
            }
        except Exception as e:
            return {'error': str(e)}


# Alias pour compatibilité
SimplePriceAPI = DVFPriceAPI
PriceAPI = DVFPriceAPI


# Tests
if __name__ == "__main__":
    # Test version Lite
    api_lite = DVFPriceAPI(use_lite=True)
    
    print("=" * 60)
    print("INFO BASE DVF")
    print("=" * 60)
    info = api_lite.get_database_info()
    for k, v in info.items():
        print(f"  {k}: {v:,}" if isinstance(v, int) else f"  {k}: {v}")
    
    print("\n" + "=" * 60)
    print("TEST ESTIMATIONS")
    print("=" * 60)
    
    # Test Paris
    print("\n1. Paris appartement (75011):")
    result = api_lite.get_price_estimate("Paris", postal_code="75011", property_type="apartment")
    print(f"   Prix: {result['price_per_sqm']:,}€/m²")
    print(f"   Source: {result['source']}")
    print(f"   Fiabilité: {result['reliability_score']}%")
    print(f"   Transactions: {result['transaction_count']}")
    
    # Test Lyon
    print("\n2. Lyon maison:")
    result = api_lite.get_price_estimate("Lyon", property_type="house")
    print(f"   Prix: {result['price_per_sqm']:,}€/m²")
    print(f"   Source: {result['source']}")
    print(f"   Fiabilité: {result['reliability_score']}%")
    print(f"   Transactions: {result['transaction_count']}")
    
    # Test ville inconnue
    print("\n3. Petite ville (Surgères):")
    result = api_lite.get_price_estimate("Surgères", property_type="apartment")
    print(f"   Prix: {result['price_per_sqm']:,}€/m²")
    print(f"   Source: {result['source']}")
    print(f"   Fiabilité: {result['reliability_score']}%")
    
    # Test comparaison
    print("\n4. Comparaison bien Paris 80m² à 720k€:")
    market = api_lite.get_price_estimate("Paris", postal_code="75011", property_type="apartment")
    comparison = api_lite.compare_property_price(720000, 80, market)
    print(f"   Prix bien: {comparison['property_price_per_sqm']:,.0f}€/m²")
    print(f"   Prix marché: {comparison['market_price_per_sqm']:,.0f}€/m²")
    print(f"   Écart: {comparison['percentage_difference']:+.1f}%")
    print(f"   Évaluation: {comparison['score']}")
    
    print("\n" + "=" * 60)
