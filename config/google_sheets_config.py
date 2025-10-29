"""
Configuration pour Google Sheets API
"""

# ID du Google Sheet (extrait de l'URL)
GOOGLE_SHEET_ID = "15Ekcu0KFpJwn1-mwDQPWBxBZmRswAvvztn3_QntLaJ8"

# Nom du fichier (pour référence)
GOOGLE_SHEET_NAME = "Rendimmo - Simulateur Rentabilité"

# Noms des feuilles (worksheets)
SHEETS_MAPPING = {
    "frais_notaire": "Frais de notaire",
    "cout_rendement": "Coûts et rendement", 
    "nom_propre": "Nom propre - Fiscalité",
    "sci": "SCI",
    "plus_value": "Plus value",
    "amortissement": "Amortissement"
}

# Mapping des cellules importantes
CELL_MAPPING = {
    # Feuille "Frais de notaire"
    "prix_bien": ("Frais de notaire", "I3"),
    "type_bien": ("Frais de notaire", "F3"),
    
    # Feuille "Coûts et rendement"
    "loyer_hc": ("Coûts et rendement", "D7"),
    "loyer_cc": ("Coûts et rendement", "D8"),
    "surface": ("Coûts et rendement", "D9"),
    "utilise_pret": ("Coûts et rendement", "D14"),
    "duree_pret": ("Coûts et rendement", "D15"),
    "apport": ("Coûts et rendement", "D16"),
    "taux_pret": ("Coûts et rendement", "D17"),
    "travaux_reno": ("Coûts et rendement", "D21"),
    "travaux_construction": ("Coûts et rendement", "D22"),
    
    # Zone des charges pour indicateurs
    "charges_labels": ("Coûts et rendement", "F18:F27"),
    "charges_values": ("Coûts et rendement", "G18:G27"),
    
    # Plus value
    "estimation_revente": ("Plus value", "E7")
}

# Scopes nécessaires pour l'API Google Sheets
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]