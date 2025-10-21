# 🔧 Guide de Dépannage Rendimo

## 🚫 Problème: "Échec de l'extraction des données LeBonCoin"

### Causes possibles:

#### 1. **Erreur 403 Forbidden**
- **Cause**: LeBonCoin bloque les requêtes automatisées
- **Solutions**:
  - Attendre quelques minutes avant de réessayer
  - Vérifier que l'URL est correcte et accessible dans un navigateur
  - Essayer avec une annonce différente

#### 2. **URL invalide**
- **Cause**: L'URL n'est pas une annonce immobilière LeBonCoin
- **Solutions**:
  - Vérifier que l'URL commence par `https://www.leboncoin.fr/ventes_immobilieres/`
  - Copier-coller l'URL complète depuis votre navigateur

#### 3. **Annonce expirée ou supprimée**
- **Cause**: L'annonce n'existe plus
- **Solutions**:
  - Essayer avec une annonce récente
  - Vérifier que l'annonce s'ouvre dans votre navigateur

## 🔍 Comment tester le scraper

1. **Test rapide** dans l'application:
   - Coller une URL d'annonce récente
   - Observer les messages dans la console

2. **Test détaillé** avec le script de diagnostic:
   ```bash
   python test_scraper.py "https://www.leboncoin.fr/ventes_immobilieres/..."
   ```

## 💡 Conseils d'utilisation

### ✅ URLs qui fonctionnent bien:
- Annonces récentes (moins de 24h)
- Annonces d'appartements ou maisons
- URLs complètes copiées depuis le navigateur

### ❌ URLs problématiques:
- Annonces très anciennes
- Recherches ou listes d'annonces
- URLs raccourcies ou modifiées

## 🛠️ Solutions de contournement

Si l'extraction automatique échoue:

1. **Saisie manuelle**:
   - Entrer les informations manuellement dans l'interface
   - Prix, surface, ville, etc.

2. **Capture d'écran**:
   - Faire une capture de l'annonce
   - Extraire les infos visuellement

3. **Copier-coller**:
   - Copier le texte de l'annonce
   - Coller dans le chat pour analyse par l'IA

## 🤖 Utilisation du chatbot

Même sans extraction automatique, vous pouvez:
- Poser toutes vos questions immobilières
- Demander des calculs de rentabilité
- Obtenir des conseils d'investissement

## 📞 Support

Si le problème persiste:
1. Vérifier les logs détaillés avec `test_scraper.py`
2. Essayer avec plusieurs annonces différentes
3. Redémarrer l'application
4. Vérifier votre connexion internet

---

💡 **Astuce**: Le chatbot reste pleinement fonctionnel même sans scraping automatique. N'hésitez pas à lui poser directement vos questions !