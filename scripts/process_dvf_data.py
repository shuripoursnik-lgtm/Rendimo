"""
Script de traitement des données DVF
Extrait les prix moyens au m² par ville et type de bien

Auteur: Assistant IA
Date: Octobre 2025
"""

import pandas as pd
import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_dvf_file(input_file: str, output_db: str = "data/dvf_prices.sqlite"):
    """
    Traite le fichier DVF et crée une base SQLite optimisée
    
    Args:
        input_file: Chemin vers le fichier DVF (CSV)
        output_db: Chemin de sortie pour la base SQLite
    """
    
    logger.info(f"📂 Lecture du fichier DVF: {input_file}")
    
    # Colonnes du fichier DVF (format texte pipe-delimited)
    columns_to_use = [
        'Date mutation',
        'Nature mutation',
        'Valeur fonciere',
        'Code postal',
        'Commune',
        'Type local',
        'Surface reelle bati',
        'Nombre pieces principales'
    ]
    
    try:
        # Lecture fichier texte pipe-delimited
        logger.info("📊 Chargement des données...")
        df = pd.read_csv(
            input_file,
            sep='|',  # Séparateur pipe
            usecols=columns_to_use,
            dtype={
                'Code postal': str,
                'Valeur fonciere': str,  # String car peut contenir des espaces
                'Surface reelle bati': str
            },
            low_memory=False,
            encoding='utf-8'
        )
        
        # Renommer les colonnes pour cohérence
        df.columns = df.columns.str.strip()  # Enlever espaces
        df = df.rename(columns={
            'Date mutation': 'date_mutation',
            'Nature mutation': 'nature_mutation',
            'Valeur fonciere': 'valeur_fonciere',
            'Code postal': 'code_postal',
            'Commune': 'nom_commune',
            'Type local': 'type_local',
            'Surface reelle bati': 'surface_reelle_bati',
            'Nombre pieces principales': 'nombre_pieces_principales'
        })
        
        # Convertir les types
        df['date_mutation'] = pd.to_datetime(df['date_mutation'], format='%d/%m/%Y', errors='coerce')
        df['valeur_fonciere'] = pd.to_numeric(df['valeur_fonciere'].str.replace(',', '.'), errors='coerce')
        df['surface_reelle_bati'] = pd.to_numeric(df['surface_reelle_bati'].str.replace(',', '.'), errors='coerce')
        
        logger.info(f"✅ {len(df):,} transactions chargées")
        
        # Nettoyage des données
        logger.info("🧹 Nettoyage des données...")
        
        # Filtrer uniquement les ventes (pas donations, etc.)
        df = df[df['nature_mutation'] == 'Vente']
        
        # Filtrer premier semestre 2025
        df = df[
            (df['date_mutation'] >= '2025-01-01') & 
            (df['date_mutation'] <= '2025-06-30')
        ]
        
        # Supprimer les valeurs aberrantes
        df = df[df['valeur_fonciere'] > 0]
        df = df[df['surface_reelle_bati'] > 0]
        df = df[df['surface_reelle_bati'] < 1000]  # Exclure surfaces > 1000m²
        
        # Calculer prix au m²
        df['price_per_sqm'] = df['valeur_fonciere'] / df['surface_reelle_bati']
        
        # Filtrer prix aberrants (< 500€/m² ou > 50000€/m²)
        df = df[
            (df['price_per_sqm'] >= 500) & 
            (df['price_per_sqm'] <= 50000)
        ]
        
        # Normaliser type de bien
        def normalize_type(type_local):
            if pd.isna(type_local):
                return 'other'
            type_local = str(type_local).lower()
            if 'appartement' in type_local:
                return 'apartment'
            elif 'maison' in type_local:
                return 'house'
            else:
                return 'other'
        
        df['property_type'] = df['type_local'].apply(normalize_type)
        
        # Nettoyer nom de ville
        df['nom_commune'] = df['nom_commune'].str.strip().str.title()
        
        logger.info(f"✅ {len(df):,} transactions valides après nettoyage")
        
        # Calcul des statistiques par ville et type
        logger.info("📈 Calcul des prix moyens par ville...")
        
        stats = df.groupby(['nom_commune', 'code_postal', 'property_type']).agg({
            'price_per_sqm': ['mean', 'median', 'std', 'count'],
            'valeur_fonciere': ['mean', 'median'],
            'surface_reelle_bati': 'mean'
        }).reset_index()
        
        # Aplatir les colonnes multi-niveaux
        stats.columns = [
            'city',
            'postal_code',
            'property_type',
            'price_per_sqm_mean',
            'price_per_sqm_median',
            'price_per_sqm_std',
            'transaction_count',
            'price_mean',
            'price_median',
            'surface_mean'
        ]
        
        # Arrondir les valeurs
        stats['price_per_sqm_mean'] = stats['price_per_sqm_mean'].round(0).astype(int)
        stats['price_per_sqm_median'] = stats['price_per_sqm_median'].round(0).astype(int)
        stats['transaction_count'] = stats['transaction_count'].astype(int)
        
        # Calculer score de fiabilité basé sur nombre de transactions
        def calculate_reliability(count):
            if count >= 100:
                return 95
            elif count >= 50:
                return 90
            elif count >= 20:
                return 85
            elif count >= 10:
                return 75
            elif count >= 5:
                return 65
            else:
                return 50
        
        stats['reliability_score'] = stats['transaction_count'].apply(calculate_reliability)
        
        logger.info(f"✅ {len(stats):,} villes × types calculés")
        
        # Afficher aperçu des meilleures données
        logger.info("\n📊 Top 10 villes (appartements) :")
        top_cities = stats[
            (stats['property_type'] == 'apartment') & 
            (stats['transaction_count'] >= 10)
        ].nlargest(10, 'price_per_sqm_mean')[
            ['city', 'postal_code', 'price_per_sqm_mean', 'transaction_count', 'reliability_score']
        ]
        print(top_cities.to_string(index=False))
        
        # Sauvegarder dans SQLite
        logger.info(f"\n💾 Sauvegarde dans {output_db}...")
        
        # Créer le dossier data si nécessaire
        Path(output_db).parent.mkdir(parents=True, exist_ok=True)
        
        # Connexion SQLite
        conn = sqlite3.connect(output_db)
        
        # Sauvegarder le DataFrame
        stats.to_sql('price_data', conn, if_exists='replace', index=False)
        
        # Créer index pour recherches rapides
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_city 
            ON price_data(city)
        ''')
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_postal_code 
            ON price_data(postal_code)
        ''')
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_property_type 
            ON price_data(property_type)
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Base de données créée : {output_db}")
        logger.info(f"📊 Statistiques :")
        logger.info(f"   - Villes uniques : {stats['city'].nunique():,}")
        logger.info(f"   - Codes postaux : {stats['postal_code'].nunique():,}")
        logger.info(f"   - Total lignes : {len(stats):,}")
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Erreur : {str(e)}")
        raise


