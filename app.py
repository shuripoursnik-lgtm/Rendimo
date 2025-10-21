"""
Rendimo - Assistant IA Immobilier (Version Simplifiée)
Application Streamlit pour l'analyse d'investissements immobiliers

Auteur: Assistant IA
Date: Octobre 2024
"""

import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Import des modules essentiels seulement
from utils.scraper import LeBonCoinScraper
from utils.calculator import RentabilityCalculator
from utils.immo_api import ImmoAPI
from api.ai_assistant import AIAssistant

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
    """Interface principale simplifiée"""
    
    # Header
    st.markdown('<h1 class="main-header">🏠 Rendimo - Assistant IA Immobilier</h1>', unsafe_allow_html=True)
    
    # Layout principal avec deux colonnes
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Section Analyse
        st.header("🔍 Analyse de bien")
        
        # Onglets simplifiés
        tab1, tab2 = st.tabs(["🔗 URL LeBonCoin", "📝 Saisie manuelle"])
        
        with tab1:
            st.write("**Analyser une annonce LeBonCoin :**")
            
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
const surface = document.body.textContent.match(/(\d+)\s*m²/)?.[1];
console.log('Surface:', surface + ' m²');

// Pièces
const rooms = document.body.textContent.match(/(\d+)\s*pièce/i)?.[1];
console.log('Pièces:', rooms);
```

4. **Copier les résultats** dans "Saisie manuelle"
                    
📖 **Guide complet :** `GUIDE_INSPECTEUR.md`""")

def chat_interface():
    """Interface de chat simplifiée"""
    
    # Affichage des messages
    for message in st.session_state.chat_history:
        if message['role'] == 'user':
            st.markdown(f'<div class="chat-message user-message"><strong>Vous:</strong> {message["content"]}</div>', 
                       unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-message assistant-message"><strong>Assistant:</strong> {message["content"]}</div>', 
                       unsafe_allow_html=True)
    
    # Saisie de message
    user_input = st.text_input("Posez votre question :", 
                              placeholder="Ex: Qu'est-ce que la rentabilité locative ?")
    
    if st.button("Envoyer"):
        if user_input.strip():
            handle_chat_message(user_input.strip())

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
        
        # Calculs de rentabilité simples
        st.subheader("📊 Analyse rapide")
        
        if property_data.get('price', 0) > 0 and property_data.get('surface', 0) > 0:
            # Estimation loyer (prix/m² local * 0.8% par mois)
            estimated_rent = int(property_data['price'] * 0.008)  # 0.8% par mois approximatif
            
            col_calc1, col_calc2 = st.columns(2)
            with col_calc1:
                st.metric("Loyer estimé/mois", f"{estimated_rent}€", help="Estimation basée sur 0.8% du prix")
            with col_calc2:
                if estimated_rent > 0:
                    annual_yield = (estimated_rent * 12 / property_data['price']) * 100
                    st.metric("Rentabilité brute", f"{annual_yield:.1f}%")
        
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
    """Estime un bien avec l'API"""
    try:
        with st.spinner("🔍 Estimation en cours..."):
            api = ImmoAPI()
            estimation = api.estimate_property_value(
                property_data.get('surface', 0),
                property_data.get('rooms', 0),
                property_data.get('city', ''),
                property_data.get('property_type', 'Appartement')
            )
            
            if estimation.get('estimated_value'):
                st.success(f"💰 **Valeur estimée :** {estimation['estimated_value']:,}€")
                
                # Comparaison avec le prix annoncé
                asking_price = property_data.get('price', 0)
                if asking_price > 0:
                    difference = asking_price - estimation['estimated_value']
                    percentage = (difference / estimation['estimated_value']) * 100
                    
                    if percentage > 10:
                        st.warning(f"⚠️ Prix supérieur de {percentage:.0f}% à l'estimation")
                    elif percentage < -10:
                        st.success(f"✅ Bon prix ! {abs(percentage):.0f}% en dessous de l'estimation")
                    else:
                        st.info(f"ℹ️ Prix proche de l'estimation ({percentage:+.0f}%)")
                        
                add_chat_message("assistant", f"📊 **Estimation réalisée :** {estimation['estimated_value']:,}€ pour ce bien")
            else:
                st.warning("⚠️ Estimation impossible avec les données disponibles")
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