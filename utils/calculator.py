"""
Module de calculs financiers pour l'investissement immobilier
Calcule la rentabilité, le cashflow, les charges, etc.

Auteur: Assistant IA
Date: Octobre 2024
"""

import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InvestmentType(Enum):
    """Types d'investissement immobilier"""
    PERSONAL = "achat_personnel"
    RENTAL = "investissement_locatif"
    FLIP = "achat_revente"

class OwnershipType(Enum):
    """Types de propriété"""
    PERSONAL_NAME = "nom_propre"
    SCI = "sci"
    JOINT_OWNERSHIP = "indivision"

@dataclass
class PropertyFinancials:
    """Structure des données financières d'un bien"""
    purchase_price: float
    surface: float
    monthly_rent: Optional[float] = None
    annual_charges: Optional[float] = None
    annual_property_tax: Optional[float] = None
    management_fees_rate: Optional[float] = None
    vacancy_rate: Optional[float] = None
    annual_maintenance: Optional[float] = None
    notary_fees_rate: Optional[float] = None
    loan_amount: Optional[float] = None
    loan_rate: Optional[float] = None
    loan_duration_years: Optional[int] = None

@dataclass
class FinancialResults:
    """Résultats des calculs financiers"""
    gross_yield: float
    net_yield: float
    monthly_cashflow: float
    annual_cashflow: float
    total_annual_charges: float
    net_annual_income: float
    roi: float
    payback_period_years: Optional[float] = None
    price_per_sqm: float = 0.0

