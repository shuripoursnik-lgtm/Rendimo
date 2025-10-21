"""
Assistant IA conversationnel pour Rendimo
Intégration avec Groq et OpenAI pour les conseils immobiliers

Auteur: Assistant IA
Date: Octobre 2024
"""

import logging
import os
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Imports conditionnels des APIs
try:
    # Chargement optionnel des variables d'environnement depuis .env
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # Pas bloquant si python-dotenv n'est pas installé
    pass
try:
    import groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("groq non disponible")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openai non disponible")

class AIAssistant:
    """
    Assistant IA conversationnel spécialisé en immobilier
    
    Cette classe fournit un chatbot intelligent capable de :
    - Répondre aux questions sur l'investissement immobilier
    - Analyser les données des biens
    - Donner des conseils personnalisés
    - Guider l'utilisateur dans son questionnaire
    """
    
    def __init__(self):
        """Initialise l'assistant IA avec les clés API disponibles"""
        self.groq_client = None
        self.openai_client = None
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        # Température plus basse pour des réponses plus précises et cohérentes
        self.generation_temperature = float(os.getenv("AI_TEMPERATURE", "0.2"))
        
        # Configuration Groq
        groq_api_key = os.getenv('GROQ_API_KEY')
        if groq_api_key and GROQ_AVAILABLE:
            try:
                self.groq_client = groq.Groq(api_key=groq_api_key)
                logger.info("Client Groq initialisé")
            except Exception as e:
                logger.error(f"Erreur initialisation Groq: {str(e)}")
        
        # Configuration OpenAI
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if openai_api_key and OPENAI_AVAILABLE:
            try:
                self.openai_client = openai.OpenAI(api_key=openai_api_key)
                logger.info("Client OpenAI initialisé")
            except Exception as e:
                logger.error(f"Erreur initialisation OpenAI: {str(e)}")
        
        # Messages système pour contextualiser l'assistant
        self.system_prompt = self._get_system_prompt()
        
        # État de la conversation
        self.conversation_state = {
            'questionnaire_active': False,
            'current_question': None,
            'collected_answers': {}
        }
        
        logger.info("Assistant IA Rendimo initialisé")
    
    def _get_system_prompt(self) -> str:
        """
        Définit le prompt système pour contextualiser l'assistant
        
        Returns:
            str: Prompt système complet
        """
        return """Tu es Rendimo, un assistant IA spécialisé dans l'investissement immobilier français.

Ton rôle :
- Aider les particuliers et investisseurs à analyser des biens immobiliers
- Fournir des conseils sur la rentabilité locative
- Expliquer les calculs financiers de manière simple
- Guider les utilisateurs dans leurs décisions d'investissement
- Répondre à TOUTES les questions liées à l'immobilier

Tes compétences :
- Analyse de rentabilité (brute, nette, cash-flow, ROI)
- Connaissance du marché immobilier français
- Fiscalité immobilière (SCI, LMNP, régimes fiscaux)
- Financement immobilier et négociation bancaire
- Gestion locative et droit immobilier
- Frais de notaire, assurances, diagnostics
- Stratégies d'investissement et diversification
- Rénovation et travaux
- Estimation de biens et négociation

Questions fréquentes que tu peux traiter :
- "Quels sont les frais de notaire pour un achat ?"
- "Comment calculer la rentabilité locative ?"
- "Qu'est-ce qu'une SCI et ses avantages ?"
- "Comment négocier le prix d'un bien ?"
- "Quelles sont les charges déductibles ?"
- "Comment obtenir le meilleur taux de crédit ?"
- "Que vérifier avant d'acheter ?"
- "Comment estimer le loyer de marché ?"

Ton style :
- Conversationnel et naturel
- Professionnel mais accessible
- Pédagogique et bienveillant
- Précis dans les chiffres avec exemples concrets
- Toujours mentionner les risques et limites
- Encourager à consulter des professionnels pour les décisions importantes

Utilise des émojis pour rendre tes réponses plus claires :
🏠 pour les biens immobiliers
💰 pour les aspects financiers
📊 pour les analyses et calculs
⚠️ pour les avertissements
✅ pour les points positifs
🔍 pour les analyses détaillées
📋 pour les listes et étapes
💡 pour les conseils et astuces
🎯 pour les objectifs
📞 pour les contacts professionnels

Réponds toujours en français et adapte ton niveau selon le niveau de connaissance apparent de l'utilisateur.
Si on te pose une question qui n'est pas liée à l'immobilier, oriente poliment la conversation vers ton domaine d'expertise.

Directives spécifiques SCI / LMNP / LMP (mise à jour 2025) :
- Si la question contient des termes comme "sci", "lmnp", "lmp", "meublé", "statut", "fiscalité", réponds de façon structurée :
    1) Définition et objectif
    2) Conditions d'éligibilité / seuils (ex: LMP si recettes > 23 000€ ET > autres revenus professionnels du foyer)
    3) Régime fiscal (micro-BIC vs réel, amortissements, déficits)
    4) Cotisations sociales (prélèvements sociaux LMNP vs cotisations SSI pour LMP)
    5) Plus-values à la revente (privées LMNP vs professionnelles LMP, exemptions possibles)
    6) Avantages / limites et quand choisir
    7) Exemple chiffré simple (si pertinent)
- Corrige gentiment les fautes usuelles (ex: "LMNA" → "LMNP") et clarifie les acronymes dès la première mention.
- Pour la SCI :
    • Par défaut, la SCI est à l'IR et convient surtout au nu; le meublé régulier rend l'activité commerciale → risque d'IS (ou opter pour l'IS).
    • Expose clairement les impacts d'une SCI à l'IS (amortissements, fiscalité des dividendes, plus-values professionnelles) vs IR.
    • Mentionne les alternatives (SARL de famille) pour de la location meublée si pertinent.

Toujours proposer une courte mise en garde : la fiscalité évolue et un avis d'expert-comptable est recommandé pour arbitrer.
"""

    def _normalize_user_message(self, text: str) -> str:
        """Normalise certaines abréviations/fautes fréquentes pour aider l'IA.

        Exemples: LMNA -> LMNP, lmna -> LMNP, lmnp/lmp en majuscules.
        """
        try:
            normalized = text
            # Corriger LMNA (faute fréquente) vers LMNP
            normalized = re.sub(r"\bLMNA\b", "LMNP", normalized, flags=re.IGNORECASE)
            # Uniformiser LMNP/LMP en majuscules
            normalized = re.sub(r"\blmnp\b", "LMNP", normalized, flags=re.IGNORECASE)
            normalized = re.sub(r"\blmp\b", "LMP", normalized, flags=re.IGNORECASE)
            # Uniformiser SCI en majuscules
            normalized = re.sub(r"\bsci\b", "SCI", normalized, flags=re.IGNORECASE)
            return normalized
        except Exception:
            return text
    
    def get_response(self, 
                    user_message: str,
                    chat_history: List[Dict],
                    property_data: Optional[Dict] = None) -> str:
        """
        Génère une réponse à un message utilisateur
        
        Args:
            user_message (str): Message de l'utilisateur
            chat_history (List[Dict]): Historique de la conversation
            property_data (Optional[Dict]): Données du bien analysé
            
        Returns:
            str: Réponse de l'assistant
        """
        logger.info(f"Génération de réponse pour: {user_message[:50]}...")
        
        try:
            # Construction du contexte
            context = self._build_context(chat_history, property_data)

            # Normalisation de la question (fautes usuelles)
            user_message = self._normalize_user_message(user_message)

            # Réponses déterministes pour thèmes sensibles (plus précises)
            lower_q = user_message.lower()
            if "sci" in lower_q:
                return self._get_sci_info()
            if any(k in lower_q for k in ["lmnp", "lmp", "meubl"]):
                return self._get_lmnp_vs_lmp_info()
            
            # Tentative avec Groq en priorité
            if self.groq_client:
                response = self._get_groq_response(user_message, context)
                if response:
                    return response
            
            # Fallback sur OpenAI
            if self.openai_client:
                response = self._get_openai_response(user_message, context)
                if response:
                    return response
            
            # Fallback ultime : réponse intelligente sans IA
            return self._get_fallback_response(user_message, property_data)
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de réponse: {str(e)}")
            return self._get_error_response()
    
    def _build_context(self, 
                      chat_history: List[Dict], 
                      property_data: Optional[Dict]) -> str:
        """
        Construit le contexte pour l'IA
        
        Args:
            chat_history: Historique des messages
            property_data: Données du bien
            
        Returns:
            str: Contexte formaté
        """
        context_parts = []
        
        # Ajout des données du bien si disponibles
        if property_data:
            context_parts.append("BIEN ANALYSÉ:")
            context_parts.append(f"- Ville: {property_data.get('city', 'N/A')}")
            context_parts.append(f"- Prix: {property_data.get('price', 'N/A')}€")
            context_parts.append(f"- Surface: {property_data.get('surface', 'N/A')} m²")
            context_parts.append(f"- Type: {property_data.get('property_type', 'N/A')}")
            if property_data.get('rooms'):
                context_parts.append(f"- Pièces: {property_data['rooms']}")
            context_parts.append("")
        
        # Ajout de l'historique récent (derniers 5 messages)
        if chat_history:
            context_parts.append("HISTORIQUE RÉCENT:")
            for message in chat_history[-5:]:
                role = "Utilisateur" if message['role'] == 'user' else "Assistant"
                context_parts.append(f"{role}: {message['content'][:100]}...")
            context_parts.append("")
        
        return '\n'.join(context_parts)
    
    def _get_groq_response(self, user_message: str, context: str) -> Optional[str]:
        """
        Obtient une réponse via l'API Groq
        
        Args:
            user_message: Message utilisateur
            context: Contexte de la conversation
            
        Returns:
            Optional[str]: Réponse ou None en cas d'erreur
        """
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "system", "content": f"CONTEXTE:\n{context}"},
                {"role": "user", "content": user_message}
            ]
            
            response = self.groq_client.chat.completions.create(
                model=self.groq_model,  # Modèle Groq configurable (par défaut 70B)
                messages=messages,
                temperature=self.generation_temperature,
                max_tokens=1000,
                top_p=1,
                stream=False
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Erreur Groq: {str(e)}")
            return None
    
    def _get_openai_response(self, user_message: str, context: str) -> Optional[str]:
        """
        Obtient une réponse via l'API OpenAI
        
        Args:
            user_message: Message utilisateur
            context: Contexte de la conversation
            
        Returns:
            Optional[str]: Réponse ou None en cas d'erreur
        """
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "system", "content": f"CONTEXTE:\n{context}"},
                {"role": "user", "content": user_message}
            ]
            
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,  # Modèle OpenAI configurable
                messages=messages,
                temperature=self.generation_temperature,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Erreur OpenAI: {str(e)}")
            return None
    
    def _get_fallback_response(self, 
                              user_message: str, 
                              property_data: Optional[Dict]) -> str:
        """
        Génère une réponse intelligente sans IA externe
        
        Args:
            user_message: Message utilisateur
            property_data: Données du bien
            
        Returns:
            str: Réponse de fallback
        """
        message_lower = user_message.lower()
        
        # Questions spécifiques SCI
        if "sci" in message_lower:
            return self._get_sci_info()

        # Questions LMNP / LMP / meublé
        if any(k in message_lower for k in ["lmnp", "lmp", "meubl"]):
            return self._get_lmnp_vs_lmp_info()

        # Questions sur les frais de notaire
        if any(word in message_lower for word in ['frais de notaire', 'notaire', 'frais d\'acquisition', 'frais achat']):
            return self._get_notary_fees_info()
        
        # Questions sur la rentabilité
        elif any(word in message_lower for word in ['rentabilité', 'rendement', 'yield']):
            return self._get_rentability_advice(property_data)
        
        # Questions sur le cashflow
        elif any(word in message_lower for word in ['cashflow', 'cash-flow', 'flux']):
            return self._get_cashflow_advice(property_data)
        
        # Questions sur les prix et négociation
        elif any(word in message_lower for word in ['prix', 'cher', 'marché', 'négocier', 'négociation']):
            return self._get_price_advice(property_data)
        
        # Questions sur l'investissement général
        elif any(word in message_lower for word in ['investissement', 'investir', 'achat', 'commencer']):
            return self._get_investment_advice()
        
        # Questions fiscales et SCI
        elif any(word in message_lower for word in ['fiscalité', 'impôt', 'sci', 'lmnp', 'déficit foncier']):
            return self._get_tax_advice()
        
        # Questions sur le financement
        elif any(word in message_lower for word in ['financement', 'prêt', 'crédit', 'banque', 'taux']):
            return self._get_financing_advice()
        
        # Questions sur les assurances
        elif any(word in message_lower for word in ['assurance', 'pno', 'gli', 'multirisque']):
            return self._get_insurance_advice()
        
        # Questions sur la gestion locative
        elif any(word in message_lower for word in ['gestion locative', 'locataire', 'bail', 'loyer']):
            return self._get_rental_management_advice()
        
        # Questions sur les travaux
        elif any(word in message_lower for word in ['travaux', 'rénovation', 'réhabilitation']):
            return self._get_renovation_advice()
        
        # Questions sur les diagnostics
        elif any(word in message_lower for word in ['diagnostic', 'dpe', 'amiante', 'plomb']):
            return self._get_diagnostics_info()
        
        # Questions sur la copropriété
        elif any(word in message_lower for word in ['copropriété', 'syndic', 'ag', 'charges']):
            return self._get_copropriety_advice()
        
        else:
            return self._get_general_response()

    def _get_sci_info(self) -> str:
        """Explication structurée de la SCI (IR/IS, usages, limites)."""
        return (
            "🏛️ Qu'est-ce qu'une SCI (Société Civile Immobilière) ?\n\n"
            "Définition: Structure juridique pour détenir et gérer un patrimoine immobilier à plusieurs (ou seul).\n\n"
            "🎯 Objectifs courants:\n"
            "• Gestion familiale d'un bien\n"
            "• Transmission (donations, démembrement) facilitée\n"
            "• Mutualiser l'investissement entre associés\n\n"
            "📚 Régimes fiscaux:\n"
            "• Par défaut: SCI à l'IR (impôt sur le revenu) → adaptée à la location nue (revenus fonciers).\n"
            "• À l'IS (option ou bascule si activité commerciale): adaptée si amortissements recherchés, mais\n"
            "  fiscalité différente à la revente (plus-values professionnelles) et double niveau d'imposition (IS + dividendes).\n\n"
            "🛋️ Location meublée et SCI:\n"
            "• Une SCI à l'IR n'est pas faite pour du meublé régulier (activité commerciale).\n"
            "• Si meublé récurrent: risque d'assujettissement à l'IS. Alternatives: SARL de famille au réel, LMNP/LMP en nom propre.\n\n"
            "✅ Avantages:\n"
            "• Souplesse statutaire (pactes entre associés)\n"
            "• Transmission progressive (donations de parts)\n"
            "• Séparation patrimoine perso / immobilier\n\n"
            "⚠️ Limites:\n"
            "• Frais (création, comptabilité, assemblées)\n"
            "• Moins adaptée au meublé régulier (risque IS)\n"
            "• À l'IS: impôt sur la société + taxation des dividendes, plus-values moins favorables\n\n"
            "💡 En pratique: privilégier SCI-IR pour du nu patrimonial. Pour du meublé récurrent, envisager LMNP/LMP en nom propre ou SARL de famille.\n"
            "Consultez un expert pour arbitrer IR vs IS selon vos objectifs et horizon de détention."
        )

    def _get_lmnp_vs_lmp_info(self) -> str:
        """Différences clés entre LMNP et LMP avec structure claire."""
        return (
            "🛋️ Location meublée: LMNP vs LMP\n\n"
            "1) Définitions:\n"
            "• LMNP (Loueur en Meublé Non Professionnel): activité meublée à titre non pro.\n"
            "• LMP (Loueur en Meublé Professionnel): statut pro selon critères.\n\n"
            "2) Conditions du LMP (cumulatives):\n"
            "• Recettes annuelles meublées > 23 000 €\n"
            "• ET supérieures aux autres revenus professionnels du foyer fiscal\n\n"
            "3) Régime fiscal (BIC):\n"
            "• Micro-BIC: abattement forfaitaire (seuil révisé périodiquement, ex ~77 700 €; à vérifier chaque année).\n"
            "• Réel: charges réelles + amortissements (hors terrain), souvent plus avantageux en meublé.\n\n"
            "4) Cotisations sociales:\n"
            "• LMNP: en général, prélèvements sociaux (17,2%) sur le résultat (si imposable).\n"
            "• LMP: cotisations sociales (SSI) sur le bénéfice, taux globaux significatifs (à estimer avec un expert).\n\n"
            "5) Plus-values à la revente:\n"
            "• LMNP: régime des plus-values des particuliers (abattements dans le temps).\n"
            "• LMP: plus-values professionnelles (possibles exonérations sous conditions: durée d'activité, CA, etc.).\n\n"
            "6) Avantages / limites:\n"
            "• LMNP: simplicité, amortissements au réel, souvent optimisant l'impôt. Limite: statut non pro.\n"
            "• LMP: reconnaissance professionnelle et exonérations possibles, mais charges sociales et complexité accrues.\n\n"
            "7) Quand choisir ?\n"
            "• Visez LMNP réel si vous débutez/optimisez l'impôt.\n"
            "• LMP possible si recettes importantes et stratégie long terme; à valider selon vos revenus pro.\n\n"
            "💡 Conseils: simulez MICRO vs RÉEL (amortissements) et anticipez cotisations/plus-values. Un expert-comptable est vivement recommandé."
        )
    
    def _get_notary_fees_info(self) -> str:
        """Informations sur les frais de notaire"""
        return """📋 **Frais de notaire et d'acquisition :**

💰 **Répartition des frais :**
• **Droits de mutation** : ~5,8% (ancien) / ~2,5% (neuf)
• **Honoraires du notaire** : ~1% (plafonné)
• **Frais et débours** : ~0,5% (hypothèque, cadastre...)

🏠 **Exemples concrets :**
• Bien ancien 300k€ → ~21-24k€ de frais
• Bien neuf 300k€ → ~10-12k€ de frais

📊 **Calcul rapide :**
• **Ancien** : Prix × 8% (règle approximative)
• **Neuf** : Prix × 3-4%

💡 **Astuces pour économiser :**
• Négocier le prix mobilier séparément
• Vérifier l'ancienneté réelle du bien
• Comparer les honoraires entre notaires

⚠️ **Attention :** Ces frais ne sont pas finançables, il faut les avoir en apport personnel !

🔍 **Simulateur officiel :** site des notaires de France pour un calcul précis."""
    
    def _get_insurance_advice(self) -> str:
        """Conseils sur les assurances immobilières"""
        return """🛡️ **Assurances immobilières essentielles :**

🏠 **Pour le propriétaire :**
• **PNO** (Propriétaire Non Occupant) : Obligatoire
  - Couvre incendie, dégâts des eaux, catastrophes
  - Prix : 200-400€/an selon le bien
  - Prendre en compte dans la rentabilité

• **GLI** (Garantie Loyers Impayés) : Recommandée
  - Couvre loyers impayés + dégradations
  - Prix : 2-4% du loyer annuel
  - Alternative aux cautions traditionnelles

🏛️ **En copropriété :**
• Assurance syndic obligatoire (incluse charges)
• Vérifier les garanties du contrat d'ensemble
• Franchise et plafonds importants

💡 **Conseils d'optimisation :**
• Comparer annuellement (loi Hamon)
• Grouper avec assurance habitation principale
• Vérifier les franchises et exclusions
• Négocier si plusieurs biens

📞 **Assureurs spécialisés :** Axa, Maif, Macif, Allianz, GMF

⚠️ **Ne jamais négliger l'assurance** - Les sinistres peuvent coûter très cher !"""
    
    def _get_rental_management_advice(self) -> str:
        """Conseils sur la gestion locative"""
        return """🏠 **Guide de la gestion locative :**

👤 **Gestion par vous-même :**
✅ Avantages : Économie (pas de commission), contrôle total
❌ Inconvénients : Temps, stress, connaissances juridiques

🏢 **Gestion par une agence :**
✅ Avantages : Délégation complète, expertise juridique
❌ Inconvénients : Commission 6-10% des loyers

📋 **Tâches de gestion :**
• Recherche et sélection des locataires
• État des lieux d'entrée et sortie
• Encaissement des loyers
• Gestion des réparations et travaux
• Relations avec les locataires

📝 **Documents essentiels :**
• Bail de location (type Alur)
• État des lieux détaillé
• Dossier locataire complet
• Quittances de loyer
• Appels de charges

💡 **Conseils pour bien choisir :**
• Dossier locataire : 3×loyer en revenus nets
• Caution : 1-2 mois de loyer
• Assurance habitation obligatoire
• Clause de solidarité si couple

⚠️ **Droits et devoirs :** Se former au droit locatif ou déléguer à un professionnel."""
    
    def _get_renovation_advice(self) -> str:
        """Conseils sur les travaux et rénovation"""
        return """🔨 **Guide des travaux immobiliers :**

💰 **Budget travaux par m² :**
• **Rafraîchissement** : 200-400€/m²
• **Rénovation complète** : 800-1200€/m²  
• **Rénovation lourde** : 1200-2000€/m²

🏠 **Priorités par ordre :**
1. **Structure** : Toiture, fondations, murs porteurs
2. **Technique** : Électricité, plomberie, chauffage
3. **Isolation** : Thermique et phonique
4. **Finitions** : Sol, peinture, cuisine, salle de bain

📋 **Travaux déductibles (revenus fonciers) :**
✅ Réparations et entretien
✅ Amélioration (dans certaines limites)
❌ Agrandissement ou construction

💡 **Astuces pour économiser :**
• Faire plusieurs devis (minimum 3)
• Grouper les travaux
• Négocier les prix
• Vérifier assurances et garanties

🎯 **Travaux rentables en locatif :**
• Création de pièces supplémentaires
• Amélioration énergétique (DPE)
• Modernisation salle de bain/cuisine
• Isolation phonique

⚠️ **Attention :** Prévoir toujours 20% de plus que le devis initial !

📞 **Professionnels :** Architecte, maître d'œuvre, artisans certifiés RGE."""
    
    def _get_diagnostics_info(self) -> str:
        """Informations sur les diagnostics immobiliers"""
        return """📋 **Diagnostics immobiliers obligatoires :**

🏠 **Pour la vente :**
• **DPE** (Diagnostic Performance Énergétique) - 10 ans
• **Amiante** - Illimité si négatif, 3 ans si positif  
• **Plomb** - 1 an (bâtiments avant 1949)
• **Termites** - 6 mois (zones à risque)
• **Gaz** - 3 ans (installations +15 ans)
• **Électricité** - 3 ans (installations +15 ans)
• **Assainissement** - 3 ans (maisons)

🏠 **Pour la location :**
• **DPE** - Obligatoire
• **Plomb** - Si avant 1949
• **Gaz/Électricité** - Si installations anciennes

💰 **Coûts moyens :**
• DPE : 150-300€
• Pack complet vente : 500-800€
• Diagnostiqueur certifié obligatoire

⚠️ **Nouveau DPE 2021 :**
• Plus contraignant (seuils F et G)
• Impact sur la valeur des biens
• Interdiction location G (2025), F (2028)

🎯 **Conséquences des mauvaises notes :**
• Décote importante (10-20%)
• Difficultés de financement
• Travaux d'amélioration nécessaires

💡 **Conseil :** Faire réaliser les diagnostics avant la mise en vente pour éviter les mauvaises surprises !"""
    
    def _get_copropriety_advice(self) -> str:
        """Conseils sur la copropriété"""
        return """🏢 **Comprendre la copropriété :**

📋 **Documents essentiels :**
• **Règlement de copropriété** : Règles de vie
• **Carnet d'entretien** : Historique travaux
• **PV d'AG** (3 dernières années) : Décisions prises
• **Budgets prévisionnels** : Charges futures

💰 **Types de charges :**
• **Générales** : Ascenseur, ménage, chauffage
• **Spéciales** : Selon les équipements  
• **Travaux** : Provisions pour gros travaux

🔍 **Points de vigilance :**
• État financier du syndic
• Travaux votés non encore réalisés
• Litiges en cours
• Fonds de travaux disponible

📊 **Charges moyennes :**
• Immeuble sans ascenseur : 25-35€/m²/an
• Immeuble avec ascenseur : 35-50€/m²/an
• Résidence avec services : 50-80€/m²/an

⚠️ **Signaux d'alarme :**
• Charges impayées importantes
• Absence d'entretien visible
• Nombreux conflits en AG
• Syndic débordé

💡 **Astuces :**
• Assister à une AG avant achat
• Rencontrer le syndic et concierge
• Vérifier l'état des parties communes
• Calculer l'impact charges sur rentabilité

🎯 **Pour l'investissement :** Les charges impactent directement la rentabilité !"""
    
    def _get_rentability_advice(self, property_data: Optional[Dict]) -> str:
        """Conseils sur la rentabilité"""
        base_advice = """🏠 **Conseils sur la rentabilité immobilière :**

📊 **Indicateurs clés :**
• **Rentabilité brute** : (Loyers annuels / Prix d'achat) × 100
• **Rentabilité nette** : (Loyers - charges) / Prix d'achat × 100
• **Cash-flow** : Revenus - (charges + mensualités prêt)

✅ **Bonnes rentabilités selon le marché :**
• Grande ville : 3-5% net
• Ville moyenne : 4-6% net  
• Petite ville : 5-8% net

⚠️ **Attention :** Une rentabilité très élevée (>8%) peut cacher des risques (mauvais quartier, vacance locative élevée, travaux importants)."""
        
        if property_data and property_data.get('city'):
            city_advice = f"\n\n🔍 Pour votre bien à {property_data['city']}, je recommande de viser une rentabilité nette d'au moins 4-5%."
            base_advice += city_advice
        
        return base_advice
    
    def _get_cashflow_advice(self, property_data: Optional[Dict]) -> str:
        """Conseils sur le cash-flow"""
        return """💰 **Comprendre le cash-flow immobilier :**

📈 **Cash-flow positif :**
• Revenus locatifs > toutes les charges
• Permet de dégager des revenus mensuels
• Idéal pour l'investissement locatif

📉 **Cash-flow négatif :**
• Vous devez compléter chaque mois
• Acceptable si l'objectif est la plus-value à long terme
• Attention à votre capacité financière

🎯 **Optimisation :**
• Négocier le prix d'achat
• Augmenter les loyers (dans la limite légale)
• Réduire les charges (syndic, assurance)
• Défiscalisation (LMNP, Pinel, etc.)

💡 Un cash-flow légèrement négatif (-50€/mois) peut être acceptable si la plus-value est importante."""
    
    def _get_price_advice(self, property_data: Optional[Dict]) -> str:
        """Conseils sur les prix"""
        advice = """💶 **Analyse des prix immobiliers :**

🔍 **Comment évaluer un prix :**
• Comparer avec les ventes récentes du quartier
• Utiliser le prix au m² comme référence
• Considérer l'état du bien et les travaux nécessaires
• Analyser l'évolution du marché local

📊 **Sources de données :**
• DVF (Demandes de Valeurs Foncières) - gratuit
• Sites d'estimation (SeLoger, MeilleursAgents)
• Notaires et agents immobiliers locaux

💡 **Négociation :**
• Une décote de 5-10% est souvent possible
• Arguments : travaux, marché, délais
• Rester respectueux et réaliste"""
        
        if property_data:
            price = property_data.get('price', 0)
            surface = property_data.get('surface', 0)
            if price and surface:
                price_per_sqm = price / surface
                advice += f"\n\n🏠 Votre bien : {price_per_sqm:,.0f}€/m²"
                advice += "\nJe vais comparer ce prix avec le marché local pour vous donner mon analyse."
        
        return advice
    
    def _get_investment_advice(self) -> str:
        """Conseils généraux sur l'investissement"""
        return """🏠 **Guide de l'investissement immobilier :**

🎯 **Définir ses objectifs :**
• Revenus complémentaires (locatif)
• Constitution d'un patrimoine
• Préparation de la retraite
• Réduction d'impôts

📋 **Étapes clés :**
1. **Budget** : Apport + capacité d'emprunt
2. **Zone** : Demande locative, prix, évolution
3. **Type de bien** : Studio, T2, maison...
4. **Financement** : Taux, durée, assurance
5. **Gestion** : Vous-même ou via une agence

✅ **Règles d'or :**
• Emplacement, emplacement, emplacement !
• Diversifier si possible (plusieurs biens)
• Prévoir une réserve pour les imprévus
• Se former continuellement

⚠️ **Risques :** Vacance locative, travaux imprévus, évolution du marché, changements fiscaux."""
    
    def _get_tax_advice(self) -> str:
        """Conseils fiscaux"""
        return """📋 **Fiscalité de l'investissement immobilier :**

🏛️ **Régimes fiscaux :**
• **Revenus fonciers** (déficit foncier possible)
• **LMNP** (Location Meublée Non Professionnelle)
• **LMP** (Location Meublée Professionnelle)

🏢 **SCI (Société Civile Immobilière) :**
✅ Avantages : Gestion familiale, transmission facilitée
❌ Inconvénients : Comptabilité, pas de déficit foncier

💡 **Dispositifs d'aide :**
• **Pinel** : Réduction d'impôt (zones éligibles)
• **Denormandie** : Rénovation dans l'ancien
• **Malraux** : Monuments historiques

⚠️ **Important :** La fiscalité change régulièrement. Consultez impérativement un expert-comptable ou conseiller en gestion de patrimoine pour optimiser votre situation."""
    
    def _get_financing_advice(self) -> str:
        """Conseils sur le financement"""
        return """💳 **Financement de votre investissement :**

🏦 **Capacité d'emprunt :**
• Taux d'endettement max : 35% (revenus nets)
• Reste à vivre suffisant
• Stabilité professionnelle
• Apport recommandé : 10-20% minimum

📊 **Négociation du prêt :**
• Comparer plusieurs banques
• Utiliser un courtier si nécessaire
• Négocier le taux, l'assurance, les frais
• Considérer la modularité (report d'échéances)

💰 **Types de prêts :**
• **Prêt amortissable** : Le plus courant
• **Prêt in fine** : Remboursement du capital à la fin
• **Prêt relais** : Pour financer avant une vente

🎯 **Stratégies :**
• Effet de levier : Emprunter pour démultiplier
• Lissage fiscal avec les intérêts d'emprunt
• Assurance emprunteur : négociable et résiliable

📞 Pensez à faire jouer la concurrence entre les banques !"""
    
    def _get_general_response(self) -> str:
        """Réponse générale"""
        return """👋 Je suis Rendimo, votre assistant IA spécialisé en investissement immobilier !

🔍 **Ce que je peux vous aider à faire :**
• Analyser la rentabilité d'un bien immobilier
• Comparer les prix avec le marché local
• Vous conseiller sur le financement
• Expliquer la fiscalité immobilière
• Calculer cash-flow et ROI

🏠 **Pour commencer :**
Collez l'URL d'une annonce LeBonCoin que vous souhaitez analyser, ou posez-moi directement vos questions sur l'immobilier !

💡 **Domaines d'expertise :**
• Investissement locatif
• Achat résidence principale  
• SCI et optimisation fiscale
• Stratégies d'investissement

N'hésitez pas à me poser vos questions ! 😊"""
    
    def _get_error_response(self) -> str:
        """Réponse en cas d'erreur"""
        return """😅 Désolé, je rencontre un petit problème technique pour vous répondre.

🔄 **Vous pouvez essayer de :**
• Reformuler votre question
• Vérifier votre connexion internet
• Réessayer dans quelques instants

💡 En attendant, n'hésitez pas à explorer les autres fonctionnalités de l'application !

Si le problème persiste, cela peut être lié à la configuration des APIs (Groq/OpenAI). Vérifiez vos clés API dans le fichier `.env`."""
    
    def start_questionnaire(self, property_data: Dict) -> str:
        """
        Démarre le questionnaire d'analyse financière
        
        Args:
            property_data: Données du bien
            
        Returns:
            str: Premier message du questionnaire
        """
        self.conversation_state['questionnaire_active'] = True
        self.conversation_state['current_question'] = 'investment_type'
        self.conversation_state['collected_answers'] = {}
        
        return f"""🏠 **Parfait ! J'ai analysé le bien à {property_data.get('city', 'N/A')}.**

Pour calculer la rentabilité précise, j'ai besoin de quelques informations :

**1️⃣ Type d'investissement :**
• 🏠 Achat pour habiter (résidence principale)
• 💰 Investissement locatif (mise en location)
• 📈 Achat-revente (plus-value à court terme)

Quel est votre projet avec ce bien ?"""
    
    def process_questionnaire_answer(self, answer: str) -> str:
        """
        Traite une réponse du questionnaire
        
        Args:
            answer: Réponse de l'utilisateur
            
        Returns:
            str: Question suivante ou fin du questionnaire
        """
        current_q = self.conversation_state.get('current_question')
        
        if current_q == 'investment_type':
            # Traitement de la réponse sur le type d'investissement
            answer_lower = answer.lower()
            if 'locatif' in answer_lower or 'investissement' in answer_lower:
                self.conversation_state['collected_answers']['investment_type'] = 'rental'
                self.conversation_state['current_question'] = 'monthly_rent'
                return """✅ **Investissement locatif** - Excellent choix !

**2️⃣ Loyer mensuel estimé :**
💰 À combien estimez-vous pouvoir louer ce bien par mois ? (en euros)

💡 *Astuce : Consultez les annonces similaires sur LeBonCoin, SeLoger ou PAP pour estimer le loyer de marché.*"""
            
            elif 'personnel' in answer_lower or 'habiter' in answer_lower:
                self.conversation_state['collected_answers']['investment_type'] = 'personal'
                return self._finish_personal_analysis()
            
            elif 'revente' in answer_lower or 'plus-value' in answer_lower:
                self.conversation_state['collected_answers']['investment_type'] = 'flip'
                return self._finish_flip_analysis()
        
        elif current_q == 'monthly_rent':
            # Traitement du loyer mensuel
            try:
                rent = float(answer.replace('€', '').replace(' ', '').replace(',', '.'))
                self.conversation_state['collected_answers']['monthly_rent'] = rent
                self.conversation_state['current_question'] = 'annual_charges'
                return f"""✅ **Loyer : {rent:.0f}€/mois**

**3️⃣ Charges annuelles :**
🏢 Quel est le montant des charges de copropriété par an ? (en euros)

💡 *Cette information se trouve généralement dans l'annonce ou vous pouvez demander au vendeur/agent.*"""
            except ValueError:
                return "❌ Merci de saisir un montant en euros (ex: 850 ou 850€)"
        
        elif current_q == 'annual_charges':
            # Traitement des charges
            try:
                charges = float(answer.replace('€', '').replace(' ', '').replace(',', '.'))
                self.conversation_state['collected_answers']['annual_charges'] = charges
                self.conversation_state['current_question'] = 'ownership_type'
                return f"""✅ **Charges : {charges:.0f}€/an**

**4️⃣ Mode de propriété :**
📋 Comment comptez-vous acheter ?
• 👤 En nom propre (personne physique)
• 🏛️ Via une SCI (Société Civile Immobilière)
• 👥 En indivision (avec d'autres personnes)"""
            except ValueError:
                return "❌ Merci de saisir un montant en euros (ex: 1200 ou 1200€)"
        
        elif current_q == 'ownership_type':
            # Finalisation du questionnaire
            answer_lower = answer.lower()
            if 'sci' in answer_lower:
                self.conversation_state['collected_answers']['ownership_type'] = 'sci'
            elif 'indivision' in answer_lower:
                self.conversation_state['collected_answers']['ownership_type'] = 'joint'
            else:
                self.conversation_state['collected_answers']['ownership_type'] = 'personal'
            
            return self._finish_rental_analysis()
        
        return "❓ Je n'ai pas bien compris votre réponse. Pouvez-vous la reformuler ?"
    
    def _finish_rental_analysis(self) -> str:
        """Finalise l'analyse pour un investissement locatif"""
        answers = self.conversation_state['collected_answers']
        
        return f"""✅ **Analyse terminée !**

📊 **Récapitulatif de vos réponses :**
• Type : Investissement locatif
• Loyer mensuel : {answers.get('monthly_rent', 0):.0f}€
• Charges annuelles : {answers.get('annual_charges', 0):.0f}€  
• Propriété : {answers.get('ownership_type', 'nom propre')}

🔄 **Calcul en cours...**
Je vais maintenant calculer la rentabilité brute, nette, le cash-flow et le ROI. 

Les résultats apparaîtront dans la section "Analyse du bien" à droite de votre écran.

💡 **Prochaines étapes :**
• Consultez le tableau d'analyse détaillée
• Téléchargez le rapport Excel complet
• Comparez avec le marché local

Des questions sur les résultats ? N'hésitez pas à me demander ! 😊"""
    
    def _finish_personal_analysis(self) -> str:
        """Finalise l'analyse pour un achat personnel"""
        return """🏠 **Achat résidence principale**

Pour un achat personnel, les critères d'analyse sont différents :

📍 **Points clés à vérifier :**
• Emplacement et commodités (transports, commerces, écoles)
• État du bien et travaux nécessaires  
• Évolution du quartier
• Capacité de financement
• Coût total (notaire, travaux, déménagement)

💰 **Conseils financiers :**
• Prévoir 8-10% de frais d'acquisition
• Garder une épargne de précaution
• Négocier le taux d'emprunt
• Vérifier l'éligibilité aux aides (PTZ, etc.)

🔍 Je vais tout de même analyser le prix au m² par rapport au marché local pour vous donner une idée de la valorisation du bien."""
    
    def _finish_flip_analysis(self) -> str:
        """Finalise l'analyse pour un achat-revente"""
        return """📈 **Achat-revente (investissement court terme)**

⚠️ **Attention : Investissement à haut risque !**

💡 **Facteurs de réussite :**
• Bien sous-évalué ou à rénover
• Marché porteur (demande > offre)
• Travaux maîtrisés (coût et délais)
• Fiscalité des plus-values immobilières
• Frais de transaction importants (achat + vente)

📊 **Calculs nécessaires :**
• Prix d'achat + frais + travaux
• Prix de revente estimé
• Délai de revente
• Fiscalité (plus-value = revenus si < 5 ans)

🏗️ **Types de biens favorables :**
• Appartements à rénover en centre-ville
• Maisons avec potentiel d'extension
• Biens atypiques sous-évalués

💼 **Je recommande fortement de consulter un professionnel pour ce type d'investissement.**"""

# Fonction utilitaire pour tester le module
def test_ai_assistant():
    """Fonction de test pour l'assistant IA"""
    assistant = AIAssistant()
    
    print("Test de l'assistant IA Rendimo...")
    
    # Test de réponse simple
    response = assistant.get_response("Qu'est-ce que la rentabilité immobilière ?", [])
    print(f"Réponse: {response[:200]}...")
    
    # Test avec données de bien
    property_data = {
        'city': 'Lyon',
        'price': 250000,
        'surface': 60,
        'property_type': 'Appartement'
    }
    
    response = assistant.get_response("Ce bien est-il rentable ?", [], property_data)
    print(f"\nRéponse avec contexte: {response[:200]}...")

if __name__ == "__main__":
    test_ai_assistant()