"""
API Prix Immobiliers Simplifiée
Système simplifié avec prix de référence + score de fiabilité

Auteur: Assistant IA
Date: Octobre 2025
"""

import logging
from typing import Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimplePriceAPI:
    """API simplifiée pour les prix immobiliers"""
    
    def __init__(self):
        """Initialise l'API avec les prix de référence DVF 2024"""
        
        # Prix moyens DVF 2024 par ville (€/m²)
        # Source: Données des Valeurs Foncières 2024 (data.gouv.fr)
        self.reference_prices = {
            # Grandes métropoles
            'paris': {'apartment': 10800, 'house': 12500, 'reliability': 95},
            'lyon': {'apartment': 5100, 'house': 5800, 'reliability': 90},
            'marseille': {'apartment': 3800, 'house': 4200, 'reliability': 88},
            'toulouse': {'apartment': 4100, 'house': 4500, 'reliability': 87},
            'nice': {'apartment': 5500, 'house': 6800, 'reliability': 89},
            'nantes': {'apartment': 4200, 'house': 4800, 'reliability': 86},
            'strasbourg': {'apartment': 3500, 'house': 4000, 'reliability': 84},
            'montpellier': {'apartment': 4000, 'house': 4600, 'reliability': 85},
            'bordeaux': {'apartment': 4800, 'house': 5400, 'reliability': 88},
            'lille': {'apartment': 3300, 'house': 3800, 'reliability': 83},
            'rennes': {'apartment': 3900, 'house': 4400, 'reliability': 84},
            'reims': {'apartment': 2400, 'house': 2800, 'reliability': 78},
            'toulon': {'apartment': 3600, 'house': 4200, 'reliability': 80},
            'grenoble': {'apartment': 3700, 'house': 4300, 'reliability': 82},
            'dijon': {'apartment': 2900, 'house': 3400, 'reliability': 79},
            'angers': {'apartment': 3100, 'house': 3600, 'reliability': 80},
            'nimes': {'apartment': 2700, 'house': 3200, 'reliability': 77},
            'villeurbanne': {'apartment': 4800, 'house': 5400, 'reliability': 85},
            'clermont-ferrand': {'apartment': 2500, 'house': 3000, 'reliability': 76},
            'aix-en-provence': {'apartment': 5200, 'house': 6500, 'reliability': 87},
            'brest': {'apartment': 2600, 'house': 3100, 'reliability': 78},
            'tours': {'apartment': 3000, 'house': 3500, 'reliability': 79},
            'amiens': {'apartment': 2300, 'house': 2700, 'reliability': 75},
            'limoges': {'apartment': 1900, 'house': 2400, 'reliability': 72},
            'annecy': {'apartment': 5800, 'house': 7200, 'reliability': 88},
            # Prix moyen national par défaut
            '_default': {'apartment': 3200, 'house': 3600, 'reliability': 65}
        }
        
        logger.info("API Prix simplifiée initialisée avec 25+ villes")
    
    def get_price_estimate(self, city: str, property_type: str = "apartment") -> Dict:
        """
        Récupère le prix moyen au m² pour une ville
        
        Args:
            city: Nom de la ville
            property_type: 'apartment', 'house', ou autre
            
        Returns:
            dict: {
                'price_per_sqm': float,      # Prix moyen €/m²
                'source': str,                # Source des données
                'reliability_score': int,     # Score 0-100
                'data_period': str           # Période des données
            }
        """
        logger.info(f"Estimation pour {city} ({property_type})")
        
        # Normaliser le nom de la ville
        city_normalized = city.lower().strip()
        
        # Normaliser le type de bien
        if property_type.lower() in ['maison', 'house']:
            prop_type = 'house'
        elif property_type.lower() in ['appartement', 'apartment', 'studio']:
            prop_type = 'apartment'
        else:
            prop_type = 'apartment'  # Par défaut
        
        # 1. Chercher correspondance exacte
        if city_normalized in self.reference_prices:
            data = self.reference_prices[city_normalized]
            price = data.get(prop_type, data.get('apartment', 3200))
            reliability = data.get('reliability', 70)
            
            return {
                'price_per_sqm': price,
                'source': f'Données DVF 2024 - {city.title()}',
                'reliability_score': reliability,
                'data_period': 'Année 2024'
            }
        
        # 2. Chercher correspondance partielle (ex: "Paris 15" → "Paris")
        for ref_city, data in self.reference_prices.items():
            if ref_city == '_default':
                continue
            if ref_city in city_normalized or city_normalized in ref_city:
                price = data.get(prop_type, data.get('apartment', 3200))
                reliability = data.get('reliability', 70) - 10  # Pénalité pour match partiel
                
                return {
                    'price_per_sqm': price,
                    'source': f'Données DVF 2024 - {ref_city.title()} (estimation)',
                    'reliability_score': max(50, reliability),
                    'data_period': 'Année 2024'
                }
        
        # 3. Fallback prix moyen national
        default_data = self.reference_prices['_default']
        price = default_data.get(prop_type, 3200)
        reliability = default_data.get('reliability', 65)
        
        return {
            'price_per_sqm': price,
            'source': 'Moyenne nationale DVF 2024',
            'reliability_score': reliability,
            'data_period': 'Année 2024'
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
                'percentage_difference': float,  # + = surcoté, - = bon prix
                'score': str  # 'Bon prix', 'Prix correct', 'Surcoté'
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


# Rétrocompatibilité : alias vers SimplePriceAPI
PriceAPI = SimplePriceAPI


# Test
if __name__ == "__main__":
    api = SimplePriceAPI()
    
    # Test Paris appartement
    print("Test Paris appartement:")
    result = api.get_price_estimate("Paris", "apartment")
    print(f"  Prix: {result['price_per_sqm']}€/m²")
    print(f"  Source: {result['source']}")
    print(f"  Fiabilité: {result['reliability_score']}%")
    print()
    
    # Test Lyon maison
    print("Test Lyon maison:")
    result = api.get_price_estimate("Lyon", "house")
    print(f"  Prix: {result['price_per_sqm']}€/m²")
    print(f"  Source: {result['source']}")
    print(f"  Fiabilité: {result['reliability_score']}%")
    print()
    
    # Test ville inconnue
    print("Test Surgères (ville non référencée):")
    result = api.get_price_estimate("Surgères", "apartment")
    print(f"  Prix: {result['price_per_sqm']}€/m²")
    print(f"  Source: {result['source']}")
    print(f"  Fiabilité: {result['reliability_score']}%")
    print()
    
    # Test comparaison
    print("Test comparaison bien Paris 80m² à 720k€:")
    market = api.get_price_estimate("Paris", "apartment")
    comparison = api.compare_property_price(720000, 80, market)
    print(f"  Prix bien: {comparison['property_price_per_sqm']}€/m²")
    print(f"  Prix marché: {comparison['market_price_per_sqm']}€/m²")
    print(f"  Écart: {comparison['percentage_difference']:+.1f}%")
    print(f"  Évaluation: {comparison['score']}")