class RentabilityCalculator:
    """
    Calculateur de rentabilité immobilière
    
    Cette classe effectue tous les calculs financiers nécessaires pour évaluer
    un investissement immobilier : rentabilité brute/nette, cashflow, ROI, etc.
    """
    
    def __init__(self):
        """Initialise le calculateur avec les paramètres par défaut"""
        # Taux par défaut (modifiables selon les besoins)
        self.default_notary_fees_rate = 0.08  # 8% frais de notaire
        self.default_management_fees_rate = 0.05  # 5% frais de gestion
        self.default_vacancy_rate = 0.05  # 5% vacance locative
        self.default_maintenance_rate = 0.01  # 1% du prix d'achat par an
        self.default_property_tax_rate = 0.012  # 1.2% taxe foncière par an
        
        logger.info("Calculateur de rentabilité initialisé")
    
    def calculate_full_analysis(self, 
                              property_data: Dict, 
                              user_inputs: Dict) -> FinancialResults:
        """
        Effectue une analyse financière complète du bien
        
        Args:
            property_data (Dict): Données du bien (prix, surface, etc.)
            user_inputs (Dict): Réponses de l'utilisateur (loyer, charges, etc.)
            
        Returns:
            FinancialResults: Résultats complets de l'analyse
        """
        logger.info("Début de l'analyse financière complète")
        
        try:
            # Création de l'objet PropertyFinancials
            financials = self._build_property_financials(property_data, user_inputs)
            
            # Calculs principaux
            results = self._perform_calculations(financials)
            
            logger.info("Analyse financière terminée avec succès")
            return results
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse financière: {str(e)}")
            raise
    
    def _build_property_financials(self, 
                                 property_data: Dict, 
                                 user_inputs: Dict) -> PropertyFinancials:
        """
        Construit l'objet PropertyFinancials à partir des données
        
        Args:
            property_data (Dict): Données du bien
            user_inputs (Dict): Réponses utilisateur
            
        Returns:
            PropertyFinancials: Objet contenant toutes les données financières
        """
        # Données de base du bien
        purchase_price = float(property_data.get('price', 0))
        surface = float(property_data.get('surface', 0))
        
        # Données utilisateur avec valeurs par défaut intelligentes
        monthly_rent = user_inputs.get('monthly_rent')
        if monthly_rent:
            monthly_rent = float(monthly_rent)
        elif purchase_price and surface:
            # Estimation du loyer si non fourni (environ 0.7% du prix par mois)
            monthly_rent = purchase_price * 0.007
        
        # Charges annuelles
        annual_charges = user_inputs.get('annual_charges')
        if annual_charges:
            annual_charges = float(annual_charges)
        else:
            # Estimation : 20€/m² par an pour un appartement
            annual_charges = surface * 20 if surface else 0
        
        # Taxe foncière
        annual_property_tax = user_inputs.get('property_tax')
        if annual_property_tax:
            annual_property_tax = float(annual_property_tax)
        else:
            # Estimation : 1.2% du prix d'achat
            annual_property_tax = purchase_price * self.default_property_tax_rate
        
        # Frais de gestion
        management_fees_rate = user_inputs.get('management_fees_rate', self.default_management_fees_rate)
        
        # Taux de vacance
        vacancy_rate = user_inputs.get('vacancy_rate', self.default_vacancy_rate)
        
        # Maintenance annuelle
        annual_maintenance = user_inputs.get('annual_maintenance')
        if annual_maintenance is None:
            annual_maintenance = purchase_price * self.default_maintenance_rate
        
        # Frais de notaire
        notary_fees_rate = user_inputs.get('notary_fees_rate', self.default_notary_fees_rate)
        
        # Données de financement (optionnelles)
        loan_amount = user_inputs.get('loan_amount')
        loan_rate = user_inputs.get('loan_rate')
        loan_duration = user_inputs.get('loan_duration_years')
        
        return PropertyFinancials(
            purchase_price=purchase_price,
            surface=surface,
            monthly_rent=monthly_rent,
            annual_charges=annual_charges,
            annual_property_tax=annual_property_tax,
            management_fees_rate=management_fees_rate,
            vacancy_rate=vacancy_rate,
            annual_maintenance=annual_maintenance,
            notary_fees_rate=notary_fees_rate,
            loan_amount=loan_amount,
            loan_rate=loan_rate,
            loan_duration_years=loan_duration
        )
    
    def _perform_calculations(self, financials: PropertyFinancials) -> FinancialResults:
        """
        Effectue tous les calculs financiers
        
        Args:
            financials (PropertyFinancials): Données financières du bien
            
        Returns:
            FinancialResults: Résultats des calculs
        """
        # Calculs de base
        annual_rent = financials.monthly_rent * 12 if financials.monthly_rent else 0
        
        # Prix au m²
        price_per_sqm = financials.purchase_price / financials.surface if financials.surface else 0
        
        # Revenus nets annuels (après vacance)
        net_annual_income = annual_rent * (1 - financials.vacancy_rate)
        
        # Charges totales annuelles
        management_fees = net_annual_income * financials.management_fees_rate
        total_annual_charges = (
            financials.annual_charges +
            financials.annual_property_tax +
            financials.annual_maintenance +
            management_fees
        )
        
        # Rentabilité brute
        gross_yield = (annual_rent / financials.purchase_price * 100) if financials.purchase_price else 0
        
        # Revenus nets après charges
        net_income_after_charges = net_annual_income - total_annual_charges
        
        # Rentabilité nette
        net_yield = (net_income_after_charges / financials.purchase_price * 100) if financials.purchase_price else 0
        
        # Cashflow
        monthly_cashflow = net_income_after_charges / 12
        
        # Si il y a un prêt, on déduit les mensualités
        monthly_loan_payment = 0
        if financials.loan_amount and financials.loan_rate and financials.loan_duration_years:
            monthly_loan_payment = self._calculate_monthly_loan_payment(
                financials.loan_amount,
                financials.loan_rate,
                financials.loan_duration_years
            )
            monthly_cashflow -= monthly_loan_payment
        
        annual_cashflow = monthly_cashflow * 12
        
        # ROI (Return on Investment)
        # Investissement initial = apport + frais de notaire
        if financials.loan_amount:
            initial_investment = (financials.purchase_price - financials.loan_amount) + (financials.purchase_price * financials.notary_fees_rate)
        else:
            initial_investment = financials.purchase_price + (financials.purchase_price * financials.notary_fees_rate)
        
        roi = (annual_cashflow / initial_investment * 100) if initial_investment else 0
        
        # Durée de retour sur investissement
        payback_period = None
        if annual_cashflow > 0:
            payback_period = initial_investment / annual_cashflow
        
        return FinancialResults(
            gross_yield=gross_yield,
            net_yield=net_yield,
            monthly_cashflow=monthly_cashflow,
            annual_cashflow=annual_cashflow,
            total_annual_charges=total_annual_charges,
            net_annual_income=net_income_after_charges,
            roi=roi,
            payback_period_years=payback_period,
            price_per_sqm=price_per_sqm
        )
    
    def _calculate_monthly_loan_payment(self, 
                                      loan_amount: float, 
                                      annual_rate: float, 
                                      duration_years: int) -> float:
        """
        Calcule la mensualité d'un prêt
        
        Args:
            loan_amount (float): Montant du prêt
            annual_rate (float): Taux annuel (ex: 0.02 pour 2%)
            duration_years (int): Durée en années
            
        Returns:
            float: Mensualité
        """
        if annual_rate == 0:
            return loan_amount / (duration_years * 12)
        
        monthly_rate = annual_rate / 12
        num_payments = duration_years * 12
        
        # Formule de calcul d'une mensualité
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / \
                         ((1 + monthly_rate)**num_payments - 1)
        
        return monthly_payment
    
    def calculate_quick_yield(self, price: float, monthly_rent: float) -> Tuple[float, float]:
        """
        Calcul rapide de rentabilité (brute et nette estimée)
        
        Args:
            price (float): Prix d'achat
            monthly_rent (float): Loyer mensuel
            
        Returns:
            Tuple[float, float]: (rentabilité brute, rentabilité nette estimée)
        """
        if not price or not monthly_rent:
            return 0.0, 0.0
        
        annual_rent = monthly_rent * 12
        gross_yield = (annual_rent / price) * 100
        
        # Estimation de la rentabilité nette (on retire environ 30% pour les charges)
        net_yield = gross_yield * 0.7
        
        return gross_yield, net_yield
    
    def estimate_rental_yield_by_city(self, city: str, property_type: str = "apartment") -> Dict:
        """
        Estime les rendements moyens par ville (données indicatives)
        
        Args:
            city (str): Nom de la ville
            property_type (str): Type de bien
            
        Returns:
            Dict: Estimations de rendement
        """
        # Données indicatives moyennes par type de ville
        # Ces données seraient idéalement récupérées d'une API réelle
        
        city_lower = city.lower()
        
        # Grandes villes (rendements généralement plus faibles)
        major_cities = ["paris", "lyon", "marseille", "toulouse", "nice", "nantes", "strasbourg", "montpellier"]
        
        # Villes moyennes
        medium_cities = ["lille", "rennes", "reims", "le havre", "saint-etienne", "toulon", "grenoble", "dijon"]
        
        if any(major_city in city_lower for major_city in major_cities):
            return {
                "gross_yield_range": (2.5, 4.5),
                "net_yield_range": (1.8, 3.2),
                "average_price_per_sqm": 5500,
                "market_type": "Grande ville"
            }
        elif any(medium_city in city_lower for medium_city in medium_cities):
            return {
                "gross_yield_range": (4.0, 6.0),
                "net_yield_range": (2.8, 4.2),
                "average_price_per_sqm": 3200,
                "market_type": "Ville moyenne"
            }
        else:
            return {
                "gross_yield_range": (5.0, 8.0),
                "net_yield_range": (3.5, 5.6),
                "average_price_per_sqm": 2100,
                "market_type": "Petite ville/Rural"
            }
    
    def generate_investment_advice(self, results: FinancialResults, city: str = "") -> str:
        """
        Génère des conseils d'investissement basés sur les résultats
        
        Args:
            results (FinancialResults): Résultats de l'analyse
            city (str): Ville du bien (optionnel)
            
        Returns:
            str: Conseils formatés
        """
        advice_parts = []
        
        # Analyse de la rentabilité
        if results.gross_yield >= 6:
            advice_parts.append("✅ **Rentabilité brute excellente** (≥6%)")
        elif results.gross_yield >= 4:
            advice_parts.append("🟡 **Rentabilité brute correcte** (4-6%)")
        else:
            advice_parts.append("🔴 **Rentabilité brute faible** (<4%)")
        
        # Analyse du cashflow
        if results.monthly_cashflow > 0:
            advice_parts.append(f"✅ **Cashflow positif** de {results.monthly_cashflow:.0f}€/mois")
        elif results.monthly_cashflow > -100:
            advice_parts.append(f"🟡 **Cashflow légèrement négatif** de {results.monthly_cashflow:.0f}€/mois")
        else:
            advice_parts.append(f"🔴 **Cashflow très négatif** de {results.monthly_cashflow:.0f}€/mois")
        
        # Analyse du ROI
        if results.roi >= 8:
            advice_parts.append("✅ **ROI excellent** (≥8%)")
        elif results.roi >= 5:
            advice_parts.append("🟡 **ROI correct** (5-8%)")
        else:
            advice_parts.append("🔴 **ROI faible** (<5%)")
        
        # Conseil sur la durée de retour
        if results.payback_period_years and results.payback_period_years <= 15:
            advice_parts.append(f"✅ **Retour sur investissement rapide** ({results.payback_period_years:.1f} ans)")
        elif results.payback_period_years and results.payback_period_years <= 25:
            advice_parts.append(f"🟡 **Retour sur investissement modéré** ({results.payback_period_years:.1f} ans)")
        elif results.payback_period_years:
            advice_parts.append(f"🔴 **Retour sur investissement long** ({results.payback_period_years:.1f} ans)")
        
        # Comparaison avec le marché local si ville fournie
        if city:
            market_data = self.estimate_rental_yield_by_city(city)
            min_yield, max_yield = market_data["gross_yield_range"]
            
            if results.gross_yield >= max_yield:
                advice_parts.append(f"🎯 **Excellent par rapport au marché local** ({min_yield}-{max_yield}%)")
            elif results.gross_yield >= min_yield:
                advice_parts.append(f"👍 **Dans la moyenne du marché local** ({min_yield}-{max_yield}%)")
            else:
                advice_parts.append(f"⚠️ **En dessous du marché local** ({min_yield}-{max_yield}%)")
        
        # Conseils généraux
        advice_parts.append("\n**📋 Conseils :**")
        
        if results.net_yield < 3:
            advice_parts.append("• Négociez le prix d'achat ou trouvez des moyens d'augmenter les loyers")
        
        if results.monthly_cashflow < 0:
            advice_parts.append("• Attention au cashflow négatif : prévoir une trésorerie suffisante")
        
        if results.gross_yield > 8:
            advice_parts.append("• Vérifiez bien l'état du bien et la zone géographique (rendement très élevé)")
        
        advice_parts.append("• Consultez un expert-comptable pour l'optimisation fiscale")
        advice_parts.append("• Vérifiez l'assurance PNO (Propriétaire Non Occupant)")
        
        return '\n'.join(advice_parts)

# Fonctions utilitaires pour les tests
def test_calculator():
    """Fonction de test pour le calculateur"""
    calculator = RentabilityCalculator()
    
    # Données de test
    property_data = {
        'price': 200000,
        'surface': 50,
        'city': 'Lyon'
    }
    
    user_inputs = {
        'monthly_rent': 800,
        'annual_charges': 1200,
        'investment_type': 'rental'
    }
    
    print("Test du calculateur de rentabilité...")
    print(f"Prix: {property_data['price']}€, Surface: {property_data['surface']}m², Loyer: {user_inputs['monthly_rent']}€/mois")
    
    # Test de calcul
    results = calculator.calculate_full_analysis(property_data, user_inputs)
    
    print(f"\nRésultats:")
    print(f"Rentabilité brute: {results.gross_yield:.2f}%")
    print(f"Rentabilité nette: {results.net_yield:.2f}%")
    print(f"Cashflow mensuel: {results.monthly_cashflow:.0f}€")
    print(f"ROI: {results.roi:.2f}%")
    
    # Test des conseils
    advice = calculator.generate_investment_advice(results, property_data['city'])
    print(f"\nConseils:\n{advice}")

if __name__ == "__main__":
    test_calculator()