"""
Module de gestion Google Sheets pour Rendimo
Utilise l'API Drive pour créer des copies temporaires
"""

import gspread
import streamlit as st
import time
import tempfile
import os
import requests
import uuid
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
        self.backup_data = {}  # Sauvegarde des données modifiées
    
    @staticmethod
    def parse_french_number(value_str):
        """
        Parse un nombre au format français avec espaces insécables, virgules et pourcentages.
        
        Exemples:
        - "7 286,19 €" → 7286.19
        - "2 691,00 €" → 2691.0
        - "5,25%" → 5.25
        - "120,00 €" → 120.0
        """
        if not value_str:
            return 0.0
            
        try:
            # Convertir en string si ce n'est pas déjà le cas
            clean_value = str(value_str)
            
            # Vérifier si c'est un pourcentage
            is_percentage = clean_value.strip().endswith('%')
            
            # Enlever le symbole € et %
            clean_value = clean_value.replace('€', '').replace('%', '').strip()
            
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
            result = float(clean_value)
            
            # Les pourcentages sont déjà au bon format dans les sheets (ex: 5.25 pour 5.25%)
            return result
            
        except (ValueError, TypeError):
            return 0.0
        
    def connect(self):
        """Établit la connexion avec Google Sheets"""
        try:
            st.info("📋 Connexion à Google Sheets...")
            
            # Chemin vers le fichier de credentials
            credentials_path = Path("config/google_sheets_credentials.json")
            
            if not credentials_path.exists():
                st.error(f"❌ Fichier de credentials introuvable : {credentials_path}")
                return False
            
            # Connexion Google Sheets
            self.gc = gspread.service_account(filename=str(credentials_path))
            
            # Se connecter au template principal
            self.sheet = self.gc.open_by_key(GOOGLE_SHEET_ID)
            
            st.success("✅ Connexion réussie à Google Sheets")
            return True
            
        except Exception as e:
            st.error(f"❌ Erreur de connexion : {str(e)}")
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
                type_bien = str(additional_data.get('type_bien', 'Ancien'))
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
            st.error(f"❌ Erreur connexion Google Sheets : {str(e)}")
            return False

    # Méthodes de base pour Google Sheets
    
    def _update_nom_propre_sheet(self, donnees_fiscales):
        """Met à jour la feuille Nom propre"""
        try:
            nom_propre_sheet = self.sheet.worksheet(SHEETS_MAPPING["nom_propre"])
            
            updates = [
                ('D6', float(donnees_fiscales.get('revenu_net', 0))),           # Revenu net global
                ('D7', str(donnees_fiscales.get('situation', 'Célibataire-divorcé-veuf'))),    # Situation familiale
                ('D8', float(donnees_fiscales.get('nombre_enfants', 0)))       # Nombre d'enfants
            ]
            
            for cell, value in updates:
                try:
                    nom_propre_sheet.update(cell, [[value]])
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
            
            # Remplir les associés du formulaire
            for i, associe in enumerate(associes[:4]):  # Maximum 4 associés
                if i < len(colonnes):
                    col = colonnes[i]
                    try:
                        # Part (ligne 8) - conversion en décimal
                        part_decimal = float(associe.get('part', 0)) / 100
                        sci_sheet.update(f'{col}8', [[part_decimal]])
                        
                        # Revenu (ligne 10)
                        revenu = float(associe.get('revenu', 0))
                        sci_sheet.update(f'{col}10', [[revenu]])
                        
                        # Situation familiale (ligne 11)
                        situation = str(associe.get('situation', 'Célibataire-divorcé-veuf'))
                        sci_sheet.update(f'{col}11', [[situation]])
                        
                        # Nombre d'enfants (ligne 12) - spécifique à chaque associé
                        enfants = float(associe.get('enfants', 0))
                        sci_sheet.update(f'{col}12', [[enfants]])
                        
                    except Exception as e:
                        st.warning(f"⚠️ Erreur associé {i+1}: {str(e)}")
            
            # Remplir les associés manquants avec des valeurs par défaut
            nb_associes_formulaire = len(associes)
            for i in range(nb_associes_formulaire, 4):  # De X+1 jusqu'à 4
                if i < len(colonnes):
                    col = colonnes[i]
                    try:
                        # Valeurs par défaut pour les associés manquants
                        sci_sheet.update(f'{col}8', [[0]])  # Part = 0
                        sci_sheet.update(f'{col}10', [[0]])  # Revenu = 0
                        sci_sheet.update(f'{col}11', [['Célibataire-divorcé-veuf']])  # Situation par défaut
                        sci_sheet.update(f'{col}12', [[0]])  # Enfants = 0
                        
                    except Exception as e:
                        st.warning(f"⚠️ Erreur associé par défaut {i+1}: {str(e)}")
            
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

    def get_fiscalite_data(self, type_regime):
        """Récupère les données fiscales selon le régime (nom_propre ou sci)"""
        try:
            if not self.sheet:
                return None
                
            if type_regime == "nom_propre":
                return self._get_nom_propre_fiscalite_data()
            elif type_regime == "sci":
                return self._get_sci_fiscalite_data()
            else:
                return None
                
        except Exception as e:
            st.error(f"❌ Erreur récupération données fiscales : {str(e)}")
            return None
    
    def _get_nom_propre_fiscalite_data(self):
        """Récupère les données fiscales Nom propre"""
        try:
            nom_propre_sheet = self.sheet.worksheet(SHEETS_MAPPING["nom_propre"])
            
            # Rentabilité brut/net de charges (F122:G123)
            rentabilite_range = nom_propre_sheet.get('F122:G123')
            rentabilite_data = []
            
            if len(rentabilite_range) >= 2:
                for i, row in enumerate(rentabilite_range):
                    if len(row) >= 2:
                        label = str(row[0]).strip() if row[0] else f"Ligne {i+1}"
                        value = self.parse_french_number(row[1]) if row[1] else 0
                        if value != 0:
                            rentabilite_data.append({'libelle': label, 'valeur': value})
            
            # Rentabilité nette avec impôts (F124:G127)
            rentabilite_nette_range = nom_propre_sheet.get('F124:G127')
            rentabilite_nette_data = []
            
            for i, row in enumerate(rentabilite_nette_range):
                if len(row) >= 2:
                    label = str(row[0]).strip() if row[0] else f"Ligne {i+1}"
                    value = self.parse_french_number(row[1]) if row[1] else 0
                    if value != 0:
                        rentabilite_nette_data.append({'libelle': label, 'valeur': value})
            
            # Cash mensuel (D130:G131) - libellés en première ligne
            cash_range = nom_propre_sheet.get('D130:G131')
            cash_data = []
            
            if len(cash_range) >= 2:
                labels = cash_range[0]  # Première ligne = libellés
                values = cash_range[1]  # Deuxième ligne = valeurs
                
                for i, (label, value) in enumerate(zip(labels, values)):
                    if label and value:
                        parsed_value = self.parse_french_number(value)
                        if parsed_value != 0:
                            cash_data.append({'libelle': str(label).strip(), 'valeur': parsed_value})
            
            return {
                'rentabilite': rentabilite_data,
                'rentabilite_nette': rentabilite_nette_data,
                'cash_mensuel': cash_data
            }
            
        except Exception as e:
            st.error(f"❌ Erreur données Nom propre : {str(e)}")
            return None
    
    def _get_sci_fiscalite_data(self):
        """Récupère les données fiscales SCI"""
        try:
            sci_sheet = self.sheet.worksheet(SHEETS_MAPPING["sci"])
            
            # Pourcentage de dividendes distribués (D59)
            dividendes_cell = sci_sheet.get('D59')
            dividendes_pct = 0
            if dividendes_cell and len(dividendes_cell) > 0 and len(dividendes_cell[0]) > 0:
                dividendes_pct = self.parse_french_number(dividendes_cell[0][0])
            
            # Cash mensuel par associé (C98:G100)
            cash_range = sci_sheet.get('C98:G100')
            cash_data = []
            
            if len(cash_range) >= 3:
                associes_row = cash_range[0]  # Première ligne = noms associés
                ir_row = cash_range[1]        # Deuxième ligne = SCI à l'IR
                is_row = cash_range[2]        # Troisième ligne = SCI à l'IS
                
                # Ignorer la première colonne C (libellés), commencer à partir de la colonne D (index 1)
                for i in range(1, len(associes_row)):
                    if i < len(ir_row) and i < len(is_row):
                        associe_nom = str(associes_row[i]).strip() if associes_row[i] else f"Associé {i}"
                        ir_value = self.parse_french_number(ir_row[i]) if ir_row[i] else 0
                        is_value = self.parse_french_number(is_row[i]) if is_row[i] else 0
                        
                        if ir_value != 0 or is_value != 0:
                            cash_data.append({
                                'associe': associe_nom,
                                'ir': ir_value,
                                'is': is_value
                            })
            
            return {
                'cash_associes': cash_data,
                'dividendes_pct': dividendes_pct
            }
            
        except Exception as e:
            st.error(f"❌ Erreur données SCI : {str(e)}")
            return None

    def get_plus_value_data(self):
        """Récupère les données de plus-value selon la durée de détention"""
        try:
            if not self.sheet:
                return None
                
            plus_value_sheet = self.sheet.worksheet(SHEETS_MAPPING["plus_value"])
            
            # Durée de détention LIBELLÉS (F25:AL25) - ne pas parser en nombre !
            duree_range = plus_value_sheet.get('F25:AL25')
            # Plus-value après imposition (F36:AL36)
            apres_imposition_range = plus_value_sheet.get('F36:AL36')
            # Plus-value avant imposition (F37:AL37)
            avant_imposition_range = plus_value_sheet.get('F37:AL37')
            
            plus_value_data = []
            
            if duree_range and apres_imposition_range and avant_imposition_range:
                durees = duree_range[0] if duree_range else []
                apres_values = apres_imposition_range[0] if apres_imposition_range else []
                avant_values = avant_imposition_range[0] if avant_imposition_range else []
                
                for i, duree in enumerate(durees):
                    if duree and i < len(apres_values) and i < len(avant_values):
                        try:
                            # Garder la durée comme libellé ("+1 ans", "+2 ans", etc.)
                            duree_label = str(duree).strip()
                            apres_val = self.parse_french_number(apres_values[i]) if apres_values[i] else 0
                            avant_val = self.parse_french_number(avant_values[i]) if avant_values[i] else 0
                            
                            # Ne garder que si au moins une valeur n'est pas zéro et que le libellé n'est pas vide
                            if duree_label and (apres_val != 0 or avant_val != 0):
                                plus_value_data.append({
                                    'duree': duree_label,  # Libellé au lieu de nombre
                                    'apres_imposition': apres_val,
                                    'avant_imposition': avant_val
                                })
                        except Exception:
                            continue
            
            return plus_value_data
            
        except Exception as e:
            st.error(f"❌ Erreur données plus-value : {str(e)}")
            return None

    def get_amortissement_data(self):
        """Récupère les données d'amortissement"""
        try:
            if not self.sheet:
                return None
                
            amortissement_sheet = self.sheet.worksheet(SHEETS_MAPPING["amortissement"])
            
            # Coût total du crédit (K8)
            cout_total_cell = amortissement_sheet.get('K8')
            cout_total = 0
            if cout_total_cell and len(cout_total_cell) > 0 and len(cout_total_cell[0]) > 0:
                cout_total = self.parse_french_number(cout_total_cell[0][0])
            
            # Mensualité hors assurance (E13) et avec assurance (F13)
            mensualite_range = amortissement_sheet.get('E13:F13')
            mensualite_hors = 0
            mensualite_avec = 0
            if mensualite_range and len(mensualite_range) > 0:
                if len(mensualite_range[0]) > 0:
                    mensualite_hors = self.parse_french_number(mensualite_range[0][0])
                if len(mensualite_range[0]) > 1:
                    mensualite_avec = self.parse_french_number(mensualite_range[0][1])
            
            # Données tableau amortissement (C13:C253, G13:G253, H13:H253)
            # Limiter à 120 mois pour éviter trop de données
            mois_range = amortissement_sheet.get('C13:C133')  # 10 ans max
            interets_range = amortissement_sheet.get('G13:G133')
            capital_range = amortissement_sheet.get('H13:H133')
            
            amortissement_data = []
            
            if mois_range and interets_range and capital_range:
                for i in range(min(len(mois_range), len(interets_range), len(capital_range))):
                    if (mois_range[i] and len(mois_range[i]) > 0 and 
                        interets_range[i] and len(interets_range[i]) > 0 and
                        capital_range[i] and len(capital_range[i]) > 0):
                        
                        try:
                            mois = str(mois_range[i][0]).strip()
                            interets = self.parse_french_number(interets_range[i][0])
                            capital = self.parse_french_number(capital_range[i][0])
                            
                            if mois and (interets != 0 or capital != 0):
                                amortissement_data.append({
                                    'mois': mois,
                                    'interets': interets,
                                    'capital': capital
                                })
                        except Exception:
                            continue
            
            return {
                'cout_total': cout_total,
                'mensualite_hors_assurance': mensualite_hors,
                'mensualite_avec_assurance': mensualite_avec,
                'tableau': amortissement_data
            }
            
        except Exception as e:
            st.error(f"❌ Erreur données amortissement : {str(e)}")
            return None
        except Exception as e:
            st.error(f"❌ Erreur récupération charges : {str(e)}")
            return None
    
    def export_to_excel(self, property_data):
        """Génère un lien de téléchargement du template Google Sheets"""
        try:
            st.info("📤 Préparation du téléchargement...")
            
            # Utiliser le template principal
            download_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=xlsx"
            
            # Nom du fichier pour le téléchargement
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"Rendimo_Analyse_{property_data.get('city', 'Bien')}_{timestamp}.xlsx"
            
            st.markdown("---")
            st.markdown("### 📥 **Télécharger votre analyse complète**")
            
            st.markdown(f"""
            🎯 **Votre analyse Google Sheets est prête !**
            
            ✅ **Template modifié** : Avec vos données personnalisées  
            ✅ **Formatage complet** : Couleurs, bordures, formules  
            ✅ **Calculs à jour** : Tous les résultats financiers  
            ✅ **Données intégrées** : Basées sur votre formulaire  
            
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
                
                **⚠️ Important :** Le fichier téléchargé contient les dernières données modifiées.
                Tous les utilisateurs voient les mêmes données car ils utilisent le même template.
                """)
            
            # Retourner l'URL pour d'autres usages si nécessaire
            return download_url
            
        except Exception as e:
            st.error(f"❌ Erreur génération lien téléchargement : {str(e)}")
            return None