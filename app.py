"""
Rendimo - Assistant IA Immobilier
Application Streamlit pour l'analyse d'investissements immobiliers

Version: 3.0 - Interface redesignée avec analyse Excel locale
Auteur: Assistant IA
Date: Octobre 2025
"""

import streamlit as st
import pandas as pd
import os
import shutil
import traceback
from datetime import datetime
from pathlib import Path

# Excel handling
from openpyxl import load_workbook
import pandas as pd

# Graphics for indicators
import plotly.express as px
import plotly.graph_objects as go

# Google Sheets et Excel
from utils.google_sheets_manager import GoogleSheetsManager
from utils.excel_manager import generate_excel_analysis

# Import des modules métier
from utils.scraper import LeBonCoinScraper
from utils.calculator import RentabilityCalculator
from api.ai_assistant import AIAssistant
from api.price_api_dvf import DVFPriceAPI

# Configuration de la page
st.set_page_config(
    page_title="Rendimo - Assistant IA Immobilier",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personnalisé avec la charte graphique Rendimo
st.markdown("""
<style>
    /* Import de Century Gothic */
    @import url('https://fonts.googleapis.com/css2?family=Century+Gothic:wght@400;700&display=swap');
    
    /* Variables CSS */
    :root {
        --rendimo-blue: #213a56;
        --rendimo-gold: #deb35b;
        --text-white: #ffffff;
    }
    
    /* Police globale */
    html, body, [class*="css"] {
        font-family: 'Century Gothic', 'Trebuchet MS', sans-serif !important;
    }
    
    /* Masquer les éléments Streamlit par défaut */
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    .stMainBlockContainer {padding-top: 1rem;}
    
    /* Fond principal */
    .stApp {
        background: linear-gradient(135deg, var(--rendimo-blue) 0%, #2c4f7a 100%);
        color: var(--text-white);
    }
    
    /* Logo et titre principal */
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        margin-bottom: 2rem;
        backdrop-filter: blur(10px);
    }
    
    .main-title {
        font-size: 3rem;
        font-weight: 700;
        color: var(--rendimo-gold);
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        margin-bottom: 0.5rem;
        background: linear-gradient(45deg, var(--rendimo-gold), #f4d03f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .main-subtitle {
        font-size: 1.2rem;
        color: var(--text-white);
        opacity: 0.9;
        max-width: 600px;
        margin: 0 auto;
        line-height: 1.6;
    }
    
    /* Cartes des onglets */
    .tab-card {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 0.5rem 0 1rem 0;
        border: 1px solid rgba(222, 179, 91, 0.3);
        backdrop-filter: blur(10px);
    }
    
    .tab-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--rendimo-gold);
        margin-bottom: 0.5rem;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
    }
    
    .tab-description {
        color: var(--text-white);
        opacity: 0.8;
        font-size: 1rem;
        line-height: 1.5;
    }
    
    /* Boutons personnalisés */
    .stButton > button {
        background: linear-gradient(45deg, var(--rendimo-gold), #f4d03f);
        color: var(--rendimo-blue);
        border: none;
        border-radius: 10px;
        font-weight: 700;
        font-family: 'Century Gothic', sans-serif;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(222, 179, 91, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(222, 179, 91, 0.4);
    }
    
    /* Métriques et indicateurs */
    .metric-container {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid var(--rendimo-gold);
    }
    
    /* Messages d'information */
    .stAlert {
        background-color: rgba(222, 179, 91, 0.1);
        border: 1px solid var(--rendimo-gold);
        color: var(--text-white);
    }
    
    /* Champs de saisie */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select {
        background-color: rgba(255, 255, 255, 0.1);
        color: var(--text-white);
        border: 1px solid rgba(222, 179, 91, 0.5);
        border-radius: 8px;
    }
    
    /* Titres de sections */
    .section-title {
        color: var(--rendimo-gold);
        font-weight: 700;
        font-size: 1.3rem;
        margin: 1.5rem 0 1rem 0;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
    }
    
    /* Chat messages */
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        backdrop-filter: blur(10px);
    }
    
    .user-message {
        background: rgba(222, 179, 91, 0.2);
        border-left: 3px solid var(--rendimo-gold);
    }
    
    .assistant-message {
        background: rgba(255, 255, 255, 0.1);
        border-left: 3px solid var(--text-white);
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: var(--rendimo-blue);
    }
    
    /* Graphiques */
    .js-plotly-plot {
        background: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

# Variables de session
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'property_data' not in st.session_state:
    st.session_state.property_data = None

def main():
    """Interface principale avec page d'accueil et navigation par onglets"""
    
    # Initialisation du state si nécessaire
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = "home"
    
    # Affichage de la page selon l'onglet sélectionné
    if st.session_state.current_tab == "home":
        show_welcome_page()
    elif st.session_state.current_tab == "ai_chat":
        show_ai_chat()
    elif st.session_state.current_tab == "simple_analysis":
        show_simple_analysis()
    elif st.session_state.current_tab == "detailed_analysis":
        show_detailed_analysis()

def show_welcome_page():
    """Page d'accueil avec logo et navigation principale"""
    
    # En-tête principal avec logo
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    
    # Logo à gauche + titre
    col1, col2 = st.columns([1, 4])
    with col1:
        try:
            logo_path = Path(__file__).parent / "Logo" / "Rendimo.jpg"
            if logo_path.exists():
                st.image(str(logo_path), width=120)
        except Exception as e:
            st.warning(f"Logo non trouvé : {e}")
    
    with col2:
        # Titre et sous-titre
        st.markdown('<h1 class="main-title">Rendimo</h1>', unsafe_allow_html=True)
        st.markdown('<p class="main-subtitle">Votre assistant IA pour l\'analyse d\'investissements immobiliers<br>Analyses précises • Rapports Excel • Intelligence artificielle</p>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Cartes de navigation
    st.markdown("### 🚀 Choisissez votre mode d'analyse")
    
    # Ligne 1 : AI Chat et Analyse Simplifiée
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="tab-card">
            <h3 class="tab-title">💬 Intelligence Artificielle</h3>
            <p class="tab-description">
                Posez vos questions à notre assistant IA spécialisé en immobilier.
                Conseils personnalisés, stratégies d'investissement et analyses de marché.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🤖 Discutez avec notre IA", key="btn_ai_chat", use_container_width=True):
            st.session_state.current_tab = "ai_chat"
            st.rerun()
    
    with col2:
        st.markdown("""
        <div class="tab-card">
            <h3 class="tab-title">⚡ Analyse Rapide</h3>
            <p class="tab-description">
                Extraction automatique depuis LeBonCoin avec analyse immédiate.
                Parfait pour un premier aperçu de la rentabilité d'un bien.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("� Analyse Simplifiée", key="btn_simple", use_container_width=True):
            st.session_state.current_tab = "simple_analysis"
            st.rerun()
    
    # Ligne 2 : Analyse Détaillée (centrée)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="tab-card">
            <h3 class="tab-title">🎯 Analyse Complète</h3>
            <p class="tab-description">
                Formulaire complet avec tous les paramètres d'investissement.
                Génération de rapport Excel professionnel avec graphiques et projections.
                Idéal pour une étude approfondie avant achat.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("📈 Analyse Détaillée", key="btn_detailed", use_container_width=True):
            st.session_state.current_tab = "detailed_analysis"
            st.rerun()
    
    # Pied de page avec informations
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **✨ Fonctionnalités**
        - Scraping automatique LeBonCoin
        - Comparaison prix DVF
        - Calculs de rentabilité
        - Rapports Excel
        """)
    
    with col2:
        st.markdown("""
        **🔧 Outils Intégrés**
        - Intelligence artificielle
        - Base de données DVF
        - Graphiques interactifs
        - Projections financières
        """)
    
    with col3:
        st.markdown("""
        **📋 Analyse Complète**
        - Rendement locatif
        - Cash-flow prévisionnel
        - Plus-value potentielle
        - Ratios d'investissement
        """)

def show_ai_chat():
    """Page de chat avec l'IA"""
    
    # Marge en haut pour le bouton retour
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Header avec retour accueil
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("🏠 Accueil", key="home_from_ai"):
            st.session_state.current_tab = "home"
            st.rerun()
    
    with col2:
        st.markdown('<h2 class="section-title">🤖 Assistant IA Immobilier</h2>', unsafe_allow_html=True)
    
    st.markdown("Posez toutes vos questions sur l'investissement immobilier à notre assistant spécialisé.")
    
    # Bouton pour effacer la conversation
    if st.button("🗑️ Effacer la conversation", key="clear_chat"):
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "Conversation effacée ! Quelle est votre nouvelle question ?", "timestamp": datetime.now().isoformat()}
        ]
        st.rerun()
    
    # Initialisation de l'assistant IA
    if 'assistant' not in st.session_state:
        st.session_state.assistant = AIAssistant()
    assistant = st.session_state.assistant
    
    # Bandeau d'état du backend IA
    if getattr(assistant, 'groq_client', None):
        backend = f"Groq · Modèle: {getattr(assistant, 'groq_model', 'n/a')} · Température: {getattr(assistant, 'generation_temperature', 'n/a')}"
        st.caption(f"🤖 Connexion IA: {backend}")
    elif getattr(assistant, 'openai_client', None):
        backend = f"OpenAI · Modèle: {getattr(assistant, 'openai_model', 'n/a')} · Température: {getattr(assistant, 'generation_temperature', 'n/a')}"
        st.caption(f"🤖 Connexion IA: {backend}")
    else:
        st.caption("🤖 Connexion IA: mode local (fallback)")
    
    # Initialisation du chat avec message de bienvenue
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "Bonjour ! Je suis votre assistant IA spécialisé en immobilier. Je peux vous aider avec :\n\n• Conseils d'investissement\n• Analyse de marché\n• Stratégies de financement\n• Fiscalité immobilière (SCI, LMNP, LMP...)\n• Gestion locative\n• Questions spécifiques sur vos biens\n\nQuelle est votre question ?", "timestamp": datetime.now().isoformat()}
        ]
    
    # Affichage des messages avec le style chat Streamlit
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Zone de saisie en bas style chat
    prompt = st.chat_input("Posez votre question (ex: Qu'est-ce qu'une SCI ? Différence LMNP vs LMP ?)")
    
    if prompt:
        # Afficher et stocker la requête utilisateur
        st.session_state.chat_messages.append({
            'role': 'user',
            'content': prompt,
            'timestamp': datetime.now().isoformat()
        })
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Obtenir la réponse de l'assistant avec contexte
        with st.chat_message("assistant"):
            with st.spinner("Rédaction de la réponse…"):
                # Utiliser get_response avec le contexte complet
                property_data = st.session_state.get('extracted_data', None)
                reply = assistant.get_response(
                    prompt,
                    st.session_state.chat_messages,
                    property_data
                )
                st.markdown(reply)
        
        # Stocker la réponse
        st.session_state.chat_messages.append({
            'role': 'assistant',
            'content': reply,
            'timestamp': datetime.now().isoformat()
        })
        
        # Pas de st.rerun ici, l'interface chat gère automatiquement

