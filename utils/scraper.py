"""
Module de scraping robuste pour LeBonCoin avec parsing JSON structuré
Version améliorée pour Rendimo

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
    """Scraper robuste pour LeBonCoin avec données structurées JSON"""
    
    def __init__(self):
        """Initialise le scraper avec headers modernes"""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8',
            'Accept-Encoding': 'gzip, deflate',  # Removed 'br' to avoid brotli dependency
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
        """Valide une URL LeBonCoin (élargie)"""
        try:
            if 'leboncoin.fr' not in url:
                return False
            return any(pattern in url for pattern in ['immobilier', 'ventes_immobilieres', 'ad'])
        except:
            return False
    
    def extract_property_data(self, url: str) -> Optional[Dict]:
        """Extrait les données d'une annonce avec parsing JSON prioritaire"""
        if not self.validate_url(url):
            logger.error("URL invalide")
            return None
        
        try:
            logger.info(f"Extraction: {url}")
            
            # Récupération avec retry
            response = self._get_page_with_retry(url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.content, 'lxml')
            logger.info("HTML parsé")
            
            # Initialisation du dict de sortie avec toutes les clés attendues
            property_data = {
                'title': '',
                'price': 0,
                'surface': 0,
                'rooms': 0,
                'bedrooms': 0,
                'city': '',
                'postal_code': '',
                'land_surface': 0,
                'year_built': 0,
                'energy_class': '',
                'ges': '',
                'property_type': '',
                'description': '',
                'reference': '',
                'price_per_m2': 0,
                'source_url': url,
                'extraction_date': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Étape 1: Parsing des données JSON structurées (prioritaire)
            ld_json_data = self._parse_ld_json(soup)
            property_data.update(ld_json_data)
            
            next_data = self._parse_next_data(soup)
            property_data.update(next_data)
            
            # Étape 2: Fallback DOM pour les champs manquants
            if not property_data['title']:
                property_data['title'] = self._extract_title(soup)
            if not property_data['price']:
                property_data['price'] = self._extract_price(soup)
            if not property_data['surface']:
                property_data['surface'] = self._extract_surface(soup)
            if not property_data['rooms']:
                property_data['rooms'] = self._extract_rooms(soup)
            if not property_data['city']:
                property_data['city'] = self._extract_city(soup)
            if not property_data['property_type']:
                property_data['property_type'] = self._extract_type(soup)
            if not property_data['description']:
                property_data['description'] = self._extract_description(soup)
            
            # Calcul du prix au m² si possible
            if property_data['price'] > 0 and property_data['surface'] > 0:
                property_data['price_per_m2'] = round(property_data['price'] / property_data['surface'], 2)
            
            # Log des champs manquants (info seulement)
            missing_fields = []
            for key in ['price', 'surface', 'city']:
                if not property_data.get(key):
                    missing_fields.append(key)
            
            if missing_fields:
                logger.info(f"Champs manquants: {', '.join(missing_fields)}")
            
            # Retourner même si certains champs manquent
            logger.info(f"Extraction complétée: {property_data.get('title', 'Sans titre')}")
            return property_data
            
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
    
    def _parse_ld_json(self, soup: BeautifulSoup) -> Dict:
        """Parse les données JSON-LD structurées"""
        data = {}
        
        try:
            # Recherche tous les scripts JSON-LD
            ld_scripts = soup.find_all('script', {'type': 'application/ld+json'})
            
            for script in ld_scripts:
                if not script.string:
                    continue
                    
                try:
                    json_data = json.loads(script.string)
                    
                    # Structure JSON-LD pour immobilier
                    if isinstance(json_data, dict):
                        # Titre
                        if json_data.get('name') and not data.get('title'):
                            data['title'] = json_data['name']
                        
                        # Prix
                        if 'offers' in json_data and not data.get('price'):
                            offers = json_data['offers']
                            if isinstance(offers, dict) and 'price' in offers:
                                try:
                                    data['price'] = int(float(offers['price']))
                                except (ValueError, TypeError):
                                    pass
                        
                        # Adresse
                        if 'address' in json_data:
                            address = json_data['address']
                            if isinstance(address, dict):
                                if 'addressLocality' in address and not data.get('city'):
                                    data['city'] = address['addressLocality']
                                if 'postalCode' in address and not data.get('postal_code'):
                                    data['postal_code'] = address['postalCode']
                        
                        # Surface
                        if 'floorSize' in json_data and not data.get('surface'):
                            try:
                                # floorSize peut être "85 m²" ou juste "85"
                                floor_size = str(json_data['floorSize'])
                                surface_match = re.search(r'(\d+)', floor_size)
                                if surface_match:
                                    data['surface'] = int(surface_match.group(1))
                            except (ValueError, TypeError):
                                pass
                        
                        # Pièces
                        if 'numberOfRooms' in json_data and not data.get('rooms'):
                            try:
                                data['rooms'] = int(json_data['numberOfRooms'])
                            except (ValueError, TypeError):
                                pass
                        
                        # Chambres
                        if 'numberOfBedrooms' in json_data and not data.get('bedrooms'):
                            try:
                                data['bedrooms'] = int(json_data['numberOfBedrooms'])
                            except (ValueError, TypeError):
                                pass
                        
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            logger.debug(f"Erreur parsing JSON-LD: {e}")
        
        return data
    
    def _parse_next_data(self, soup: BeautifulSoup) -> Dict:
        """Parse les données __NEXT_DATA__ de Next.js"""
        data = {}
        
        try:
            # Recherche le script __NEXT_DATA__
            next_script = soup.find('script', {'id': '__NEXT_DATA__'})
            if not next_script or not next_script.string:
                # Essai avec id="___NEXT_DATA__" (triple underscore)
                next_script = soup.find('script', {'id': '___NEXT_DATA__'})
            
            if next_script and next_script.string:
                try:
                    next_data = json.loads(next_script.string)
                    
                    # Navigation: props -> pageProps -> ad
                    ad_data = None
                    if 'props' in next_data:
                        props = next_data['props']
                        if 'pageProps' in props:
                            page_props = props['pageProps']
                            if 'ad' in page_props:
                                ad_data = page_props['ad']
                    
                    if ad_data and isinstance(ad_data, dict):
                        # Titre/Subject
                        if 'subject' in ad_data and not data.get('title'):
                            data['title'] = ad_data['subject']
                        
                        # Prix
                        if 'price' in ad_data and not data.get('price'):
                            price_obj = ad_data['price']
                            if isinstance(price_obj, dict) and 'value' in price_obj:
                                try:
                                    data['price'] = int(price_obj['value'])
                                except (ValueError, TypeError):
                                    pass
                        
                        # Localisation
                        if 'location' in ad_data:
                            location = ad_data['location']
                            if isinstance(location, dict):
                                if 'city' in location and not data.get('city'):
                                    data['city'] = location['city']
                                if 'zipcode' in location and not data.get('postal_code'):
                                    data['postal_code'] = location['zipcode']
                        
                        # ID/Référence
                        if 'id' in ad_data and not data.get('reference'):
                            data['reference'] = str(ad_data['id'])
                        
                        # Attributs (square, rooms, bedrooms, etc.)
                        if 'attributes' in ad_data:
                            attributes = ad_data['attributes']
                            if isinstance(attributes, list):
                                for attr in attributes:
                                    if not isinstance(attr, dict):
                                        continue
                                    
                                    key = attr.get('key', '').lower()
                                    value = attr.get('value')
                                    
                                    if key == 'square' and not data.get('surface'):
                                        try:
                                            data['surface'] = int(value)
                                        except (ValueError, TypeError):
                                            pass
                                    elif key == 'rooms' and not data.get('rooms'):
                                        try:
                                            data['rooms'] = int(value)
                                        except (ValueError, TypeError):
                                            pass
                                    elif key == 'bedrooms' and not data.get('bedrooms'):
                                        try:
                                            data['bedrooms'] = int(value)
                                        except (ValueError, TypeError):
                                            pass
                                    elif key == 'land' and not data.get('land_surface'):
                                        try:
                                            data['land_surface'] = int(value)
                                        except (ValueError, TypeError):
                                            pass
                                    elif key == 'year' and not data.get('year_built'):
                                        try:
                                            data['year_built'] = int(value)
                                        except (ValueError, TypeError):
                                            pass
                                    elif key == 'energy_rate' and not data.get('energy_class'):
                                        data['energy_class'] = str(value)
                                    elif key == 'ges' and not data.get('ges'):
                                        data['ges'] = str(value)
                        
                except json.JSONDecodeError as e:
                    logger.debug(f"Erreur parsing __NEXT_DATA__: {e}")
                    
        except Exception as e:
            logger.debug(f"Erreur parsing Next.js data: {e}")
        
        return data
    
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
        """Extrait la ville (conserve le nom complet)"""
        selectors = [
            '[data-qa-id*="location"]',
            '.styles_location__3s1s8',
            '[class*="location"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                location_text = element.get_text(strip=True)
                if location_text:
                    # Nettoyer mais conserver les noms composés comme "La Rochelle"
                    # Retirer seulement le code postal final si présent
                    location_clean = re.sub(r'\s+\d{5}$', '', location_text).strip()
                    return location_clean if location_clean else location_text
        
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
    """Test du scraper avec nouvelles fonctionnalités"""
    scraper = LeBonCoinScraper()
    test_url = "https://www.leboncoin.fr/ventes_immobilieres/test"
    
    print("🔍 Test scraper robuste avec parsing JSON")
    print(f"URL valide: {scraper.validate_url(test_url)}")
    
    # Test de validation élargie
    test_urls = [
        "https://www.leboncoin.fr/ad/immobilier/123456",
        "https://www.leboncoin.fr/ventes_immobilieres/789",
        "https://www.leboncoin.fr/immobilier/987654",
        "https://www.autres-sites.fr/test"
    ]
    
    print("\n📋 Tests de validation URL:")
    for url in test_urls:
        is_valid = scraper.validate_url(url)
        print(f"  {url}: {'✅' if is_valid else '❌'}")
    
    print(f"\n🎯 Test extraction sur: {test_url}")
    data = scraper.extract_property_data(test_url)
    if data:
        print("✅ Données extraites:")
        for key, value in data.items():
            if value:  # Afficher seulement les champs non vides
                print(f"  {key}: {value}")
        
        # Afficher le prix au m² si calculable
        if data.get('price_per_m2'):
            print(f"\n💰 Prix au m²: {data['price_per_m2']}€")
    else:
        print("❌ Extraction échouée")

if __name__ == "__main__":
    test_scraper()