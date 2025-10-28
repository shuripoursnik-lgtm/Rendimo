"""
Rendimo - Assistant IA Immobilier
Application Streamlit pour l'analyse d'investissements immobiliers avec export Excel

Version: 2.0 - Analyse détaillée avec export Excel
Auteur: Assistant IA
Date: Octobre 2024
"""

import streamlit as st
import pandas as pd
import os
import shutil
from datetime import datetime
from pathlib import Path

# Excel handling
from openpyxl import load_workbook

# Import des modules métier
from utils.scraper import LeBonCoinScraper
from utils.calculator import RentabilityCalculator
from api.ai_assistant import AIAssistant
from api.price_api_dvf import DVFPriceAPI

# Configuration de la page
st.set_page_config(
    page_title="Rendimo - Assistant IA Immobilier",
    page_icon="🏠",
    layout="wide"
)

# CSS simplifié
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 0.5rem;
        margin: 0.5rem 0;
        border-radius: 5px;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 3px solid #2196f3;
    }
    .assistant-message {
        background-color: #f1f8e9;
        border-left: 3px solid #4caf50;
    }
</style>
""", unsafe_allow_html=True)

# Variables de session
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'property_data' not in st.session_state:
    st.session_state.property_data = None

def main():
    """
    Fonction principale de l'application Rendimo.
    
    Structure:
    - Interface à 3 onglets pour analyse de biens immobiliers
    - Chat bot IA pour conseils personnalisés
    - Export Excel avec données fiscales détaillées
    """
    
    # ============================================================================
    # EN-TÊTE APPLICATION
    # ============================================================================
    st.markdown('<h1 class="main-header">🏠 Rendimo - Assistant IA Immobilier</h1>', unsafe_allow_html=True)
    
    # Layout principal avec deux colonnes
    col1, col2 = st.columns([1, 1])
    
    # ============================================================================
    # COLONNE 1: ANALYSE DE BIEN
    # ============================================================================
    with col1:
        st.header("🔍 Analyse de bien")
        
        # Interface à 3 onglets
        tab1, tab2, tab3 = st.tabs(["🔗 URL LeBonCoin", "📝 Saisie manuelle", "📊 Analyse détaillée"])
        
        # TAB 1: Scraping LeBonCoin avec disclaimer
        with tab1:
            st.write("**Analyser une annonce LeBonCoin :**")
            
            # Disclaimer d'usage responsable
            st.info("""
            ⚠️ **Utilisation responsable**
            - Usage limité à 1-2 annonces par jour par utilisateur
            - Données à usage personnel d'analyse uniquement
            - Respect des conditions d'utilisation de LeBonCoin
            - Aucune donnée personnelle du vendeur n'est collectée
            """)
            
            url_input = st.text_input(
                "URL de l'annonce :",
                placeholder="https://www.leboncoin.fr/ventes_immobilieres/...",
                help="Copiez l'URL complète de l'annonce"
            )
            
            col_btn1, col_btn2 = st.columns([1, 1])
            
            with col_btn1:
                if st.button("Analyser l'annonce", type="primary"):
                    if url_input.strip():
                        analyze_property_from_url(url_input.strip())
                    else:
                        st.error("Veuillez entrer une URL valide")
            
            with col_btn2:
                if st.button("📋 Guide Inspecteur"):
                    show_inspector_guide()
        
        with tab2:
            st.write("**Saisie manuelle des données :**")
            manual_input_form()
        
        with tab3:
            st.write("**Analyse détaillée avec export Excel :**")
            detailed_analysis_form()
        
        st.divider()
        
    # Chat interface
    st.header("💬 Assistant IA")
    chat_interface()
    
    with col2:
        # Section Résultats avec estimation intégrée
        st.header("📊 Analyse & Estimation")
        results_interface()

def analyze_property_from_url(url):
    """Analyse une propriété à partir de son URL LeBonCoin"""
    try:
        with st.spinner("🔍 Extraction des données de l'annonce..."):
            scraper = LeBonCoinScraper()
            property_data = scraper.extract_property_data(url)
            
            if property_data and (property_data.get('title') or property_data.get('price')):
                st.session_state.property_data = property_data
                
                # Message de succès
                success_msg = f"""✅ **Données extraites avec succès !**

