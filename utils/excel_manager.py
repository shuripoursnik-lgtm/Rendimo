"""
Gestionnaire Excel pour Rendimo
Utilise OpenPyXL pour modifier le template Excel local
"""

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
import streamlit as st
from openpyxl import load_workbook
import uuid

class ExcelManager:
    """Gestionnaire pour les opérations Excel avec OpenPyXL"""
    
    def __init__(self):
        # Chemin relatif au projet (fonctionne en local ET en cloud)
        self.template_path = Path(__file__).parent.parent / "Template Excel" / "Rendimmo - Rentabilité.xlsx"
        self.temp_file_path = None
        self.workbook = None
        
    def create_temporary_copy(self, property_data):
        """Crée une copie temporaire du template Excel"""
        try:
            st.info("📋 Création d'une copie Excel temporaire...")
            
            # Vérifier que le template existe
            if not self.template_path.exists():
                st.error(f"❌ Template Excel introuvable : {self.template_path}")
                return False
            
            # Générer un nom unique pour la copie temporaire
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            session_id = str(uuid.uuid4())[:8]
            city = property_data.get('city', 'Bien').replace(' ', '_')
            
            temp_filename = f"Rendimo_{city}_{timestamp}_{session_id}.xlsx"
            
            # Créer le fichier temporaire sur le serveur (local ou cloud)
            temp_dir = Path(tempfile.gettempdir()) / "rendimo_temp"
            temp_dir.mkdir(exist_ok=True)
            
            self.temp_file_path = temp_dir / temp_filename
            
            # Copier le template vers le fichier temporaire
            shutil.copy2(self.template_path, self.temp_file_path)
            
            # Charger le workbook
            self.workbook = load_workbook(self.temp_file_path)
            
            st.success(f"✅ Copie Excel temporaire créée !")
            st.info(f"📄 Fichier : {temp_filename}")
            
            return True
            
        except Exception as e:
            st.error(f"❌ Erreur création copie Excel : {str(e)}")
            return False
    
    def update_property_data(self, property_data, additional_data):
        """Met à jour les données du bien dans le fichier Excel"""
        try:
            if not self.workbook:
                st.error("❌ Aucun fichier Excel ouvert")
                return False
            
            st.info("📝 Mise à jour des données dans Excel...")
            
            # ============================================================================
            # FEUILLE "FRAIS DE NOTAIRE"
            # ============================================================================
            try:
                frais_sheet = self.workbook["Frais de notaire"]
                
                # Prix du bien (I3)
                prix = property_data.get('price', 0)
                if prix:
                    frais_sheet['I3'] = prix
                
                # Type de bien (F3)
                type_bien = additional_data.get('type_bien', 'Ancien')
                frais_sheet['F3'] = type_bien
                
            except Exception as e:
                st.warning(f"⚠️ Erreur feuille 'Frais de notaire': {str(e)}")
            
            # ============================================================================
            # FEUILLE "COÛTS ET RENDEMENT"
            # ============================================================================
            try:
                cout_sheet = self.workbook["Coûts et rendement"]
                
                # Données de location et bien
                updates = [
                    ('D7', float(additional_data.get('loyer_hc', 0)), 'Loyer HC'),
                    ('D8', float(additional_data.get('loyer_cc', 0)), 'Loyer CC'),
                    ('D9', float(property_data.get('surface', 0)), 'Surface'),
                    ('D14', additional_data.get('utilise_pret', 'Oui'), 'Utilise prêt'),
                    ('D15', float(additional_data.get('duree_pret', 20)), 'Durée prêt'),
                    ('D16', float(additional_data.get('apport', 0)), 'Apport'),
                    ('D17', float(additional_data.get('taux_pret', 4.0)) / 100, 'Taux prêt'),
                    ('D21', float(additional_data.get('cout_renovation', 0)), 'Coût rénovation'),
                    ('D22', float(additional_data.get('cout_construction', 0)), 'Coût construction')
                ]
                
                for cell, value, description in updates:
                    try:
                        cout_sheet[cell] = value
                    except Exception as e:
                        st.warning(f"⚠️ Erreur mise à jour {cell} ({description}): {str(e)}")
                
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
                plus_value_sheet = self.workbook["Plus value"]
                estimation = float(additional_data.get('estimation_revente', 0))
                plus_value_sheet['E7'] = estimation
                
            except Exception as e:
                st.warning(f"⚠️ Erreur feuille 'Plus value': {str(e)}")
            
            # Sauvegarder les modifications
            self.workbook.save(self.temp_file_path)
            st.success("✅ Données Excel mises à jour avec succès !")
            
            return True
            
        except Exception as e:
            st.error(f"❌ Erreur mise à jour Excel : {str(e)}")
            return False
    
    def _update_nom_propre_sheet(self, donnees_fiscales):
        """Met à jour la feuille Nom propre"""
        try:
            nom_propre_sheet = self.workbook["Nom propre - Fiscalité"]
            
            updates = [
                ('D6', float(donnees_fiscales.get('revenu_net', 0)), 'Revenu net global'),
                ('D7', donnees_fiscales.get('situation', 'Célibataire-divorcé-veuf'), 'Situation familiale'),
                ('D8', float(donnees_fiscales.get('nombre_enfants', 0)), 'Nombre d\'enfants')
            ]
            
            for cell, value, description in updates:
                try:
                    nom_propre_sheet[cell] = value
                except Exception as e:
                    st.warning(f"⚠️ Erreur {description}: {str(e)}")
                
        except Exception as e:
            st.warning(f"⚠️ Erreur feuille 'Nom propre': {str(e)}")
    
    def _update_sci_sheet(self, donnees_fiscales):
        """Met à jour la feuille SCI"""
        try:
            sci_sheet = self.workbook["SCI"]
            
            # Capital SCI
            capital = float(donnees_fiscales.get('capital', 1000))
            sci_sheet['D6'] = capital
            
            # Données des associés (colonnes D, E, F, G)
            associes = donnees_fiscales.get('associes', [])
            colonnes = ['D', 'E', 'F', 'G']
            
            for i, associe in enumerate(associes[:4]):  # Maximum 4 associés
                if i < len(colonnes):
                    col = colonnes[i]
                    try:
                        # Part (ligne 8) - conversion en décimal
                        part_decimal = float(associe.get('part', 0)) / 100
                        sci_sheet[f'{col}8'] = part_decimal
                        
                        # Revenu (ligne 10)
                        revenu = float(associe.get('revenu', 0))
                        sci_sheet[f'{col}10'] = revenu
                        
                        # Situation familiale (ligne 11)
                        situation = associe.get('situation', 'Célibataire-divorcé-veuf')
                        sci_sheet[f'{col}11'] = situation
                        
                        # Nombre d'enfants (ligne 12)
                        enfants = float(associe.get('enfants', 0))
                        sci_sheet[f'{col}12'] = enfants
                        
                    except Exception as e:
                        st.warning(f"⚠️ Erreur associé {i+1}: {str(e)}")
            
        except Exception as e:
            st.warning(f"⚠️ Erreur feuille 'SCI': {str(e)}")
    
    def get_download_info(self, property_data):
        """Retourne les informations pour le téléchargement"""
        try:
            if not self.temp_file_path or not self.temp_file_path.exists():
                return None
            
            # Nom de fichier pour le téléchargement
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            download_filename = f"Rendimo_Analyse_{property_data.get('city', 'Bien')}_{timestamp}.xlsx"
            
            return {
                'file_path': self.temp_file_path,
                'filename': download_filename,
                'size': self.temp_file_path.stat().st_size
            }
            
        except Exception as e:
            st.error(f"❌ Erreur informations téléchargement : {str(e)}")
            return None
    
    def create_download_button(self, property_data):
        """Crée un bouton de téléchargement Streamlit (HORS formulaire)"""
        try:
            download_info = self.get_download_info(property_data)
            if not download_info:
                st.error("❌ Impossible de préparer le téléchargement")
                return False
            
            # Lire le fichier pour le téléchargement
            with open(download_info['file_path'], 'rb') as file:
                file_data = file.read()
            
            st.markdown("### 📥 **Télécharger votre analyse Excel**")
            
            # Informations sur le fichier
            file_size_mb = download_info['size'] / (1024 * 1024)
            st.markdown(f"""
            🎯 **Votre fichier Excel personnalisé est prêt !**
            
            ✅ **Fichier modifié** : Avec toutes vos données  
            ✅ **Formules calculées** : Résultats financiers à jour  
            ✅ **Formatage préservé** : Couleurs, bordures, graphiques  
            ✅ **Taille** : {file_size_mb:.1f} MB  
            """)
            
            # Bouton de téléchargement Streamlit (HORS de tout formulaire)
            download_clicked = st.download_button(
                label="📊 Télécharger l'analyse Excel complète",
                data=file_data,
                file_name=download_info['filename'],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Télécharge votre analyse personnalisée au format Excel",
                key=f"download_{property_data.get('city', 'bien')}_{int(datetime.now().timestamp())}"
            )
            
            if download_clicked:
                st.success("✅ Téléchargement initié !")
                
            return True
            
        except Exception as e:
            st.error(f"❌ Erreur création bouton téléchargement : {str(e)}")
            return False
    
    def cleanup(self):
        """Nettoie le fichier temporaire"""
        try:
            if self.temp_file_path and self.temp_file_path.exists():
                self.temp_file_path.unlink()
                st.info(f"🗑️ Fichier temporaire supprimé")
                return True
            return True
        except Exception as e:
            st.warning(f"⚠️ Erreur suppression fichier temporaire : {str(e)}")
            return False
    
    def __del__(self):
        """Destructeur - nettoie automatiquement"""
        self.cleanup()

def generate_excel_analysis(property_data, additional_data):
    """
    Fonction principale pour générer l'analyse Excel
    Retourne le gestionnaire Excel pour créer le bouton de téléchargement HORS formulaire
    """
    try:
        st.info("🚀 Génération de l'analyse Excel...")
        
        # Créer le gestionnaire Excel
        excel_manager = ExcelManager()
        
        # Créer une copie temporaire
        if not excel_manager.create_temporary_copy(property_data):
            return None
        
        # Mettre à jour les données
        if not excel_manager.update_property_data(property_data, additional_data):
            excel_manager.cleanup()
            return None
        
        st.success("✅ Analyse Excel générée avec succès !")
        
        # Retourner le gestionnaire pour utilisation ultérieure
        return excel_manager
        
    except Exception as e:
        st.error(f"❌ Erreur génération Excel : {str(e)}")
        return None