def show_simple_analysis():
    """Page d'analyse simplifiée avec extraction LeBonCoin"""
    
    # Marge en haut pour le bouton retour
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Header avec retour accueil
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("🏠 Accueil", key="home_from_simple"):
            st.session_state.current_tab = "home"
            st.rerun()
    
    with col2:
        st.markdown('<h2 class="section-title">📊 Analyse Simplifiée</h2>', unsafe_allow_html=True)
    
    st.markdown("Collez un lien LeBonCoin pour une analyse rapide, ou saisissez manuellement les données.")
    
    # Onglets pour URL ou saisie manuelle
    tab1, tab2 = st.tabs(["🔗 URL LeBonCoin", "✏️ Saisie manuelle"])
    
    with tab1:
        # Zone de saisie URL
        url = st.text_input("🔗 URL de l'annonce LeBonCoin :", 
                           placeholder="https://www.leboncoin.fr/ventes_immobilieres/...",
                           help="Collez le lien de l'annonce immobilière à analyser")
        
        if st.button("🚀 Analyser cette annonce", disabled=not url.strip()):
            if url.strip():
                with st.spinner("🔄 Extraction des données en cours..."):
                    try:
                        # Scraping
                        scraper = LeBonCoinScraper()
                        property_data = scraper.extract_property_data(url)
                        
                        if property_data:
                            # Stockage dans la session pour utilisation dans l'analyse détaillée
                            st.session_state.extracted_data = property_data
                            
                            # Affichage des données extraites
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown('<h3 class="section-title">🏠 Informations du bien</h3>', unsafe_allow_html=True)
                                st.metric("Prix de vente", f"{property_data.get('price', 'N/A'):,} €")
                                st.metric("Surface", f"{property_data.get('surface', 'N/A')} m²")
                                st.metric("Localisation", property_data.get('city', property_data.get('location', 'N/A')))
                                
                                if property_data.get('rooms'):
                                    st.metric("Nombre de pièces", property_data.get('rooms'))
                            
                            with col2:
                                # Analyse DVF si possible
                                location = property_data.get('city', property_data.get('location', ''))
                                if location:
                                    try:
                                        # Préparer les données pour l'API DVF
                                        surface = property_data.get('surface', 0)
                                        price = property_data.get('price', 0)
                                        
                                        # Mapping type LeBonCoin → DVF
                                        raw_type = (property_data.get('property_type', '') or '').lower()
                                        if 'maison' in raw_type or 'villa' in raw_type:
                                            api_type = 'house'
                                        elif 'appartement' in raw_type or 'studio' in raw_type or 'duplex' in raw_type:
                                            api_type = 'apartment'
                                        else:
                                            api_type = 'apartment'  # Fallback
                                        
                                        dvf_api = DVFPriceAPI(use_lite=False)  # Base complète
                                        market_data = dvf_api.get_price_estimate(
                                            city=location,
                                            postal_code=property_data.get('postal_code', None),
                                            property_type=api_type
                                        )
                                        
                                        if not market_data.get('error'):
                                            st.markdown('<h3 class="section-title">📈 Comparaison marché DVF</h3>', unsafe_allow_html=True)
                                            
                                            # Métriques marché
                                            col_m1, col_m2 = st.columns(2)
                                            with col_m1:
                                                st.metric("Prix moyen m²", f"{market_data.get('price_per_sqm', 0):,.0f} €/m²")
                                                reliability = market_data.get('reliability_score', 0)
                                                transaction_count = market_data.get('transaction_count', 0)
                                                
                                                if reliability >= 85:
                                                    icon = "🟢"
                                                elif reliability >= 70:
                                                    icon = "🟡"
                                                else:
                                                    icon = "🟠"
                                                st.metric("Fiabilité", f"{icon} {reliability}% ({transaction_count} trans.)")
                                            
                                            with col_m2:
                                                # Comparaison du bien vs marché
                                                if surface > 0 and price > 0:
                                                    property_price_per_sqm = price / surface
                                                    market_price_per_sqm = market_data.get('price_per_sqm', 0)
                                                    
                                                    if market_price_per_sqm > 0:
                                                        diff_pct = ((property_price_per_sqm - market_price_per_sqm) / market_price_per_sqm) * 100
                                                        st.metric("Prix bien €/m²", f"{property_price_per_sqm:,.0f} €/m²")
                                                        
                                                        if diff_pct > 10:
                                                            evaluation = "🔴 Cher"
                                                        elif diff_pct > -5:
                                                            evaluation = "🟡 Correct"
                                                        else:
                                                            evaluation = "🟢 Bon prix"
                                                        
                                                        st.metric("Écart vs marché", f"{diff_pct:+.1f}%", delta=evaluation)
                                            
                                            # Calcul de rentabilité estimée
                                            if surface > 0 and price > 0:
                                                # Estimation loyer basée sur 15€/m² par défaut ou données DVF
                                                estimated_rent_per_sqm = 15  # Estimation conservative
                                                estimated_monthly_rent = surface * estimated_rent_per_sqm
                                                annual_rent = estimated_monthly_rent * 12
                                                
                                                gross_yield = (annual_rent / price) * 100
                                                
                                                st.markdown("---")
                                                st.markdown('<h4 class="section-title">💰 Rentabilité estimée</h4>', unsafe_allow_html=True)
                                                
                                                col_r1, col_r2 = st.columns(2)
                                                with col_r1:
                                                    st.metric("Loyer estimé", f"{estimated_monthly_rent:,.0f} €/mois")
                                                with col_r2:
                                                    if gross_yield >= 7:
                                                        yield_icon = "🟢"
                                                    elif gross_yield >= 5:
                                                        yield_icon = "🟡"
                                                    else:
                                                        yield_icon = "🔴"
                                                    st.metric("Rendement brut", f"{yield_icon} {gross_yield:.1f}%")
                                        
                                        else:
                                            st.warning("ℹ️ Données DVF non disponibles pour cette localisation")
                                    
                                    except Exception as e:
                                        st.warning(f"Erreur DVF : {str(e)}")
                                else:
                                    st.info("📍 Localisation nécessaire pour l'analyse DVF")
                            
                            # Bouton pour passer à l'analyse détaillée
                            st.markdown("---")
                            if st.button("📈 Passer à l'analyse détaillée", key="to_detailed"):
                                # Pré-remplir les données dans la session
                                st.session_state.update({
                                    'property_price': property_data.get('price', 0),
                                    'property_surface': property_data.get('surface', 0),
                                    'property_location': property_data.get('city', property_data.get('location', '')),
                                    'property_rooms': property_data.get('rooms', 0),
                                    'current_tab': 'detailed_analysis'
                                })
                                st.rerun()
                        
                        else:
                            st.error("❌ Impossible d'extraire les données de cette annonce. Vérifiez l'URL.")
                    
                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'extraction : {str(e)}")

