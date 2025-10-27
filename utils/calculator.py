"""
Module de calculs financiers pour l'investissement immobilier
Calcul simple de rentabilité brute

Auteur: Assistant IA
Date: Octobre 2025
"""

import logging
from typing import Dict

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RentabilityCalculator:
    """
    Calculateur de rentabilité immobilière simplifié
    
    Calcule la rentabilité brute à partir du prix d'achat et du loyer mensuel estimé
    """
    
    def __init__(self):
        """Initialise le calculateur"""
        logger.info("Calculateur de rentabilité initialisé")
    
    def calculate_gross_yield(self, purchase_price: float, monthly_rent: float) -> Dict:
        """
        Calcule la rentabilité brute
        
        Formule : Rentabilité brute = (Loyer annuel / Prix d'achat) × 100
        
        Args:
            purchase_price: Prix d'achat du bien (€)
            monthly_rent: Loyer mensuel estimé (€)
            
        Returns:
            Dict avec les résultats :
            - gross_yield: Rentabilité brute en %
            - annual_rent: Loyer annuel en €
            - purchase_price: Prix d'achat en €
            - evaluation: Évaluation textuelle
        """
        if purchase_price <= 0:
            return {
                'error': 'Prix d\'achat invalide',
                'gross_yield': 0,
                'annual_rent': 0,
                'purchase_price': purchase_price
            }
        
        if monthly_rent <= 0:
            return {
                'error': 'Loyer mensuel invalide',
                'gross_yield': 0,
                'annual_rent': 0,
                'purchase_price': purchase_price
            }
        
        # Calcul du loyer annuel
        annual_rent = monthly_rent * 12
        
        # Calcul de la rentabilité brute
        gross_yield = (annual_rent / purchase_price) * 100
        
        # Évaluation qualitative
        if gross_yield >= 8:
            evaluation = "🟢 Excellente rentabilité"
        elif gross_yield >= 6:
            evaluation = "🟢 Bonne rentabilité"
        elif gross_yield >= 4:
            evaluation = "🟡 Rentabilité correcte"
        elif gross_yield >= 2:
            evaluation = "🟠 Rentabilité faible"
        else:
            evaluation = "🔴 Rentabilité très faible"
        
        logger.info(f"Rentabilité brute calculée : {gross_yield:.2f}%")
        
        return {
            'gross_yield': round(gross_yield, 2),
            'annual_rent': round(annual_rent, 2),
            'monthly_rent': round(monthly_rent, 2),
            'purchase_price': round(purchase_price, 2),
            'evaluation': evaluation
        }


# Test
if __name__ == "__main__":
    calculator = RentabilityCalculator()
    
    print("Test du calculateur de rentabilité simplifié")
    print("=" * 50)
    
    # Test 1 : Bon rendement
    print("\nTest 1 : Appartement 200 000€, loyer 1000€/mois")
    result = calculator.calculate_gross_yield(200000, 1000)
    print(f"  Rentabilité brute : {result['gross_yield']}%")
    print(f"  Loyer annuel : {result['annual_rent']}€")
    print(f"  Évaluation : {result['evaluation']}")
    
    # Test 2 : Rendement moyen
    print("\nTest 2 : Maison 300 000€, loyer 1200€/mois")
    result = calculator.calculate_gross_yield(300000, 1200)
    print(f"  Rentabilité brute : {result['gross_yield']}%")
    print(f"  Loyer annuel : {result['annual_rent']}€")
    print(f"  Évaluation : {result['evaluation']}")
    
    # Test 3 : Faible rendement
    print("\nTest 3 : Appartement Paris 500 000€, loyer 1500€/mois")
    result = calculator.calculate_gross_yield(500000, 1500)
    print(f"  Rentabilité brute : {result['gross_yield']}%")
    print(f"  Loyer annuel : {result['annual_rent']}€")
    print(f"  Évaluation : {result['evaluation']}")