def create_lite_version(full_db: str, lite_db: str, top_n_cities: int = 50):
    """
    Crée une version allégée avec uniquement les N plus grandes villes
    
    Args:
        full_db: Base complète
        lite_db: Base allégée de sortie
        top_n_cities: Nombre de villes à garder
    """
    logger.info(f"📦 Création version Lite ({top_n_cities} villes)...")
    
    conn_full = sqlite3.connect(full_db)
    df = pd.read_sql("SELECT * FROM price_data", conn_full)
    conn_full.close()
    
    # Identifier les top N villes par nombre total de transactions
    top_cities = df.groupby('city')['transaction_count'].sum().nlargest(top_n_cities).index
    
    # Filtrer
    df_lite = df[df['city'].isin(top_cities)]
    
    # Sauvegarder
    conn_lite = sqlite3.connect(lite_db)
    df_lite.to_sql('price_data', conn_lite, if_exists='replace', index=False)
    
    # Index
    conn_lite.execute('CREATE INDEX idx_city ON price_data(city)')
    conn_lite.execute('CREATE INDEX idx_postal_code ON price_data(postal_code)')
    conn_lite.execute('CREATE INDEX idx_property_type ON price_data(property_type)')
    
    conn_lite.commit()
    conn_lite.close()
    
    logger.info(f"✅ Version Lite créée : {lite_db}")
    logger.info(f"   - {len(df_lite):,} lignes (vs {len(df):,} dans version complète)")
    logger.info(f"   - Villes : {', '.join(sorted(top_cities)[:10])}...")


def test_database(db_path: str):
    """Teste la base de données créée"""
    logger.info(f"\n🧪 Test de la base {db_path}...")
    
    conn = sqlite3.connect(db_path)
    
    # Test requête Paris appartement
    query = """
        SELECT city, postal_code, property_type, 
               price_per_sqm_mean, transaction_count, reliability_score
        FROM price_data
        WHERE city LIKE '%Paris%' AND property_type = 'apartment'
        LIMIT 5
    """
    
    df = pd.read_sql(query, conn)
    print("\n📍 Test Paris appartements :")
    print(df.to_string(index=False))
    
    conn.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python process_dvf_data.py <fichier_dvf.csv>")
        print("Exemple: python process_dvf_data.py data/dvf_2025_s1.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    # Traiter le fichier complet
    stats = process_dvf_file(
        input_file,
        output_db="data/dvf_prices_full.sqlite"
    )
    
    # Créer version Lite
    create_lite_version(
        full_db="data/dvf_prices_full.sqlite",
        lite_db="data/dvf_prices_lite.sqlite",
        top_n_cities=50
    )
    
    # Tester
    test_database("data/dvf_prices_lite.sqlite")
    
    print("\n✅ Traitement terminé !")
    print("📁 Fichiers créés :")
    print("   - data/dvf_prices_full.sqlite (base complète)")
    print("   - data/dvf_prices_lite.sqlite (50 plus grandes villes)")
