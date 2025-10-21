"""
Module de scraping simplifié pour LeBonCoin
Version nettoyée pour Rendimo

Auteur: Assistant IA
Date: Octobre 2024
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import logging
from typing import Dict, Optional
import time
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LeBonCoinScraper:
    """Scraper simplifié pour LeBonCoin"""
    
    def __init__(self):
        """Initialise le scraper avec headers modernes"""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def validate_url(self, url: str) -> bool:
        """Valide une URL LeBonCoin"""
        try:
            return 'leboncoin.fr' in url and 'ventes_immobilieres' in url
        except:
            return False
    
    def extract_property_data(self, url: str) -> Optional[Dict]:
        """Extrait les données d'une annonce"""
        if not self.validate_url(url):
            logger.error("URL invalide")
            return None
        
        try:
            logger.info(f"Extraction: {url}")
            
            # Récupération avec retry
            response = self._get_page_with_retry(url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            logger.info("HTML parsé")
            
            # Extraction des données
            property_data = {
                'title': self._extract_title(soup),
                'price': self._extract_price(soup),
                'surface': self._extract_surface(soup),
                'rooms': self._extract_rooms(soup),
                'city': self._extract_city(soup),
                'property_type': self._extract_type(soup),
                'description': self._extract_description(soup),
                'source_url': url,
                'extraction_date': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Vérification que nous avons des données utiles
            if property_data['title'] or property_data['price'] > 0:
                logger.info(f"Extraction réussie: {property_data['title']}")
                return property_data
            
            logger.warning("Aucune donnée utile extraite")
            return None
            
        except Exception as e:
            logger.error(f"Erreur extraction: {str(e)}")
            return None
    
    def _get_page_with_retry(self, url: str, max_retries: int = 3):
        """Récupère la page avec gestion des erreurs"""
        for attempt in range(max_retries):
            try:
                # Délai aléatoire pour simuler comportement humain
                time.sleep(random.uniform(1, 3))
                
                response = self.session.get(url, timeout=15)
                
                if response.status_code == 403:
                    logger.warning(f"Erreur 403 (tentative {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(random.uniform(2, 5))
                        continue
                
                response.raise_for_status()
                logger.info(f"Page récupérée: {response.status_code}")
                return response
                
            except Exception as e:
                logger.error(f"Tentative {attempt + 1} échouée: {e}")
                if attempt == max_retries - 1:
                    return None
                    
        return None
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extrait le titre de l'annonce"""
        selectors = ['h1', '[data-qa-id="adview_title"]', '.breadcrumb-summary-title']
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                return element.get_text(strip=True)
        
        return ""
    
    def _extract_price(self, soup: BeautifulSoup) -> int:
        """Extrait le prix"""
        selectors = [
            '[data-qa-id="adview_price"]',
            '.styles_price__3Uukr',
            'span[aria-label*="Prix"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text(strip=True)
                # Extraire seulement les chiffres
                price_clean = re.sub(r'[^\d]', '', price_text)
                if price_clean:
                    return int(price_clean)
        
        # Recherche dans tout le texte pour les prix en €
        all_text = soup.get_text()
        price_matches = re.findall(r'([\d\s]+)\s*€', all_text)
        for match in price_matches:
            price_clean = re.sub(r'[^\d]', '', match)
            if price_clean and len(price_clean) >= 4:  # Au moins 1000€
                return int(price_clean)
        
        return 0
    
    def _extract_surface(self, soup: BeautifulSoup) -> int:
        """Extrait la surface en m²"""
        # Recherche dans tout le texte
        all_text = soup.get_text()
        surface_matches = re.findall(r'(\d+)\s*m²', all_text)
        
        for match in surface_matches:
            surface = int(match)
            if 10 <= surface <= 500:  # Fourchette réaliste
                return surface
        
        return 0
    
    def _extract_rooms(self, soup: BeautifulSoup) -> int:
        """Extrait le nombre de pièces"""
        all_text = soup.get_text()
        
        # Différents patterns possibles
        patterns = [
            r'(\d+)\s*pièces?',
            r'(\d+)\s*p\.',
            r'T(\d+)',
            r'(\d+)\s*ch\.'  # chambres
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            for match in matches:
                rooms = int(match)
                if 1 <= rooms <= 10:  # Fourchette réaliste
                    return rooms
        
        return 0
    
    def _extract_city(self, soup: BeautifulSoup) -> str:
        """Extrait la ville"""
        selectors = [
            '[data-qa-id*="location"]',
            '.styles_location__3s1s8',
            '[class*="location"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                location_text = element.get_text(strip=True)
                # Extraire la ville (premier mot généralement)
                if location_text:
                    words = location_text.split()
                    return words[0] if words else location_text
        
        return ""
    
    def _extract_type(self, soup: BeautifulSoup) -> str:
        """Extrait le type de bien"""
        all_text = soup.get_text().lower()
        
        if 'maison' in all_text:
            return 'Maison'
        elif 'appartement' in all_text:
            return 'Appartement'
        elif 'studio' in all_text:
            return 'Studio'
        else:
            return 'Autre'
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extrait la description"""
        selectors = [
            '[data-qa-id="adview_description"]',
            '.description',
            '[class*="description"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)[:500]  # Limiter à 500 caractères
        
        return ""

def test_scraper():
    """Test du scraper"""
    scraper = LeBonCoinScraper()
    test_url = "https://www.leboncoin.fr/ventes_immobilieres/test"
    
    print("🔍 Test scraper simplifié")
    print(f"URL valide: {scraper.validate_url(test_url)}")
    
    data = scraper.extract_property_data(test_url)
    if data:
        print("✅ Données extraites:")
        for key, value in data.items():
            print(f"  {key}: {value}")
    else:
        print("❌ Extraction échouée")

if __name__ == "__main__":
    test_scraper()