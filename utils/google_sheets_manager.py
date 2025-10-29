"""
Module de gestion Google Sheets pour Rendimo
Remplace la gestion Excel par Google Sheets API
"""

import gspread
import streamlit as st
import time
import tempfile
import os
import requests
from pathlib import Path
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
import pandas as pd

from config.google_sheets_config import (
    GOOGLE_SHEET_ID, 
    GOOGLE_SHEET_NAME,
    SHEETS_MAPPING,
    CELL_MAPPING,
    GOOGLE_SCOPES
)

class GoogleSheetsManager:
    """Gestionnaire pour les opérations Google Sheets"""
    
    def __init__(self):
        self.gc = None
        self.sheet = None
    
    @staticmethod
    def parse_french_number(value_str):
        """
        Parse un nombre au format français avec espaces insécables et virgules.
        
        Exemples:
        - "7 286,19 €" → 7286.19
        - "2 691,00 €" → 2691.0
        - "120,00 €" → 120.0
        """
        if not value_str:
            return 0.0
            
        try:
            # Convertir en string si ce n'est pas déjà le cas
            clean_value = str(value_str)
            
            # Enlever le symbole €
            clean_value = clean_value.replace('€', '').strip()
            
            # Enlever TOUS les types d'espaces possibles
            spaces_to_remove = [
                ' ',        # Espace normal
                '\u00A0',   # Espace insécable (non-breaking space)
                '\u202F',   # Espace insécable étroit (narrow no-break space)
                '\u2009',   # Espace fine (thin space)
                '\u2008',   # Espace ponctuation (punctuation space)
                '\u200A',   # Espace ultra-fine (hair space)
            ]
            
            for space in spaces_to_remove:
                clean_value = clean_value.replace(space, '')
            
            # Remplacer la virgule française par un point décimal
            clean_value = clean_value.replace(',', '.')
            
            # Convertir en float
            return float(clean_value)
            
        except (ValueError, TypeError):
            return 0.0
        
    def connect(self):
        """Connexion à Google Sheets avec service account"""
        try:
            st.info("📋 Connexion à Google Sheets...")
            
            # Chemin vers le fichier de credentials
            credentials_path = Path("config/google_sheets_credentials.json")
            
            if not credentials_path.exists():
                st.error("❌ Fichier de credentials Google Sheets non trouvé")
                st.info("� Veuillez suivre les instructions dans config/README_Google_Sheets_Setup.md")
                return False
            
            # Connexion avec le service account
            self.gc = gspread.service_account(filename=str(credentials_path))
            self.sheet = self.gc.open_by_key(GOOGLE_SHEET_ID)
            
            return True
            
        except FileNotFoundError:
            st.error("❌ Fichier de credentials non trouvé")
            st.info("💡 Veuillez configurer les credentials Google Sheets (voir config/README_Google_Sheets_Setup.md)")
            return False
        except gspread.SpreadsheetNotFound:
            st.error("❌ Google Sheet non trouvé ou accès refusé")
            st.info("💡 Vérifiez que le service account a accès au Google Sheet")
            return False
        except Exception as e:
            st.error(f"❌ Erreur connexion Google Sheets : {str(e)}")
            st.info("💡 Vérifiez que le service account a accès au fichier Google Sheets")
            return False
    
    def update_property_data(self, property_data, additional_data):
        """Met à jour les données du bien dans Google Sheets"""
        try:
            if not self.sheet:
                st.error("❌ Pas de connexion Google Sheets")
                return False
            
            # ============================================================================
            # FEUILLE "FRAIS DE NOTAIRE"
            # ============================================================================
            try:
                frais_sheet = self.sheet.worksheet(SHEETS_MAPPING["frais_notaire"])
                
                # Prix du bien (I3) - S'assurer que c'est un nombre
                prix = property_data.get('price', 0)
                if prix:
                    frais_sheet.update('I3', [[prix]])  # Format liste de listes
                
                # Type de bien (F3) - S'assurer que c'est du texte
                type_bien = str(additional_data.get('type_bien', 'Occasion'))
                frais_sheet.update('F3', [[type_bien]])  # Format liste de listes
                
            except Exception as e:
                st.warning(f"⚠️ Erreur feuille 'Frais de notaire': {str(e)}")
            
            # ============================================================================
            # FEUILLE "COÛTS ET RENDEMENT"
            # ============================================================================
            try:
                cout_sheet = self.sheet.worksheet(SHEETS_MAPPING["cout_rendement"])
                
                # Préparer les données avec format correct
                updates = [
                    ('D7', float(additional_data.get('loyer_hc', 0))),
                    ('D8', float(additional_data.get('loyer_cc', 0))),
                    ('D9', float(property_data.get('surface', 0))),
                    ('D14', str(additional_data.get('utilise_pret', 'Oui'))),
                    ('D15', float(additional_data.get('duree_pret', 20))),
                    ('D16', float(additional_data.get('apport', 0))),
                    ('D17', float(additional_data.get('taux_pret', 4.0)) / 100),  # Conversion en décimal
                    ('D21', float(additional_data.get('cout_renovation', 0))),
                    ('D22', float(additional_data.get('cout_construction', 0)))
                ]
                
                # Mise à jour une par une avec format correct
                for cell, value in updates:
                    try:
                        cout_sheet.update(cell, [[value]])  # Format liste de listes
                    except Exception as e:
                        st.warning(f"⚠️ Erreur mise à jour {cell}: {str(e)}")
                
            except Exception as e:
                st.warning(f"⚠️ Erreur feuille 'Coûts et rendement': {str(e)}")
            
            # ============================================================================
            # FEUILLES FISCALES (NOM PROPRE / SCI)
            # ============================================================================
            donnees_fiscales = additional_data.get('donnees_fiscales', {})
            
            if donnees_fiscales.get('type') == 'nom_propre':
                self._update_nom_propre_sheet(donnees_fiscales)
            elif donnees_fiscales.get('type') == 'sci':
                self._update_sci_sheet(donnees_fiscales)
            
            # ============================================================================
            # PLUS VALUE
            # ============================================================================
            try:
                plus_value_sheet = self.sheet.worksheet(SHEETS_MAPPING["plus_value"])
                estimation = float(additional_data.get('estimation_revente', 0))
                plus_value_sheet.update('E7', [[estimation]])  # Format liste de listes
                
            except Exception as e:
                st.warning(f"⚠️ Erreur feuille 'Plus value': {str(e)}")
            
            # Attendre que Google Sheets recalcule
            time.sleep(2)  # Attendre pour le recalcul
            
            return True
            
        except Exception as e:
            st.error(f"❌ Erreur mise à jour Google Sheets : {str(e)}")
            return False
    
    def _update_nom_propre_sheet(self, donnees_fiscales):
        """Met à jour la feuille Nom propre"""
        try:
            nom_propre_sheet = self.sheet.worksheet(SHEETS_MAPPING["nom_propre"])
            
            updates = [
                ('D6', float(donnees_fiscales.get('revenu_foyer', 0))),
                ('D7', str(donnees_fiscales.get('situation_familiale', 'Célibataire-divorcé-veuf'))),
                ('D8', float(donnees_fiscales.get('nombre_enfants', 0)))
            ]
            
            for cell, value in updates:
                try:
                    nom_propre_sheet.update(cell, [[value]])  # Format liste de listes
                except Exception as e:
                    st.warning(f"⚠️ Erreur mise à jour {cell}: {str(e)}")
                
        except Exception as e:
            st.warning(f"⚠️ Erreur feuille 'Nom propre': {str(e)}")
    
    def _update_sci_sheet(self, donnees_fiscales):
        """Met à jour la feuille SCI"""
        try:
            sci_sheet = self.sheet.worksheet(SHEETS_MAPPING["sci"])
            
            # Capital SCI
            capital = float(donnees_fiscales.get('capital', 1000))
            sci_sheet.update('D6', [[capital]])
            
            # Données des associés (colonnes D, E, F, G)
            associes = donnees_fiscales.get('associes', [])
            colonnes = ['D', 'E', 'F', 'G']
            
            for i, associe in enumerate(associes[:4]):  # Maximum 4 associés
                if i < len(colonnes):
                    col = colonnes[i]
                    try:
                        # Part (ligne 8) - conversion en décimal
                        part_decimal = float(associe.get('part', 0)) / 100
                        sci_sheet.update(f'{col}8', [[part_decimal]])
                        
                        # Situation (ligne 9) 
                        situation = str(associe.get('situation', 'Célibataire-divorcé-veuf'))
                        sci_sheet.update(f'{col}9', [[situation]])
                        
                        # Revenu (ligne 10)
                        revenu = float(associe.get('revenu', 0))
                        sci_sheet.update(f'{col}10', [[revenu]])
                        
                        # Enfants (ligne 11)
                        enfants = float(associe.get('enfants', 0))
                        sci_sheet.update(f'{col}11', [[enfants]])
                        
                    except Exception as e:
                        st.warning(f"⚠️ Erreur associé {i+1}: {str(e)}")
            
        except Exception as e:
            st.warning(f"⚠️ Erreur feuille 'SCI': {str(e)}")
    
    def get_charges_data(self):
        """Récupère les données des charges pour les indicateurs"""
        try:
            if not self.sheet:
                return None
                
            cout_sheet = self.sheet.worksheet(SHEETS_MAPPING["cout_rendement"])
            
            # Récupérer les libellés et valeurs (F18:G27)
            charges_range = cout_sheet.get('F18:G27')
            charges_data = []
            
            for i, row in enumerate(charges_range):
                if len(row) >= 2:  # S'assurer qu'il y a au moins 2 colonnes
                    label = row[0] if len(row) > 0 else ""
                    value = row[1] if len(row) > 1 else ""
                    
                    # Nettoyer et valider
                    if label and str(label).strip():
                        try:
                            # Utiliser la fonction de parsing français
                            value_float = self.parse_french_number(value)
                            
                            if value_float > 0:
                                charges_data.append({
                                    'libelle': str(label).strip(),
                                    'valeur': value_float
                                })
                                
                        except Exception:
                            continue
            
            return charges_data
            
        except Exception as e:
            st.error(f"❌ Erreur récupération charges : {str(e)}")
            return None
        except Exception as e:
            st.error(f"❌ Erreur récupération charges : {str(e)}")
            return None
    
    def export_to_excel(self, property_data):
        """Génère un lien de téléchargement du Google Sheet avec mise en forme complète"""
        try:
            st.info("📤 Préparation du téléchargement Google Sheets...")
            
            # ============================================================================
            # MÉTHODE : LIEN DE TÉLÉCHARGEMENT DIRECT GOOGLE SHEETS
            # ============================================================================
            
            # URL de téléchargement direct Excel de Google Sheets
            # Cette méthode préserve TOUT le formatage (couleurs, images, formules, etc.)
            download_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=xlsx"
            
            # Nom du fichier pour le téléchargement
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"Rendimo_Analyse_{property_data.get('city', 'Bien')}_{timestamp}.xlsx"
            
            # ============================================================================
            # BOUTON DE TÉLÉCHARGEMENT STREAMLIT
            # ============================================================================
            
            st.markdown("---")
            st.markdown("### 📥 **Télécharger votre analyse complète**")
            
            st.markdown(f"""
            🎯 **Votre Google Sheet personnalisé est prêt !**
            
            ✅ **Formatage complet** : Couleurs, bordures, images  
            ✅ **Formules calculées** : Tous les résultats financiers  
            ✅ **Données à jour** : Basées sur votre formulaire  
            
            👇 **Cliquez sur le bouton ci-dessous pour télécharger :**
            """)
            
            # Bouton de téléchargement avec lien direct
            st.markdown(f"""
            <div style="text-align: center; margin: 20px 0;">
                <a href="{download_url}" download="{filename}" target="_blank">
                    <button style="
                        background-color: #4CAF50;
                        color: white;
                        padding: 15px 32px;
                        text-align: center;
                        text-decoration: none;
                        display: inline-block;
                        font-size: 16px;
                        margin: 4px 2px;
                        cursor: pointer;
                        border: none;
                        border-radius: 8px;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                    ">
                        📊 Télécharger l'Excel avec mise en forme complète
                    </button>
                </a>
            </div>
            """, unsafe_allow_html=True)
            
            # Lien alternatif en cas de problème
            st.markdown(f"""
            **🔗 Lien direct (si le bouton ne fonctionne pas) :**  
            [`{filename}`]({download_url})
            """)
            
            # ============================================================================
            # INFORMATIONS ADDITIONNELLES
            # ============================================================================
            
            with st.expander("ℹ️ Informations sur le téléchargement"):
                st.markdown(f"""
                **📋 Détails du fichier :**
                - **Nom :** `{filename}`
                - **Format :** Excel (.xlsx)
                - **Source :** Google Sheets avec formules calculées
                - **Contenu :** Toutes les feuilles avec vos données
                
                **🎨 Formatage préservé :**
                - ✅ Couleurs des cellules
                - ✅ Bordures et styles
                - ✅ Images et graphiques
                - ✅ Mise en forme conditionnelle
                - ✅ Formules et calculs
                
                **💡 Note :** Le téléchargement s'effectue directement depuis Google Sheets, 
                garantissant que vous obtenez exactement la même mise en forme que votre template !
                """)
            
            # Retourner l'URL pour d'autres usages si nécessaire
            return download_url
            
        except Exception as e:
            st.error(f"❌ Erreur génération lien téléchargement : {str(e)}")
            return None