def show_detailed_analysis():
    """Page d'analyse détaillée avec formulaire complet"""
    
    # Marge en haut pour le bouton retour
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Header avec retour accueil
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("🏠 Accueil", key="home_from_detailed"):
            st.session_state.current_tab = "home"
            st.rerun()
    
    with col2:
        st.markdown('<h2 class="section-title">📈 Analyse Détaillée</h2>', unsafe_allow_html=True)
    
    # Vérifier si on a des données extraites pour pré-remplir
    extracted_data = st.session_state.get('extracted_data')
    if extracted_data:
        st.info(f"📋 **Bien pré-rempli :** {extracted_data.get('title', 'Bien immobilier')} - {extracted_data.get('price', 0):,}€ - {extracted_data.get('surface', 0)} m²")
    
    # Structure d'investissement - Hors formulaire pour mise à jour temps réel
    st.subheader("🏛️ Structure d'investissement")
    type_investissement = st.selectbox(
        "Investissez-vous en nom propre ou via SCI ?", 
        options=["Nom propre", "SCI"], 
        index=0,
        key="type_investissement"
    )
    
    # Configuration SCI hors formulaire pour mise à jour temps réel
    nombre_associes = 2  # Valeur par défaut
    if type_investissement == "SCI":
        st.markdown("**🏢 Configuration SCI**")
        nombre_associes = st.number_input("Nombre d'associés", 
                                        min_value=1, max_value=4, value=2, step=1,
                                        key="nb_associes_sci")
    
    # Formulaire principal complet
    with st.form("detailed_analysis"):
        # Section 1: Informations du bien (pré-remplie si données extraites)
        st.subheader("🏠 Informations du bien")
        col1, col2 = st.columns(2)
        
        with col1:
            price = st.number_input("Prix d'achat (€)", 
                                  min_value=0, 
                                  value=extracted_data.get('price', 0) if extracted_data else 0, 
                                  step=1000)
            surface = st.number_input("Surface (m²)", 
                                    min_value=0.0, 
                                    value=float(extracted_data.get('surface', 0)) if extracted_data else 0.0, 
                                    step=0.1)
            type_bien = st.selectbox("Neuf ou Occasion ?", options=["Occasion", "Neuf"], index=0)
            cout_renovation = st.number_input("Coût des travaux de rénovation (€)", min_value=0, value=0, step=500)
            
        with col2:
            location = st.text_input("Ville/Code postal", 
                                   value=extracted_data.get('city', extracted_data.get('location', '')) if extracted_data else '')
            rooms = st.number_input("Nombre de pièces", 
                                  min_value=1, 
                                  value=max(extracted_data.get('rooms', 3), 1) if extracted_data else 3)
            cout_construction = st.number_input("Coût des travaux de construction (€)", min_value=0, value=0, step=500)
        
        # Section 2: Données locatives
        st.subheader("💰 Données locatives")
        col1, col2 = st.columns(2)
        
        with col1:
            loyer_hc = st.number_input("Loyer mensuel HC estimé (€)", 
                                     min_value=0, 
                                     value=int(surface * 15) if surface > 0 else 800, 
                                     step=25)
            
        with col2:
            loyer_cc = st.number_input("Loyer mensuel CC estimé (€)", 
                                     min_value=0, 
                                     value=int(surface * 16) if surface > 0 else 850, 
                                     step=25)
        
        # Section 3: Financement
        st.subheader("🏦 Financement")
        col1, col2 = st.columns(2)
        
        with col1:
            utilise_pret = st.selectbox("Vous utilisez un prêt ?", options=["Oui", "Non"], index=0)
            apport_default = int(price * 0.15) if price > 0 else 0  # 15% du prix
            apport = st.number_input("Combien d'apport (€)", min_value=0, value=apport_default, step=1000)
            
        with col2:
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
            capital_sci = st.number_input("Capital de la SCI (€)", 
                                        min_value=0, value=1000, step=100)
            
            # Informations pour chaque associé
            associes = []
            for i in range(int(nombre_associes)):
                st.markdown(f"**👤 Associé {i+1}**")
                col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                
                with col_a1:
                    # Calcul automatique de la répartition égale
                    part_default = round(100.0 / nombre_associes, 1)
                    part = st.number_input(f"Part détenue (%)", 
                                         min_value=0.0, max_value=100.0, 
                                         value=part_default, 
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
        estimation_revente_default = int(price * 1.2) if price > 0 else 0  # 120% du prix
        estimation_revente = st.number_input("Estimation à la revente (€)", 
                                           min_value=0, value=estimation_revente_default, step=5000)
        
        submitted = st.form_submit_button("📁 Générer l'analyse Excel complète", type="primary", use_container_width=True)
    
    # HORS du formulaire - Traitement et téléchargement
    if submitted and price > 0 and surface > 0:
        # Sauvegarder les données dans la session pour traitement hors formulaire
        st.session_state['excel_generation_data'] = {
            'property_data': {
                'price': price,
                'surface': surface,
                'city': location,
                'location': location,
                'rooms': rooms,
                'title': f"Bien {rooms}P - {location}"
            },
            'additional_data': {
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
            }
        }
        st.session_state['generate_excel'] = True
    
    # Traitement HORS formulaire
    if st.session_state.get('generate_excel', False):
        generation_data = st.session_state.get('excel_generation_data')
        if generation_data:
            # Créer l'analyse avec Google Sheets + Excel
            excel_file = generate_google_sheets_analysis(
                generation_data['property_data'], 
                generation_data['additional_data']
            )
            
            if excel_file:
                st.success("✅ Analyse générée avec succès !")
            
            # Réinitialiser le flag pour éviter la génération en boucle
            st.session_state['generate_excel'] = False

def generate_google_sheets_analysis(property_data, additional_data):
    """
    Génère une analyse avec Google Sheets et crée les indicateurs visuels.
    Version simplifiée : modification directe du template + téléchargement.
    
    Args:
        property_data (dict): Données du bien (prix, surface, ville, etc.)
        additional_data (dict): Données supplémentaires du formulaire
        
    Returns:
        bool: True si succès, False sinon
    """
    try:
        with st.spinner("🔄 Génération de l'analyse en cours..."):
            # Initialiser le gestionnaire Google Sheets
            gs_manager = GoogleSheetsManager()
            
            # Connexion à Google Sheets
            if not gs_manager.connect():
                st.error("❌ Erreur de connexion à Google Sheets")
                return False
            
            # Mise à jour des données dans le template principal
            if not gs_manager.update_property_data(property_data, additional_data):
                st.error("❌ Erreur de mise à jour des données")
                return False
            
            # ============================================================================
            # CRÉATION DES INDICATEURS VISUELS
            # ============================================================================
            
            st.markdown("---")
            st.markdown("### 📊 Indicateurs basés sur Google Sheets")
            
            # Section 1: Camembert des charges
            charges_data = gs_manager.get_charges_data()
            if charges_data:
                create_charges_pie_chart(charges_data)
            else:
                st.warning("⚠️ Impossible de récupérer les données des charges")
            
            # Section 2: Indicateurs fiscaux
            st.markdown("---")
            donnees_fiscales = additional_data.get('donnees_fiscales', {})
            type_regime = donnees_fiscales.get('type', 'nom_propre')
            
            if type_regime:
                st.markdown(f"### 📋 Analyse fiscale - Régime {type_regime.replace('_', ' ').title()}")
                create_fiscalite_charts(gs_manager, type_regime)
            
            # Section 3: Plus-value
            st.markdown("---")
            create_plus_value_chart(gs_manager)
            
            # Section 4: Amortissement du prêt
            st.markdown("---")
            create_amortissement_chart(gs_manager)
            
            # ============================================================================
            # EXPORT EXCEL POUR TÉLÉCHARGEMENT (OpenPyXL - Local) - HORS FORMULAIRE
            # ============================================================================
            
            st.markdown("---")
            st.markdown("### 📥 Téléchargement Excel")
            
            # Générer l'analyse Excel locale
            excel_manager = generate_excel_analysis(property_data, additional_data)
            
            if excel_manager:
                # Créer le bouton de téléchargement HORS du contexte de formulaire
                excel_manager.create_download_button(property_data)
            else:
                st.error("❌ Erreur génération fichier Excel")
            
            # ============================================================================ 
            # INFORMATIONS COMPLÉMENTAIRES
            # ============================================================================
            
            st.markdown("---")
            with st.expander("ℹ️ À propos de cette analyse"):
                st.markdown("""
                **🔄 Double approche :**
                - **Indicateurs temps réel** : Calculés via Google Sheets API
                - **Téléchargement Excel** : Copie locale modifiée avec OpenPyXL
                
                **✅ Avantages :**
                - **Fiabilité** : Pas de problème de quota Google Drive
                - **Performance** : Traitement local rapide
                - **Compatibilité** : Excel natif avec toutes les formules
                - **Autonomie** : Fonctionne hors ligne après téléchargement
                
                **🔄 Données synchronisées :**
                Les indicateurs affichés et le fichier Excel contiennent exactement les mêmes données.
                """)
            
            return True
            
    except Exception as e:
        st.error(f"❌ Erreur analyse Google Sheets : {str(e)}")
        return False

def create_charges_pie_chart(charges_data):
    """Crée le camembert des charges annuelles à partir des données Google Sheets."""
    try:
        df_charges = pd.DataFrame(charges_data)
        
        if df_charges.empty:
            st.warning("⚠️ Aucune donnée de charges trouvée")
            return
        
        # ============================================================================
        # CAMEMBERT PROFESSIONNEL
        # ============================================================================
        
        st.subheader("💰 Répartition des charges annuelles")
        st.caption("*Données calculées en temps réel depuis Google Sheets*")
        
        # Couleurs sobres et professionnelles
        colors_sober = [
            '#2C3E50', '#34495E', '#5D6D7E', '#85929E', 
            '#AEB6BF', '#D5DBDB', '#BDC3C7', '#95A5A6',
            '#7F8C8D', '#566573'
        ]
        
        # Créer le camembert avec Plotly
        fig_pie = px.pie(
            df_charges, 
            values='valeur', 
            names='libelle',
            title="Répartition des charges annuelles",
            color_discrete_sequence=colors_sober
        )
        
        # Personnalisation du graphique avec € dans le hover
        fig_pie.update_traces(
            textposition='inside', 
            textinfo='percent+label',
            textfont_size=11,
            marker=dict(line=dict(color='#FFFFFF', width=2)),
            hovertemplate='<b>%{label}</b><br>' +
                         'Montant: %{value:,.0f} €<br>' +
                         'Pourcentage: %{percent}<br>' +
                         '<extra></extra>'
        )
        
        fig_pie.update_layout(
            height=550,
            showlegend=True,
            title_font_size=18,
            title_x=0.5,
            font=dict(size=12),
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.05
            )
        )
        
        # Afficher le graphique
        st.plotly_chart(fig_pie, use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ Erreur création camembert : {str(e)}")

def create_fiscalite_charts(gs_manager, type_regime):
    """Crée les graphiques fiscaux selon le régime (nom_propre ou sci)"""
    try:
        if type_regime == "nom_propre":
            create_nom_propre_charts(gs_manager)
        elif type_regime == "sci":
            # Pour SCI : aucun indicateur selon votre demande
            st.info("📊 Aucun indicateur spécifique affiché pour le régime SCI")
    except Exception as e:
        st.error(f"❌ Erreur création graphiques fiscaux : {str(e)}")

def create_nom_propre_charts(gs_manager):
    """Crée les graphiques pour le régime Nom propre - avec tous les histogrammes"""
    try:
        data = gs_manager.get_fiscalite_data("nom_propre")
        if not data:
            st.warning("⚠️ Aucune donnée fiscale Nom propre trouvée")
            return
        
        # Couleurs cohérentes
        colors_sober = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#5D737E', '#64A6BD', '#90A959']
        
        # 1. Rentabilité brut/net de charges
        if data.get('rentabilite'):
            st.subheader("📊 Rentabilité de l'investissement")
            df_rentabilite = pd.DataFrame(data['rentabilite'])
            
            fig_rentabilite = px.bar(
                df_rentabilite, 
                x='libelle', 
                y='valeur',
                title="Rentabilité brute vs nette de charges",
                color_discrete_sequence=colors_sober
            )
            
            fig_rentabilite.update_traces(
                hovertemplate='<b>%{x}</b><br>Rentabilité: %{y:.2f}%<extra></extra>'
            )
            
            fig_rentabilite.update_layout(
                xaxis_title="Type de rentabilité",
                yaxis_title="Pourcentage (%)",
                showlegend=False
            )
            
            st.plotly_chart(fig_rentabilite, use_container_width=True)
        
        # 2. Rentabilité nette avec impôts
        if data.get('rentabilite_nette'):
            st.subheader("💰 Rentabilité nette (impôts compris)")
            df_rentabilite_nette = pd.DataFrame(data['rentabilite_nette'])
            
            fig_rentabilite_nette = px.bar(
                df_rentabilite_nette, 
                x='libelle', 
                y='valeur',
                title="Rentabilité nette après imposition",
                color_discrete_sequence=colors_sober[1:]
            )
            
            fig_rentabilite_nette.update_traces(
                hovertemplate='<b>%{x}</b><br>Rentabilité: %{y:.2f}%<extra></extra>'
            )
            
            fig_rentabilite_nette.update_layout(
                xaxis_title="Période/Type",
                yaxis_title="Pourcentage (%)",
                showlegend=False
            )
            
            st.plotly_chart(fig_rentabilite_nette, use_container_width=True)
        
        # 3. Cash mensuel
        if data.get('cash_mensuel'):
            st.subheader("💵 Cash-flow mensuel")
            df_cash = pd.DataFrame(data['cash_mensuel'])
            
            fig_cash = px.bar(
                df_cash, 
                x='libelle', 
                y='valeur',
                title="Cash-flow mensuel par catégorie",
                color_discrete_sequence=colors_sober[2:]
            )
            
            fig_cash.update_traces(
                hovertemplate='<b>%{x}</b><br>Montant: %{y:,.0f} €<extra></extra>'
            )
            
            fig_cash.update_layout(
                xaxis_title="Catégorie",
                yaxis_title="Montant (€)",
                showlegend=False
            )
            
            st.plotly_chart(fig_cash, use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ Erreur graphiques Nom propre : {str(e)}")

def create_sci_charts(gs_manager):
    """Crée les graphiques pour le régime SCI"""
    try:
        data = gs_manager.get_fiscalite_data("sci")
        if not data:
            st.warning("⚠️ Aucune donnée fiscale SCI trouvée")
            return
        
        # Cash mensuel par associé
        if data.get('cash_associes'):
            st.subheader("👥 Cash mensuel par associé après imposition")
            
            df_sci = pd.DataFrame(data['cash_associes'])
            
            # Transformer les données pour l'affichage
            df_melted = pd.melt(
                df_sci, 
                id_vars=['associe'], 
                value_vars=['ir', 'is'],
                var_name='regime',
                value_name='cash'
            )
            
            # Renommer les régimes
            df_melted['regime'] = df_melted['regime'].map({
                'ir': 'SCI à l\'IR',
                'is': 'SCI à l\'IS'
            })
            
            fig_sci = px.bar(
                df_melted, 
                x='associe', 
                y='cash',
                color='regime',
                title="Cash mensuel par associé selon le régime fiscal",
                barmode='group',
                color_discrete_map={
                    'SCI à l\'IR': '#2E86AB',
                    'SCI à l\'IS': '#A23B72'
                }
            )
            
            fig_sci.update_traces(
                hovertemplate='<b>%{x}</b><br>%{fullData.name}<br>Cash: %{y:,.0f} €<extra></extra>'
            )
            
            fig_sci.update_layout(
                xaxis_title="Associés",
                yaxis_title="Cash mensuel (€)",
                legend_title="Régime fiscal"
            )
            
            st.plotly_chart(fig_sci, use_container_width=True)
            
            # Note explicative APRÈS le graphique
            dividendes_pct = data.get('dividendes_pct', 0)
            st.info(f"📊 **SCI à l'IS** : cash mensuel calculé sur la base des dividendes distribués à hauteur de : **{dividendes_pct:.1f}%**")
            
    except Exception as e:
        st.error(f"❌ Erreur graphiques SCI : {str(e)}")

def create_plus_value_chart(gs_manager):
    """Crée le graphique de plus-value selon la durée de détention"""
    try:
        st.subheader("📈 Plus-value selon la durée de détention")
        
        data = gs_manager.get_plus_value_data()
        if not data:
            st.warning("⚠️ Aucune donnée de plus-value trouvée")
            return
        
        df_plus_value = pd.DataFrame(data)
        
        if df_plus_value.empty:
            st.warning("⚠️ Aucune donnée de plus-value valide")
            return
        
        fig_plus_value = go.Figure()
        
        # Courbe plus-value après imposition
        fig_plus_value.add_trace(go.Scatter(
            x=df_plus_value['duree'],
            y=df_plus_value['apres_imposition'],
            mode='lines+markers',
            name='Après imposition',
            line=dict(color='#2E86AB', width=3),
            marker=dict(size=6),
            hovertemplate='<b>Après imposition</b><br>Durée: %{x} ans<br>Plus-value: %{y:,.0f} €<extra></extra>'
        ))
        
        # Courbe plus-value avant imposition
        fig_plus_value.add_trace(go.Scatter(
            x=df_plus_value['duree'],
            y=df_plus_value['avant_imposition'],
            mode='lines+markers',
            name='Avant imposition',
            line=dict(color='#A23B72', width=3),
            marker=dict(size=6),
            hovertemplate='<b>Avant imposition</b><br>Durée: %{x} ans<br>Plus-value: %{y:,.0f} €<extra></extra>'
        ))
        
        fig_plus_value.update_layout(
            title="Évolution de la plus-value selon la durée de détention",
            xaxis_title="Durée de détention (années)",
            yaxis_title="Plus-value (€)",
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_plus_value, use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ Erreur graphique plus-value : {str(e)}")

def create_amortissement_chart(gs_manager):
    """Crée le graphique d'amortissement avec encadrés informatifs"""
    try:
        st.subheader("🏦 Amortissement du prêt")
        
        data = gs_manager.get_amortissement_data()
        if not data:
            st.warning("⚠️ Aucune donnée d'amortissement trouvée")
            return
        
        # Encadrés avec les informations clés
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="💰 Coût total du crédit",
                value=f"{data['cout_total']:,.0f} €"
            )
        
        with col2:
            st.metric(
                label="📅 Mensualité hors assurance",
                value=f"{data['mensualite_hors_assurance']:,.0f} €"
            )
        
        with col3:
            st.metric(
                label="�️ Mensualité avec assurance",
                value=f"{data['mensualite_avec_assurance']:,.0f} €"
            )
        
        # Graphique d'amortissement
        if data.get('tableau'):
            df_amortissement = pd.DataFrame(data['tableau'])
            
            if not df_amortissement.empty:
                # Limiter l'affichage à 60 mois pour la lisibilité
                df_display = df_amortissement.head(60)
                
                fig_amortissement = go.Figure()
                
                # Barres empilées : Capital en bas, Intérêts au-dessus
                fig_amortissement.add_trace(go.Bar(
                    x=df_display['mois'],
                    y=df_display['capital'],
                    name='Capital',
                    marker_color='#2E86AB',
                    hovertemplate='<b>%{x}</b><br>Capital: %{y:,.0f} €<extra></extra>'
                ))
                
                fig_amortissement.add_trace(go.Bar(
                    x=df_display['mois'],
                    y=df_display['interets'],
                    name='Intérêts',
                    marker_color='#A23B72',
                    hovertemplate='<b>%{x}</b><br>Intérêts: %{y:,.0f} €<extra></extra>'
                ))
                
                fig_amortissement.update_layout(
                    title="Répartition capital/intérêts par mensualité",
                    xaxis_title="Mois",
                    yaxis_title="Montant (€)",
                    barmode='stack',
                    hovermode='x unified'
                )
                
                # Masquer les étiquettes de l'axe X si trop nombreuses
                if len(df_display) > 24:
                    fig_amortissement.update_xaxes(showticklabels=False)
                
                st.plotly_chart(fig_amortissement, use_container_width=True)
                
                if len(df_amortissement) > 60:
                    st.info(f"📊 Affichage limité aux 60 premiers mois (sur {len(df_amortissement)} total)")
        
    except Exception as e:
        st.error(f"❌ Erreur graphique amortissement : {str(e)}")
        # Récupération des données pré-remplies si elles existent
        pre_price = st.session_state.get('property_price', 0)
        pre_surface = st.session_state.get('property_surface', 0)
        pre_location = st.session_state.get('property_location', '')
        pre_rooms = st.session_state.get('property_rooms', 0)
        
        # Formulaire principal
        with st.form("detailed_analysis_form"):
            # Informations du bien
            st.markdown('<h3 class="section-title">🏠 Informations du bien</h3>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                price = st.number_input("Prix d'achat (€)", min_value=0, value=pre_price, step=1000)
                surface = st.number_input("Surface (m²)", min_value=0.0, value=float(pre_surface), step=0.1)
                
            with col2:
                location = st.text_input("Ville/Code postal", value=pre_location)
                rooms = st.number_input("Nombre de pièces", min_value=1, value=max(pre_rooms, 1))
            
            # Données financières
            st.markdown('<h3 class="section-title">💰 Données financières</h3>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                rent = st.number_input("Loyer mensuel estimé (€)", min_value=0, step=50)
                notary_fees = st.number_input("Frais de notaire (%)", min_value=0.0, max_value=15.0, value=7.5, step=0.1)
                
            with col2:
                monthly_charges = st.number_input("Charges mensuelles (€)", min_value=0, step=25)
                renovation_cost = st.number_input("Coût travaux (€)", min_value=0, step=1000)
            
            # Financement
            st.markdown('<h3 class="section-title">🏦 Financement</h3>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                loan_amount = st.number_input("Montant emprunté (€)", min_value=0, value=int(price * 0.8) if price > 0 else 0, step=1000)
                interest_rate = st.number_input("Taux d'intérêt (%)", min_value=0.0, max_value=10.0, value=3.5, step=0.1)
                
            with col2:
                loan_duration = st.number_input("Durée emprunt (années)", min_value=1, max_value=30, value=20)
                insurance_rate = st.number_input("Assurance emprunteur (%)", min_value=0.0, max_value=1.0, value=0.36, step=0.01)
            
            # Fiscalité
            st.markdown('<h3 class="section-title">📋 Fiscalité</h3>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                tax_rate = st.number_input("Taux imposition (%)", min_value=0.0, max_value=50.0, value=30.0, step=1.0)
                property_tax = st.number_input("Taxe foncière annuelle (€)", min_value=0, step=100)
                
            with col2:
                management_fees = st.number_input("Frais de gestion (%)", min_value=0.0, max_value=15.0, value=8.0, step=0.5)
                vacancy_rate = st.number_input("Taux de vacance (%)", min_value=0.0, max_value=50.0, value=5.0, step=1.0)
            
            # Bouton de soumission
            submitted = st.form_submit_button("📊 Générer l'analyse complète", use_container_width=True)
        
        # Traitement du formulaire
        if submitted and price > 0 and surface > 0:
            # Préparation des données
            property_data = {
                'price': price,
                'surface': surface,
                'location': location,
                'rooms': rooms,
                'rent': rent,
                'notary_fees': notary_fees,
                'monthly_charges': monthly_charges,
                'renovation_cost': renovation_cost,
                'loan_amount': loan_amount,
                'interest_rate': interest_rate,
                'loan_duration': loan_duration,
                'insurance_rate': insurance_rate,
                'tax_rate': tax_rate,
                'property_tax': property_tax,
                'management_fees': management_fees,
                'vacancy_rate': vacancy_rate
            }
            
            generate_analysis_and_excel(property_data)

def generate_analysis_and_excel(property_data):
    """Génère l'analyse et le fichier Excel"""
    
    with st.spinner("🔄 Génération de l'analyse en cours..."):
        try:
            # Calculs de rentabilité
            calculator = RentabilityCalculator()
            results = calculator.calculate_full_analysis(property_data)
            
            # Affichage des résultats
            display_analysis_results(results)
            
            # Génération du fichier Excel
            excel_file_path = generate_excel_analysis(property_data, results)
            
            if excel_file_path and os.path.exists(excel_file_path):
                # Bouton de téléchargement
                with open(excel_file_path, "rb") as file:
                    st.download_button(
                        label="📥 Télécharger le rapport Excel",
                        data=file.read(),
                        file_name=f"Analyse_Rendimo_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                
                # Nettoyage du fichier temporaire
                try:
                    os.remove(excel_file_path)
                except:
                    pass
            
        except Exception as e:
            st.error(f"❌ Erreur lors de l'analyse : {str(e)}")

def display_analysis_results(results):
    """Affiche les résultats de l'analyse"""
    
    st.markdown('<h3 class="section-title">📊 Résultats de l\'analyse</h3>', unsafe_allow_html=True)
    
    # Indicateurs principaux
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Rendement brut",
            f"{results.get('gross_yield', 0):.2f}%",
            delta=f"{results.get('gross_yield', 0) - 5:.2f}% vs 5%"
        )
    
    with col2:
        st.metric(
            "Rendement net",
            f"{results.get('net_yield', 0):.2f}%",
            delta=f"{results.get('net_yield', 0) - 3:.2f}% vs 3%"
        )
    
    with col3:
        st.metric(
            "Cash-flow mensuel",
            f"{results.get('monthly_cashflow', 0):.0f} €",
            delta="Positif" if results.get('monthly_cashflow', 0) > 0 else "Négatif"
        )
    
    with col4:
        st.metric(
            "ROI (10 ans)",
            f"{results.get('roi_10_years', 0):.1f}%"
        )
    
    # Graphiques si disponibles
    if results.get('charts'):
        st.markdown('<h3 class="section-title">📈 Graphiques d\'analyse</h3>', unsafe_allow_html=True)
        
        # Exemple de graphique de cash-flow
        if 'cashflow_projection' in results.get('charts', {}):
            st.plotly_chart(results['charts']['cashflow_projection'], use_container_width=True)
        
        # Exemple de répartition des coûts
        if 'cost_breakdown' in results.get('charts', {}):
            st.plotly_chart(results['charts']['cost_breakdown'], use_container_width=True)

if __name__ == "__main__":
    main()