**Bien analysé :**
- 📍 **Ville :** {property_data.get('city', 'Non spécifiée')}
- 💰 **Prix :** {property_data.get('price', 0):,}€
- 📐 **Surface :** {property_data.get('surface', 0)} m²
- 🏠 **Type :** {property_data.get('property_type', 'Non spécifié')}
- 🛏️ **Pièces :** {property_data.get('rooms', 'Non spécifié')}

Les calculs d'estimation apparaissent dans la colonne de droite ! 👉"""
                
                add_chat_message("assistant", success_msg)
                st.success("✅ Extraction réussie ! Voir les résultats à droite.")
                
            else:
                st.error("❌ Impossible d'extraire les données")
                add_chat_message("assistant", """❌ **Extraction échouée**

💡 **Solutions :**
1. Utilisez l'onglet "Saisie manuelle"  
2. Consultez le "Guide Inspecteur" pour extraire manuellement
3. Vérifiez que l'annonce existe encore

N'hésitez pas à me poser vos questions directement ! 😊""")
    
    except Exception as e:
        st.error(f"❌ Erreur : {str(e)}")

def manual_input_form():
    """Formulaire de saisie manuelle"""
    with st.form("manual_form"):
        col_a, col_b = st.columns(2)
        
        with col_a:
            property_type = st.selectbox("Type", ["Appartement", "Maison", "Studio", "Autre"])
            price = st.number_input("Prix (€)", min_value=0, value=0, step=1000)
            surface = st.number_input("Surface (m²)", min_value=0, value=0, step=1)
            
        with col_b:
            city = st.text_input("Ville", placeholder="ex: Surgères")
            rooms = st.number_input("Pièces", min_value=0, value=0, step=1)
            postal_code = st.text_input("Code postal", placeholder="ex: 17700")
        
        if st.form_submit_button("Analyser ce bien", type="primary"):
            if price > 0 and surface > 0 and city:
                manual_data = {
                    'title': f"{property_type} {surface}m² - {city}",
                    'price': price,
                    'surface': surface,
                    'rooms': rooms,
                    'city': city,
                    'postal_code': postal_code,
                    'property_type': property_type,
                    'source_url': 'SAISIE_MANUELLE',
                    'extraction_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                st.session_state.property_data = manual_data
                add_chat_message("assistant", f"✅ **Bien ajouté :** {property_type} {surface}m² à {city} pour {price:,}€")
                st.success("✅ Bien ajouté ! Voir l'analyse à droite.")
            else:
                st.error("❌ Veuillez remplir tous les champs obligatoires")

def show_inspector_guide():
    """Affiche le guide d'utilisation de l'inspecteur"""
    st.info("""**🔍 Guide d'extraction manuelle :**
                    
1. **Ouvrir l'annonce** dans votre navigateur
2. **F12** pour ouvrir l'inspecteur  
3. **Console** → Coller ce script :

```javascript
// Prix
const price = document.querySelector('[data-qa-id="adview_price"]')?.textContent;
console.log('Prix:', price);

// Surface  
const surface = document.body.textContent.match(/(\\d+)\\s*m²/)?.[1];
console.log('Surface:', surface + ' m²');

// Pièces
const rooms = document.body.textContent.match(/(\\d+)\\s*pièce/i)?.[1];
console.log('Pièces:', rooms);
```

4. **Copier les résultats** dans "Saisie manuelle"
                    
📖 **Guide complet :** `GUIDE_INSPECTEUR.md`""")

def detailed_analysis_form():
    """
    Formulaire d'analyse détaillée avec export Excel.
    
    Collecte des informations supplémentaires pour générer un fichier Excel
    personnalisé avec les données du bien immobilier et les paramètres
    fiscaux selon la structure d'investissement (Nom propre ou SCI).
    """
    
    # Vérification des prérequis
    if not st.session_state.get('property_data'):
        st.warning("⚠️ Veuillez d'abord analyser un bien via l'onglet 'URL LeBonCoin' ou 'Saisie manuelle'")
        return
    
    property_data = st.session_state.property_data
    
    # Affichage du bien sélectionné
    st.info(f"""
    **📋 Bien sélectionné :**
    - **Titre :** {property_data.get('title', 'N/A')}
    - **Prix :** {property_data.get('price', 0):,}€
    - **Surface :** {property_data.get('surface', 0)} m²
    - **Ville :** {property_data.get('city', 'N/A')}
    """)
    
    st.markdown("### 📊 Informations supplémentaires pour l'analyse")
    
    # Structure d'investissement - Hors formulaire pour mise à jour temps réel
    st.subheader("🏛️ Structure d'investissement")
    type_investissement = st.selectbox(
        "Investissez-vous en nom propre ou via SCI ?", 
        options=["Nom propre", "SCI"], 
        index=0,
        key="type_investissement"
    )
    
    # Formulaire principal
    with st.form("detailed_analysis"):
        # Section 1: Caractéristiques du bien et financement
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏠 Caractéristiques du bien")
            type_bien = st.selectbox("Neuf ou Occasion ?", options=["Occasion", "Neuf"], index=0)
            loyer_hc = st.number_input("Loyer mensuel HC estimé (€)", min_value=0, value=800, step=25)
            loyer_cc = st.number_input("Loyer mensuel CC estimé (€)", min_value=0, value=850, step=25)
            cout_renovation = st.number_input("Coût des travaux de rénovation (€)", min_value=0, value=0, step=500)
            cout_construction = st.number_input("Coût des travaux de construction (€)", min_value=0, value=0, step=500)
            
        with col2:
            st.subheader("💰 Financement")
            utilise_pret = st.selectbox("Vous utilisez un prêt ?", options=["Oui", "Non"], index=0)
            apport_default = int(property_data.get('price', 0) * 0.15)  # 15% du prix
            apport = st.number_input("Combien d'apport (€)", min_value=0, value=apport_default, step=1000)
            duree_pret = st.number_input("Durée du prêt (années)", min_value=1, max_value=30, value=20, step=1)
            taux_pret = st.number_input("Taux du prêt (%)", min_value=0.0, max_value=10.0, value=4.0, step=0.1)
        
        # Variables pour stocker les données fiscales
        donnees_fiscales = {}
        
        if type_investissement == "Nom propre":
            st.markdown("---")
            st.markdown("**📋 Informations fiscales - Nom propre**")
            col_np1, col_np2 = st.columns(2)
            
            with col_np1:
                situation = st.selectbox("Situation ?", 
                                       options=["Célibataire-divorcé-veuf", "Marié-pacsé"], 
                                       index=0)
                revenu_net = st.number_input("Revenu net global du foyer (€)", 
                                           min_value=0, value=50000, step=1000)
            
            with col_np2:
                nombre_enfants = st.number_input("Nombre d'enfants", 
                                               min_value=0, max_value=10, value=0, step=1)
            
            donnees_fiscales = {
                'type': 'nom_propre',
                'situation': situation,
                'revenu_net': revenu_net,
                'nombre_enfants': nombre_enfants
            }
        
        else:  # SCI
            st.markdown("---")
            st.markdown("**🏢 Informations SCI**")
            col_sci1, col_sci2 = st.columns(2)
            
            with col_sci1:
                capital_sci = st.number_input("Capital de la SCI (€)", 
                                            min_value=0, value=1000, step=100)
                nombre_associes = st.number_input("Nombre d'associés", 
                                                min_value=1, max_value=4, value=2, step=1)
            
            # Informations pour chaque associé
            associes = []
            for i in range(int(nombre_associes)):
                st.markdown(f"**👤 Associé {i+1}**")
                col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                
                with col_a1:
                    part = st.number_input(f"Part détenue (%)", 
                                         min_value=0.0, max_value=100.0, 
                                         value=50.0 if i == 0 else 50.0, 
                                         step=1.0, key=f"part_{i}")
                
                with col_a2:
                    situation_assoc = st.selectbox(f"Situation", 
                                                 options=["Célibataire-divorcé-veuf", "Marié-pacsé"], 
                                                 index=0, key=f"situation_{i}")
                
                with col_a3:
                    revenu_assoc = st.number_input(f"Revenu net (€)", 
                                                 min_value=0, value=50000, 
                                                 step=1000, key=f"revenu_{i}")
                
                with col_a4:
                    enfants_assoc = st.number_input(f"Enfants", 
                                                  min_value=0, max_value=10, 
                                                  value=0, step=1, key=f"enfants_{i}")
                
                associes.append({
                    'part': part,
                    'situation': situation_assoc,
                    'revenu': revenu_assoc,
                    'enfants': enfants_assoc
                })
            
            donnees_fiscales = {
                'type': 'sci',
                'capital': capital_sci,
                'nombre_associes': nombre_associes,
                'associes': associes
            }
        
        # Estimation à la revente
        st.markdown("---")
        st.subheader("📈 Plus-value")
        estimation_revente_default = int(property_data.get('price', 0) * 1.2)  # 120% du prix
        estimation_revente = st.number_input("Estimation à la revente (€)", 
                                           min_value=0, value=estimation_revente_default, step=5000)
        
        submitted = st.form_submit_button("📁 Générer l'analyse Excel", type="primary")
        
        if submitted:
            # Créer l'Excel avec les données
            excel_file = generate_excel_analysis(property_data, {
                'type_bien': type_bien,
                'loyer_hc': loyer_hc,
                'loyer_cc': loyer_cc,
                'utilise_pret': utilise_pret,
                'apport': apport,
                'duree_pret': duree_pret,
                'taux_pret': taux_pret,
                'cout_renovation': cout_renovation,
                'cout_construction': cout_construction,
                'donnees_fiscales': donnees_fiscales,
                'estimation_revente': estimation_revente
            })
            
            if excel_file:
                st.success("✅ Analyse Excel générée avec succès !")
                # Stocker le fichier dans session_state pour le téléchargement
                st.session_state['excel_file'] = excel_file
                st.session_state['excel_filename'] = f"Rendimo_Analyse_{property_data.get('city', 'Bien')}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    
    # Bouton de téléchargement en dehors du formulaire
    if 'excel_file' in st.session_state and st.session_state['excel_file']:
        with open(st.session_state['excel_file'], "rb") as file:
            st.download_button(
                label="💾 Télécharger l'analyse Excel",
                data=file.read(),
                file_name=st.session_state['excel_filename'],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

def generate_excel_analysis(property_data, additional_data):
    """
    Génère un fichier Excel personnalisé avec les données du bien immobilier.
    
    Args:
        property_data (dict): Données du bien (prix, surface, ville, etc.)
        additional_data (dict): Données supplémentaires du formulaire
        
    Returns:
        str: Chemin vers le fichier Excel généré, ou None en cas d'erreur
        
    Mapping des données:
        - Feuille "Frais de notaire": Prix (I3), Type bien (F3)
        - Feuille "Coûts et rendement": Loyers, prêt, travaux
        - Feuille "Nom propre - Fiscalité" ou "SCI": Données fiscales
        - Feuille "Plus value": Estimation revente (E7)
    """
    try:
        # Vérification du template
        template_path = Path("Excel/Rendimmo - Rentabilité.xlsx")
        if not template_path.exists():
            st.error("❌ Fichier template Excel non trouvé")
            return None
        
        # Ouverture directe du template et préparation du fichier de sortie
        workbook = load_workbook(template_path)
        output_path = Path(f"temp_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        
        # ============================================================================
        # SECTION 1: FEUILLE "FRAIS DE NOTAIRE"
        # ============================================================================
        if "Frais de notaire" in workbook.sheetnames:
            sheet_frais = workbook["Frais de notaire"]
            sheet_frais["I3"] = property_data.get('price', 0)  # Prix du bien
            sheet_frais["F3"] = additional_data.get('type_bien', 'Occasion')  # Type bien
        
        # ============================================================================
        # SECTION 2: FEUILLE "COÛTS ET RENDEMENT"
        # ============================================================================
        sheet_cout = None
        for sheet_name in workbook.sheetnames:
            if "rendement" in sheet_name.lower():
                sheet_cout = workbook[sheet_name]
                break
        
        if sheet_cout:
            # Données locatives
            sheet_cout["D7"] = additional_data.get('loyer_hc', 0)      # Loyer HC
            sheet_cout["D8"] = additional_data.get('loyer_cc', 0)      # Loyer CC
            sheet_cout["D9"] = property_data.get('surface', 0)         # Surface
            
            # Données de financement
            sheet_cout["D14"] = additional_data.get('utilise_pret', 'Oui')     # Prêt
            sheet_cout["D15"] = additional_data.get('duree_pret', 20)          # Durée
            sheet_cout["D16"] = additional_data.get('apport', 0)               # Apport
            sheet_cout["D17"] = additional_data.get('taux_pret', 4.0) / 100    # Taux
            
            # Données travaux
            sheet_cout["D21"] = additional_data.get('cout_renovation', 0)      # Rénovation
            sheet_cout["D22"] = additional_data.get('cout_construction', 0)    # Construction
        
        # ============================================================================
        # SECTION 3: DONNÉES FISCALES (NOM PROPRE OU SCI)
        # ============================================================================
        donnees_fiscales = additional_data.get('donnees_fiscales', {})
        
        if donnees_fiscales.get('type') == 'nom_propre':
            # Feuille "Nom propre - Fiscalité"
            if "Nom propre - Fiscalité" in workbook.sheetnames:
                sheet_np = workbook["Nom propre - Fiscalité"]
                sheet_np["D6"] = donnees_fiscales.get('revenu_net', 50000)    # Revenu net
                sheet_np["D7"] = donnees_fiscales.get('situation', 'Célibataire-divorcé-veuf')  # Situation
                sheet_np["D8"] = donnees_fiscales.get('nombre_enfants', 0)    # Enfants
        
        elif donnees_fiscales.get('type') == 'sci':
            # Feuille "SCI"
            if "SCI" in workbook.sheetnames:
                sheet_sci = workbook["SCI"]
                sheet_sci["D6"] = donnees_fiscales.get('capital', 1000)  # Capital SCI
                
                # Données des associés (maximum 4)
                associes = donnees_fiscales.get('associes', [])
                colonnes = ['D', 'E', 'F', 'G']  # Colonnes pour associés 1-4
                
                for i, associe in enumerate(associes[:4]):
                    col = colonnes[i]
                    sheet_sci[f"{col}8"] = associe.get('part', 50) / 100      # Part (%)
                    sheet_sci[f"{col}10"] = associe.get('revenu', 50000)       # Revenu
                    sheet_sci[f"{col}11"] = associe.get('situation', 'Célibataire-divorcé-veuf')  # Situation
                    sheet_sci[f"{col}12"] = associe.get('enfants', 0)          # Enfants
        
        # ============================================================================
        # SECTION 4: FEUILLE "PLUS VALUE"
        # ============================================================================
        if "Plus value" in workbook.sheetnames:
            sheet_pv = workbook["Plus value"]
            sheet_pv["E7"] = additional_data.get('estimation_revente', 0)  # Estimation revente
        
        # Sauvegarde du fichier Excel
        workbook.save(output_path)
        workbook.close()
        
        return str(output_path)
        
    except Exception as e:
        st.error(f"❌ Erreur lors de la génération Excel : {str(e)}")
        return None

def chat_interface():
    """Interface de chat classique orientée immobilier (Streamlit chat)."""

    # Initialiser/afficher l'état de la connexion IA
    if 'assistant' not in st.session_state:
        st.session_state.assistant = AIAssistant()
    assistant: AIAssistant = st.session_state.assistant

    # Bandeau d'état du backend IA
    backend = ""
    if getattr(assistant, 'groq_client', None):
        backend = f"Groq · Modèle: {getattr(assistant, 'groq_model', 'n/a')} · Température: {getattr(assistant, 'generation_temperature', 'n/a')}"
        st.caption(f"Connexion IA: {backend}")
    elif getattr(assistant, 'openai_client', None):
        backend = f"OpenAI · Modèle: {getattr(assistant, 'openai_model', 'n/a')} · Température: {getattr(assistant, 'generation_temperature', 'n/a')}"
        st.caption(f"Connexion IA: {backend}")
    else:
        st.caption("Connexion IA: mode local (fallback)")

    # Replay de l'historique en bulles de chat
    for msg in st.session_state.chat_history:
        with st.chat_message(msg['role']):
            st.markdown(msg['content'])

    # Entrée utilisateur en bas, style chat
    prompt = st.chat_input("Posez votre question (ex: Qu'est-ce qu'une SCI ? Différence LMNP vs LMP ?)" )
    if prompt:
        # Afficher et stocker la requête utilisateur
        st.session_state.chat_history.append({
            'role': 'user',
            'content': prompt,
            'timestamp': datetime.now().isoformat()
        })
        with st.chat_message("user"):
            st.markdown(prompt)

        # Obtenir la réponse de l'assistant avec contexte du bien
        with st.chat_message("assistant"):
            with st.spinner("Rédaction de la réponse…"):
                reply = assistant.get_response(
                    prompt,
                    st.session_state.chat_history,
                    st.session_state.property_data
                )
                st.markdown(reply)
        # Stocker la réponse
        st.session_state.chat_history.append({
            'role': 'assistant',
            'content': reply,
            'timestamp': datetime.now().isoformat()
        })
        # Pas de st.rerun ici, l'UI de chat gère le flux

def results_interface():
    """Interface des résultats avec estimation intégrée"""
    
    if st.session_state.property_data:
        property_data = st.session_state.property_data
        
        # Résumé du bien
        st.subheader("🏠 Bien analysé")
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.metric("Prix", f"{property_data.get('price', 0):,}€")
            st.metric("Surface", f"{property_data.get('surface', 0)} m²")
        with col_r2:
            if property_data.get('price', 0) > 0 and property_data.get('surface', 0) > 0:
                price_per_sqm = property_data['price'] / property_data['surface']
                st.metric("Prix/m²", f"{price_per_sqm:,.0f}€")
            st.metric("Pièces", property_data.get('rooms', 'N/A'))
        
        st.divider()

        # Estimation via API intégrée
        st.subheader("💰 Estimation de marché")

        if st.button("🔍 Estimer avec données locales"):
            estimate_with_api(property_data)

        # Calculs de rentabilité avec saisie du loyer
        st.subheader("📊 Analyse de rentabilité")

        if property_data.get('price', 0) > 0 and property_data.get('surface', 0) > 0:
            # Champ de saisie du loyer estimé
            loyer_suggest = int(property_data['price'] * 0.008)  # Suggestion 0.8% du prix
            
            monthly_rent = st.number_input(
                "💶 Loyer mensuel estimé (€)",
                min_value=0,
                value=loyer_suggest,
                step=50,
                help="Estimez le loyer mensuel que vous pourriez obtenir"
            )
            
            if monthly_rent > 0:
                # Utiliser le calculator
                calculator = RentabilityCalculator()
                result = calculator.calculate_gross_yield(property_data['price'], monthly_rent)
                
                if 'error' not in result:
                    col_calc1, col_calc2, col_calc3 = st.columns(3)
                    with col_calc1:
                        st.metric("Loyer annuel", f"{result['annual_rent']:,.0f}€")
                    with col_calc2:
                        st.metric("Rentabilité brute", f"{result['gross_yield']:.2f}%")
                    with col_calc3:
                        st.metric("Évaluation", result['evaluation'])
                else:
                    st.warning(f"⚠️ {result['error']}")

        # Bouton réinitialiser
        if st.button("🔄 Nouvelle analyse"):
            st.session_state.property_data = None
            st.rerun()
            
    else:
        st.info("👈 Analysez un bien pour voir les résultats ici")
        
        # Aide rapide
        st.markdown("""
        **Comment utiliser Rendimo :**
        
        1. 🔗 **Collez une URL** LeBonCoin dans l'onglet correspondant
        2. 📝 **Ou saisissez manuellement** les données du bien
        3. 📊 **Consultez l'analyse** qui apparaîtra ici
        4. 💬 **Posez vos questions** à l'assistant IA
        """)

def estimate_with_api(property_data):
    """Estime un bien via SimplePriceAPI avec score de fiabilité"""
    try:
        with st.spinner("🔍 Estimation en cours..."):
            # Pré-requis
            surface = property_data.get('surface', 0)
            price = property_data.get('price', 0)
            if surface <= 0:
                st.warning("⚠️ Surface requise pour l'estimation")
                return

            city = property_data.get('city', '') or ''
            postal_code = property_data.get('postal_code', None)
            raw_type = (property_data.get('property_type') or '').lower()

            # Mapping type LeBonCoin → DVF (apartment|house|other)
            if 'maison' in raw_type or 'villa' in raw_type:
                api_type = 'house'
            elif 'appartement' in raw_type or 'studio' in raw_type or 'duplex' in raw_type:
                api_type = 'apartment'
            elif 'terrain' in raw_type or 'parking' in raw_type or 'garage' in raw_type:
                api_type = 'other'
            else:
                # Fallback par défaut : appartement pour tout le reste
                api_type = 'apartment'

            api = DVFPriceAPI(use_lite=False)  # Utilise la base FULL avec toutes les villes
            market = api.get_price_estimate(city=city, postal_code=postal_code, property_type=api_type)

            if market.get('error'):
                st.info("ℹ️ Aucune estimation disponible pour cette commune.")
                add_chat_message("assistant", "ℹ️ Impossible d'estimer le prix pour cette zone.")
                return

            # Sauvegarde en session pour chatbot/usage ultérieur
            st.session_state['market_data'] = market

            # Affichage simplifié des métriques marché
            st.markdown("### 📈 Marché local")
            m1, m2, m3 = st.columns([2, 1, 1])
            with m1:
                st.metric("Prix moyen €/m²", f"{market.get('price_per_sqm', 0):,}€")
            with m2:
                # Score de fiabilité avec indicateur visuel
                reliability = market.get('reliability_score', 0)
                transaction_count = market.get('transaction_count', 0)
                if reliability >= 85:
                    icon = "🟢"
                elif reliability >= 70:
                    icon = "🟡"
                else:
                    icon = "🟠"
                st.metric("Fiabilité", f"{icon} {reliability}% ({transaction_count} trans.)")
            with m3:
                st.caption("**Source:**")
                st.caption(market.get('source', 'N/A'))

            # Comparaison du bien vs marché
            st.markdown("### 🧮 Comparaison du bien")
            cmp_res = api.compare_property_price(property_price=price, property_surface=surface, market_data=market)
            if 'error' in cmp_res:
                st.warning(f"⚠️ {cmp_res['error']}")
            else:
                k1, k2, k3 = st.columns(3)
                with k1:
                    st.metric("Prix du bien €/m²", f"{cmp_res['property_price_per_sqm']:.0f}€")
                with k2:
                    st.metric("Écart vs marché", f"{cmp_res['percentage_difference']:+.1f}%")
                with k3:
                    st.metric("Évaluation", cmp_res.get('score', 'N/A'))

            # Message chatbot avec source et fiabilité
            add_chat_message(
                "assistant",
                f"📊 Estimation affichée pour {city} ({api_type}). "
                f"Prix moyen: {market.get('price_per_sqm', 'N/A')}€/m² — "
                f"Source: {market.get('source', 'N/A')} — "
                f"Fiabilité: {market.get('reliability_score', 'N/A')}%"
            )

    except Exception as e:
        st.error(f"❌ Erreur estimation : {str(e)}")

def handle_chat_message(message):
    """Traite un message de chat"""
    try:
        # Ajouter le message utilisateur
        add_chat_message("user", message)
        
        # Initialiser l'assistant IA
        assistant = AIAssistant()
        
        # Obtenir la réponse
        response = assistant.get_response(
            message, 
            st.session_state.chat_history,
            st.session_state.property_data
        )
        
        # Ajouter la réponse
        add_chat_message("assistant", response)
        
        st.rerun()
        
    except Exception as e:
        add_chat_message("assistant", f"❌ Erreur : {str(e)}")
        st.rerun()

def add_chat_message(role, content):
    """Ajoute un message au chat"""
    st.session_state.chat_history.append({
        'role': role,
        'content': content,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == "__main__":
    main()