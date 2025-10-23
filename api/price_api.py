"""
Module d'intégration des APIs de prix immobiliers
Récupère et compare les prix au m² du marché local

Auteur: Assistant IA
Date: Octobre 2024
"""

import os
import json
import time
import logging
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from statistics import median
from urllib.parse import quote

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PriceAPI:
    """
    Classe pour intégrer différentes APIs de prix immobiliers
    
    Cette classe permet de récupérer les prix au m² depuis différentes sources :
    - API Data.gouv (DVF - Demandes de Valeurs Foncières)
    - API MeilleursAgents (si clé disponible)
    - API Castorus (si clé disponible)
    """
    
    def __init__(self, meilleurs_agents_key: Optional[str] = None):
        """
        Initialise le client API
        
        Args:
            meilleurs_agents_key (Optional[str]): Clé API MeilleursAgents
        """
        self.meilleurs_agents_key = meilleurs_agents_key
        self.session = requests.Session()
        
        # URLs des APIs
        self.dvf_base_url = "https://apidf-preprod.apur.org/api/dvf/opendata"
        self.data_gouv_url = "https://api.gouv.fr/api/api-dvf.html"
        self.geo_api_url = "https://geo.api.gouv.fr/communes"
        
        # Headers par défaut
        self.session.headers.update({
            'User-Agent': 'Rendimo-Assistant/1.0',
            'Accept': 'application/json'
        })

        # Cache mémoire + disque (24h)
        self._mem_cache: Dict[str, Dict] = {}
        self._cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cache_prices")
        try:
            os.makedirs(self._cache_dir, exist_ok=True)
        except Exception as e:
            logger.debug(f"Impossible de créer le dossier de cache: {e}")
        
        logger.info("Client API de prix immobiliers initialisé")
    
    def get_local_prices(self, 
                        city: str, 
                        postal_code: Optional[str] = None,
                        property_type: str = "apartment") -> Dict:
        """Retourne uniquement le prix moyen €/m² DVF (agrégat analyze) pour la commune.

        - Si DVF indisponible: retourne {'error': 'Aucune estimation DVF disponible'}.
        - Pas de fallback estimation.
        """
        logger.info(f"Recherche des prix (DVF-agrégat) pour {city} ({property_type})")

        insee_code = self._resolve_insee(city, postal_code)
        months = 24

        if not insee_code:
            return {"error": "Aucune estimation DVF disponible (INSEE introuvable)"}

        cache_key = f"agg:{insee_code}:{property_type}:{months}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        agg = self._query_dvf_aggregate(insee_code, property_type, months=months, city=city, postal_code=postal_code)
        if agg and agg.get("avg_m2"):
            avg = float(agg["avg_m2"])
            result = {
                "price_per_sqm": int(round(avg)),
                "min_price": None,
                "max_price": None,
                "transaction_count": agg.get("count") or "N/A",
                "data_period": f"{months} derniers mois",
                "city": city,
                "postal_code": postal_code,
                "property_type": property_type,
                "source": "DVF (agrégat API)",
                "confidence": None,
            }
            self._cache_set(cache_key, result)
            return result

        return {"error": "Aucune estimation DVF disponible"}

    # ---------------------- Normalisation INSEE ----------------------
    def _resolve_insee(self, city: str, postal_code: Optional[str]) -> Optional[str]:
        """Résout le code INSEE via l'API geo.api.gouv.fr. Ne lève pas d'exception."""
        try:
            params = {"nom": city, "limit": 1}
            if postal_code:
                params = {"nom": city, "codePostal": postal_code, "limit": 1}
            resp = self.session.get(self.geo_api_url, params=params, timeout=5)
            if resp.status_code != 200:
                logger.info(f"INSEE non résolu ({resp.status_code}) pour {city} {postal_code or ''}")
                return None
            data = resp.json()
            if isinstance(data, list) and data:
                code = data[0].get("code")
                if code:
                    return code
            return None
        except requests.exceptions.RequestException as e:
            logger.info(f"Erreur réseau INSEE: {e}")
            return None
        except Exception as e:
            logger.debug(f"Erreur INSEE: {e}")
            return None

    # ---------------------- DVF plugin & stats ----------------------
    def _query_dvf(self, insee_code: str, property_type: str, months: int = 24) -> List[Dict]:
        """Récupère les transactions DVF via l'API data.economie.gouv.fr (Opendatasoft).

        Paramètres:
            insee_code: code INSEE commune (ex: 17433)
            property_type: 'apartment' | 'house'
            months: fenêtre temporelle récente à considérer

        Retour:
            Liste de dicts: {price, surface, type, date}
        """
        try:
            env_base = os.getenv("DVF_API_BASE_URL")
            base_urls = [env_base] if env_base else []
            base_urls += [
                "https://data.economie.gouv.fr/api/records/1.0/search/",
                "https://api.etalab.gouv.fr/api/records/1.0/search/",
            ]
            dataset = os.getenv("DVF_DATASET", "valeurs-foncieres")

            # Mapping type_local DVF
            type_local = "Appartement" if property_type == "apartment" else "Maison"

            # Période de filtre locale (côté client)
            cutoff = datetime.utcnow() - timedelta(days=max(1, months) * 30)

            params = {
                "dataset": dataset,
                "rows": os.getenv("DVF_ROWS", "1000"),  # plafond raisonnable
                "sort": "-date_mutation",
                "refine.nature_mutation": "Vente",
                "refine.code_commune": insee_code,
                "refine.type_local": type_local,
            }

            # Option: clé API ODS (non nécessaire en public)
            headers = {"Accept": "application/json", "User-Agent": "Rendimo-Assistant/1.0"}
            records = []
            last_status = None
            for base_url in base_urls:
                try:
                    resp = self.session.get(base_url, params=params, headers=headers, timeout=10)
                    last_status = resp.status_code
                    if resp.status_code == 200:
                        data = resp.json() or {}
                        records = data.get("records", []) or []
                        break
                except requests.exceptions.RequestException:
                    continue
            if not records:
                if last_status:
                    logger.info(f"DVF HTTP {last_status} pour commune {insee_code}")
                return []

            txs: List[Dict] = []
            for rec in records:
                fields = rec.get("fields", {})
                try:
                    price = fields.get("valeur_fonciere")
                    surf = fields.get("surface_reelle_bati")
                    tloc = fields.get("type_local")
                    d = fields.get("date_mutation")
                    if not price or not surf or not d:
                        continue
                    # Filtre date
                    date_str = str(d)[:10]
                    try:
                        d_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    except Exception:
                        # DVF date parfois "YYYY/MM/DD"
                        try:
                            d_obj = datetime.strptime(date_str.replace("/", "-"), "%Y-%m-%d")
                        except Exception:
                            continue
                    if d_obj < cutoff:
                        continue

                    # Map type
                    norm_type = "apartment" if str(tloc).lower().startswith("appartement") else (
                        "house" if str(tloc).lower().startswith("maison") else None
                    )
                    if norm_type and norm_type != property_type:
                        # Par sécurité, garder seulement le type demandé
                        continue
                    txs.append({
                        "price": float(price),
                        "surface": float(surf),
                        "type": norm_type or property_type,
                        "date": date_str,
                    })
                except Exception:
                    continue

            # Si rien via code_commune (cas Lyon arrondissements), tentative légère via code département
            if not txs and len(insee_code) >= 2:
                dep = insee_code[:2]
                params_fallback = {
                    "dataset": dataset,
                    "rows": os.getenv("DVF_ROWS", "1000"),
                    "sort": "-date_mutation",
                    "refine.nature_mutation": "Vente",
                    "refine.code_departement": dep,
                    "refine.type_local": type_local,
                }
                resp2 = None
                for base_url in base_urls:
                    try:
                        r2 = self.session.get(base_url, params=params_fallback, headers=headers, timeout=10)
                        if r2.status_code == 200:
                            resp2 = r2
                            break
                    except requests.exceptions.RequestException:
                        continue
                if resp2 is not None and resp2.status_code == 200:
                    data2 = resp2.json() or {}
                    for rec in data2.get("records", []) or []:
                        fields = rec.get("fields", {})
                        try:
                            if str(fields.get("code_commune")) != insee_code:
                                continue
                            price = fields.get("valeur_fonciere")
                            surf = fields.get("surface_reelle_bati")
                            d = fields.get("date_mutation")
                            if not price or not surf or not d:
                                continue
                            date_str = str(d)[:10]
                            d_obj = datetime.strptime(date_str.replace("/", "-"), "%Y-%m-%d")
                            if d_obj < cutoff:
                                continue
                            txs.append({
                                "price": float(price),
                                "surface": float(surf),
                                "type": property_type,
                                "date": date_str,
                            })
                        except Exception:
                            continue

            return txs
        except requests.exceptions.RequestException as e:
            logger.info(f"Erreur réseau DVF: {e}")
            return []
        except Exception as e:
            logger.debug(f"_query_dvf error: {e}")
            return []

    def _expand_insee_to_query(self, insee_code: str) -> List[str]:
        """Déploie un code INSEE ville en codes d'arrondissements pour P/L/M.
        Paris 75056 -> 75101..75120; Lyon 69123 -> 69381..69389; Marseille 13055 -> 13201..13216
        Sinon retourne [insee_code].
        """
        try:
            if insee_code == "75056":
                return [f"751{str(i).zfill(2)}" for i in range(1, 21)]
            if insee_code == "69123":
                return [f"6938{i}" for i in range(1, 10)]
            if insee_code == "13055":
                return [f"132{str(i).zfill(2)}" for i in range(1, 17)]
            return [insee_code]
        except Exception:
            return [insee_code]

    def _query_dvf_aggregate(self, insee_code: str, property_type: str, months: int = 24, city: Optional[str] = None, postal_code: Optional[str] = None) -> Optional[Dict]:
        """Agrégat DVF via endpoint 'analyze' pour obtenir un €/m² moyen par commune.

        Retour: {'avg_m2': float, 'count': Optional[int], 'period_months': int} ou None.
        """
        try:
            base_urls = []
            env_base = os.getenv("DVF_API_BASE_URL")
            if env_base:
                # Normaliser vers /analyze/
                if env_base.endswith("/search/"):
                    env_base = env_base.replace("/search/", "/analyze/")
                base_urls.append(env_base)
            base_urls += [
                "https://data.economie.gouv.fr/api/records/1.0/analyze/",
                "https://api.etalab.gouv.fr/api/records/1.0/analyze/",
            ]
            dataset = os.getenv("DVF_DATASET", "valeurs-foncieres")
            type_local = "Appartement" if property_type == "apartment" else "Maison"

            cutoff = (datetime.utcnow() - timedelta(days=max(1, months) * 30)).strftime("%Y-%m-%d")
            where = f'date_mutation >= "{cutoff}"'
            # Fallback période plus large si aucune donnée (36 mois)
            cutoff_wide = (datetime.utcnow() - timedelta(days=36 * 30)).strftime("%Y-%m-%d")
            where_wide = f'date_mutation >= "{cutoff_wide}"'
            headers = {"Accept": "application/json", "User-Agent": "Rendimo-Assistant/1.0"}

            def extract_sums_from_series(data_json: Dict, codes_filter: Optional[List[str]] = None) -> Tuple[float, float]:
                """Extrait la somme des valeurs et des surfaces depuis le JSON analyze.

                Si codes_filter est fourni, on agrège uniquement les points dont x est dans cette liste.
                """
                total_price = 0.0
                total_surf = 0.0
                series = data_json.get("series") or []
                if not series:
                    return (0.0, 0.0)
                # On s'attend à 2 séries: sum(valeur_fonciere) et sum(surface_reelle_bati)
                sum_price_map: Dict[str, float] = {}
                sum_surf_map: Dict[str, float] = {}
                for s in series:
                    label = str(s.get("serie", "")).lower()
                    datapoints = s.get("data") or s.get("values") or []
                    for pt in datapoints:
                        try:
                            xcode = str(pt.get("x")) if isinstance(pt, dict) else None
                            yval = float(pt.get("y")) if isinstance(pt, dict) and pt.get("y") is not None else None
                            if xcode is None or yval is None:
                                continue
                            if codes_filter and xcode not in codes_filter:
                                continue
                            if "valeur" in label:
                                sum_price_map[xcode] = sum_price_map.get(xcode, 0.0) + yval
                            elif "surface_reelle_bati" in label or "surface" in label:
                                sum_surf_map[xcode] = sum_surf_map.get(xcode, 0.0) + yval
                        except Exception:
                            continue
                # Agréger sur les codes
                all_codes = set(sum_price_map.keys()) | set(sum_surf_map.keys())
                for c in all_codes:
                    sp = sum_price_map.get(c, 0.0)
                    ss = sum_surf_map.get(c, 0.0)
                    total_price += sp
                    total_surf += ss
                return (total_price, total_surf)

            def do_request(base_url: str) -> Optional[Dict]:
                try:
                    total_price = 0.0
                    total_surf = 0.0
                    # 1) Essai direct: refines par code_commune (avec expansion P/L/M)
                    exp_codes = self._expand_insee_to_query(insee_code)
                    for code in exp_codes:
                        qs = (
                            f"dataset={quote(dataset)}&x=code_commune"
                            f"&y.sum=valeur_fonciere&y.sum=surface_reelle_bati"
                            f"&refine.nature_mutation=Vente"
                            f"&refine.type_local={quote(type_local)}"
                            f"&refine.code_commune={quote(code)}"
                            f"&where={quote(where)}"
                        )
                        url = f"{base_url}?{qs}"
                        resp = self.session.get(url, headers=headers, timeout=10)
                        if resp.status_code == 200:
                            sp, ss = extract_sums_from_series(resp.json() or {})
                            total_price += sp
                            total_surf += ss
                        else:
                            try:
                                logger.info(f"DVF analyze status {resp.status_code} (code_commune) via {base_url}")
                            except Exception:
                                pass
                    if total_price > 0 and total_surf > 0:
                        return {"avg_m2": total_price / total_surf, "count": None, "period_months": months}

                    # 2) Fallback par code_postal si fourni: on regroupe par code_commune et on filtre nos codes
                    if postal_code:
                        qs = (
                            f"dataset={quote(dataset)}&x=code_commune"
                            f"&y.sum=valeur_fonciere&y.sum=surface_reelle_bati"
                            f"&refine.nature_mutation=Vente"
                            f"&refine.type_local={quote(type_local)}"
                            f"&refine.code_postal={quote(str(postal_code))}"
                            f"&where={quote(where)}"
                        )
                        url = f"{base_url}?{qs}"
                        resp = self.session.get(url, headers=headers, timeout=10)
                        if resp.status_code == 200:
                            sp, ss = extract_sums_from_series(resp.json() or {}, codes_filter=exp_codes)
                            total_price += sp
                            total_surf += ss
                        else:
                            try:
                                logger.info(f"DVF analyze status {resp.status_code} (code_postal) via {base_url}")
                            except Exception:
                                pass
                        if total_price > 0 and total_surf > 0:
                            return {"avg_m2": total_price / total_surf, "count": None, "period_months": months}

                    # 3) Fallback par nom de commune si fourni: group by code_commune, filtre codes
                    if city:
                        commune = city.upper()
                        # Essai avec nom_commune
                        for refine_field in ("nom_commune", "commune"):
                            qs = (
                                f"dataset={quote(dataset)}&x=code_commune"
                                f"&y.sum=valeur_fonciere&y.sum=surface_reelle_bati"
                                f"&refine.nature_mutation=Vente"
                                f"&refine.type_local={quote(type_local)}"
                                f"&refine.{refine_field}={quote(commune)}"
                                f"&where={quote(where)}"
                            )
                            url = f"{base_url}?{qs}"
                            resp = self.session.get(url, headers=headers, timeout=10)
                            if resp.status_code == 200:
                                sp, ss = extract_sums_from_series(resp.json() or {}, codes_filter=exp_codes)
                                total_price += sp
                                total_surf += ss
                                if total_price > 0 and total_surf > 0:
                                    return {"avg_m2": total_price / total_surf, "count": None, "period_months": months}
                            else:
                                try:
                                    logger.info(f"DVF analyze status {resp.status_code} ({refine_field}) via {base_url}")
                                except Exception:
                                    pass

                    # 4) Fallback période élargie (36 mois) sur code_commune
                    if total_price == 0.0 and total_surf == 0.0:
                        for code in exp_codes:
                            qs = (
                                f"dataset={quote(dataset)}&x=code_commune"
                                f"&y.sum=valeur_fonciere&y.sum=surface_reelle_bati"
                                f"&refine.nature_mutation=Vente"
                                f"&refine.type_local={quote(type_local)}"
                                f"&refine.code_commune={quote(code)}"
                                f"&where={quote(where_wide)}"
                            )
                            url = f"{base_url}?{qs}"
                            resp = self.session.get(url, headers=headers, timeout=10)
                            if resp.status_code == 200:
                                sp, ss = extract_sums_from_series(resp.json() or {})
                                total_price += sp
                                total_surf += ss
                            else:
                                try:
                                    logger.info(f"DVF analyze status {resp.status_code} (wide period) via {base_url}")
                                except Exception:
                                    pass
                        if total_price > 0 and total_surf > 0:
                            return {"avg_m2": total_price / total_surf, "count": None, "period_months": months}
                    return None
                except requests.exceptions.RequestException:
                    return None
                except Exception:
                    return None

            for base in base_urls:
                out = do_request(base)
                if out:
                    return out
            return None
        except Exception:
            return None

    def _compute_stats(self, transactions: List[Dict]) -> Dict:
        """Calcule median/p10/p90 sur les prix au m² à partir d'une liste de transactions.

        Chaque transaction est supposée contenir au minimum:
        - price (euros)
        - surface (m² habitables)
        - type (optionnel: 'apartment'|'house')
        - date (optionnelle: 'YYYY-MM-DD')
        """
        try:
            # Filtrage qualité
            prices_m2: List[float] = []
            last_date: Optional[str] = None
            for tx in transactions or []:
                try:
                    price = float(tx.get('price', 0))
                    surface = float(tx.get('surface', 0))
                    if price <= 1000 or surface < 8 or surface > 300:
                        continue
                    # Type si fourni (tolérant)
                    t = tx.get('type')
                    if t and t not in ('apartment', 'house', 'Appartement', 'Maison'):
                        continue
                    prices_m2.append(price / surface)
                    # Date la plus récente
                    d = tx.get('date')
                    if d and (not last_date or d > last_date):
                        last_date = d
                except Exception:
                    continue

            if not prices_m2:
                return {}

            prices_m2.sort()
            count = len(prices_m2)

            def percentile(sorted_list: List[float], p: float) -> float:
                """Calcul de percentile sans numpy (p entre 0 et 100)."""
                if not sorted_list:
                    return 0.0
                k = (len(sorted_list) - 1) * (p / 100.0)
                f = int(k)
                c = min(f + 1, len(sorted_list) - 1)
                if f == c:
                    return sorted_list[int(k)]
                d0 = sorted_list[f] * (c - k)
                d1 = sorted_list[c] * (k - f)
                return d0 + d1

            med = median(prices_m2)
            p10 = percentile(prices_m2, 10)
            p90 = percentile(prices_m2, 90)

            return {
                'median_m2': round(med),
                'p10_m2': round(p10),
                'p90_m2': round(p90),
                'count': count,
                'period_months': None,  # rempli en amont
                'last_tx_date': last_date,
            }
        except Exception as e:
            logger.debug(f"_compute_stats error: {e}")
            return {}

    # ---------------------- Cache 24h ----------------------
    def _cache_get(self, key: str) -> Optional[Dict]:
        """Récupère une entrée de cache si < 24h (mémoire puis disque)."""
        try:
            now = time.time()
            # mémoire
            cached = self._mem_cache.get(key)
            if cached and (now - cached.get('_ts', 0) < 24 * 3600):
                return cached.get('data')
            # disque
            fpath = os.path.join(self._cache_dir, f"{self._safe_key(key)}.json")
            if os.path.exists(fpath):
                with open(fpath, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
                if now - payload.get('_ts', 0) < 24 * 3600:
                    self._mem_cache[key] = payload
                    return payload.get('data')
        except Exception as e:
            logger.debug(f"_cache_get error: {e}")
        return None

    def _cache_set(self, key: str, data: Dict) -> None:
        """Écrit dans le cache (mémoire + disque)."""
        try:
            payload = {'_ts': time.time(), 'data': data}
            self._mem_cache[key] = payload
            fpath = os.path.join(self._cache_dir, f"{self._safe_key(key)}.json")
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.debug(f"_cache_set error: {e}")

    @staticmethod
    def _safe_key(key: str) -> str:
        return key.replace(':', '_').replace('/', '_')
    
    def _get_dvf_prices(self, 
                       city: str, 
                       postal_code: Optional[str],
                       property_type: str) -> Optional[Dict]:
        """
        Récupère les prix depuis l'API DVF (Demandes de Valeurs Foncières)
        
        Args:
            city (str): Nom de la ville
            postal_code (Optional[str]): Code postal
            property_type (str): Type de bien
            
        Returns:
            Optional[Dict]: Données de prix ou None
        """
        try:
            # Construction de la requête pour l'API DVF
            # Note: Cette API peut avoir des limitations ou changer
            
            # URL simplifiée pour DVF
            params = {
                'nom_commune': city.upper(),
                'nature_mutation': 'Vente',
                'type_local': 'Appartement' if property_type == 'apartment' else 'Maison'
            }
            
            if postal_code:
                params['code_postal'] = postal_code
            
            # NOTE: Cette méthode historique est conservée pour compatibilité
            # mais le nouveau flux DVF passe par _resolve_insee/_query_dvf/_compute_stats
            # Ici, on continue de renvoyer une simulation si appelée.
            return self._simulate_dvf_response(city, property_type)
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération DVF: {str(e)}")
            return None
    
    def _simulate_dvf_response(self, city: str, property_type: str) -> Dict:
        """
        Simule une réponse DVF avec des données réalistes
        (En production, cette méthode serait remplacée par de vrais appels API)
        
        Args:
            city (str): Nom de la ville
            property_type (str): Type de bien
            
        Returns:
            Dict: Données simulées
        """
        # Base de données simplifiée des prix par ville
        city_prices = {
            'paris': {'apartment': 10500, 'house': 12000},
            'lyon': {'apartment': 4800, 'house': 5200},
            'marseille': {'apartment': 3200, 'house': 3800},
            'toulouse': {'apartment': 3800, 'house': 4200},
            'nice': {'apartment': 5200, 'house': 6000},
            'nantes': {'apartment': 3600, 'house': 4000},
            'strasbourg': {'apartment': 3200, 'house': 3600},
            'montpellier': {'apartment': 3800, 'house': 4200},
            'bordeaux': {'apartment': 4200, 'house': 4600},
            'lille': {'apartment': 2800, 'house': 3200}
        }
        
        city_lower = city.lower()
        
        # Recherche exacte puis approximative
        price_per_sqm = None
        for city_key, prices in city_prices.items():
            if city_key in city_lower or city_lower in city_key:
                price_per_sqm = prices.get(property_type, prices['apartment'])
                break
        
        # Prix par défaut si ville non trouvée
        if price_per_sqm is None:
            if 'paris' in city_lower:
                price_per_sqm = 10500 if property_type == 'apartment' else 12000
            else:
                # Prix moyen national
                price_per_sqm = 3200 if property_type == 'apartment' else 3600
        
        # Variation de ±10% pour simuler la réalité
        import random
        variation = random.uniform(0.9, 1.1)
        price_per_sqm = int(price_per_sqm * variation)
        
        return {
            'price_per_sqm': price_per_sqm,
            'min_price': int(price_per_sqm * 0.8),
            'max_price': int(price_per_sqm * 1.2),
            'transaction_count': random.randint(50, 300),
            'data_period': '12 derniers mois',
            'city': city,
            'property_type': property_type
        }
    
    def _get_meilleurs_agents_prices(self, city: str, property_type: str) -> Optional[Dict]:
        """
        Récupère les prix depuis l'API MeilleursAgents
        
        Args:
            city (str): Nom de la ville
            property_type (str): Type de bien
            
        Returns:
            Optional[Dict]: Données de prix ou None
        """
        if not self.meilleurs_agents_key:
            return None
        
        try:
            # URL de l'API MeilleursAgents (exemple)
            url = "https://api.meilleursagents.com/v1/prices/search"
            
            headers = {
                'Authorization': f'Bearer {self.meilleurs_agents_key}',
                'Content-Type': 'application/json'
            }
            
            params = {
                'city': city,
                'property_type': property_type,
                'transaction_type': 'sale'
            }
            
            response = self.session.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Traitement de la réponse (structure dépendante de l'API réelle)
            if data and 'price_per_sqm' in data:
                return {
                    'price_per_sqm': data['price_per_sqm'],
                    'min_price': data.get('min_price'),
                    'max_price': data.get('max_price'),
                    'transaction_count': data.get('transaction_count'),
                    'data_period': data.get('period', '12 derniers mois'),
                    'city': city,
                    'property_type': property_type
                }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur API MeilleursAgents: {str(e)}")
        except Exception as e:
            logger.error(f"Erreur lors du traitement MeilleursAgents: {str(e)}")
        
        return None
    
    def _get_estimated_prices(self, city: str, property_type: str) -> Dict:
        """
        Fournit des estimations de prix basées sur des données moyennes
        
        Args:
            city (str): Nom de la ville
            property_type (str): Type de bien
            
        Returns:
            Dict: Estimations de prix
        """
        # Estimations basées sur la taille de la ville et la région
        city_lower = city.lower()
        
        # Classification des villes
        major_cities = ['paris', 'lyon', 'marseille', 'toulouse', 'nice', 'nantes', 'strasbourg', 'montpellier', 'bordeaux', 'lille']
        
        if any(major_city in city_lower for major_city in major_cities):
            base_price = 4500 if property_type == 'apartment' else 5000
            category = "Grande ville"
        else:
            # Estimation pour ville moyenne/petite
            base_price = 2800 if property_type == 'apartment' else 3200
            category = "Ville moyenne"
        
        # Ajustements régionaux approximatifs
        if 'paris' in city_lower or 'neuilly' in city_lower or 'boulogne' in city_lower:
            base_price *= 2.5
        elif any(region in city_lower for region in ['lyon', 'nice', 'cannes', 'antibes']):
            base_price *= 1.3
        
        return {
            'price_per_sqm': base_price,
            'min_price': int(base_price * 0.8),
            'max_price': int(base_price * 1.2),
            'transaction_count': 'N/A',
            'data_period': 'Estimation moyenne',
            'city': city,
            'property_type': property_type,
            'category': category,
            'reliability': 'Estimation'
        }
    
    def compare_property_price(self, 
                              property_price: float,
                              property_surface: float,
                              market_data: Dict) -> Dict:
        """
        Compare le prix d'un bien avec le marché local
        
        Args:
            property_price (float): Prix du bien
            property_surface (float): Surface du bien
            market_data (Dict): Données du marché local
            
        Returns:
            Dict: Résultats de la comparaison
        """
        if not property_surface or property_surface <= 0:
            return {'error': 'Surface invalide'}
        
        property_price_per_sqm = property_price / property_surface
        market_price_per_sqm = market_data.get('price_per_sqm', 0)
        
        if market_price_per_sqm <= 0:
            return {'error': 'Données de marché invalides'}
        
        # Calcul de la différence
        difference = property_price_per_sqm - market_price_per_sqm
        percentage_difference = (difference / market_price_per_sqm) * 100
        
        # Évaluation
        if percentage_difference <= -15:
            evaluation = "Très bon prix (>15% sous le marché)"
            score = "Excellent"
        elif percentage_difference <= -5:
            evaluation = "Bon prix (5-15% sous le marché)"
            score = "Bon"
        elif percentage_difference <= 5:
            evaluation = "Prix dans la moyenne (±5%)"
            score = "Correct"
        elif percentage_difference <= 15:
            evaluation = "Prix un peu élevé (5-15% au-dessus)"
            score = "Élevé"
        else:
            evaluation = "Prix très élevé (>15% au-dessus)"
            score = "Très élevé"
        
        # Position relative par rapport à l'intervalle inter-déciles si dispo
        p10 = market_data.get('p10_m2')
        p90 = market_data.get('p90_m2')
        relative_position = None
        if isinstance(p10, (int, float)) and isinstance(p90, (int, float)) and p10 and p90:
            if property_price_per_sqm < p10:
                relative_position = "Très sous le marché"
            elif property_price_per_sqm > p90:
                relative_position = "Très au-dessus du marché"
            else:
                relative_position = "Dans l’intervalle inter-déciles"

        return {
            'property_price_per_sqm': property_price_per_sqm,
            'market_price_per_sqm': market_price_per_sqm,
            'difference': difference,
            'percentage_difference': percentage_difference,
            'evaluation': evaluation,
            'score': score,
            'market_data': market_data,
            'relative_position': relative_position
        }
    
    def get_historical_trends(self, city: str, period_months: int = 12) -> Dict:
        """
        Récupère les tendances historiques des prix (simulation)
        
        Args:
            city (str): Nom de la ville
            period_months (int): Période en mois
            
        Returns:
            Dict: Données de tendance
        """
        # Pour ce MVP, on simule des tendances
        import random
        
        # Génération d'une tendance simulée
        monthly_changes = []
        current_change = 0
        
        for month in range(period_months):
            # Simulation d'une variation mensuelle réaliste
            change = random.uniform(-0.5, 0.8)  # Entre -0.5% et +0.8% par mois
            current_change += change
            monthly_changes.append(round(current_change, 2))
        
        # Calcul de la tendance générale
        total_change = monthly_changes[-1] if monthly_changes else 0
        
        if total_change > 5:
            trend = "Hausse forte"
        elif total_change > 2:
            trend = "Hausse modérée"
        elif total_change > -2:
            trend = "Stabilité"
        elif total_change > -5:
            trend = "Baisse modérée"
        else:
            trend = "Baisse forte"
        
        return {
            'city': city,
            'period_months': period_months,
            'total_change_percent': total_change,
            'trend': trend,
            'monthly_changes': monthly_changes,
            'last_update': datetime.now().strftime('%Y-%m-%d')
        }
    
    def get_neighborhood_analysis(self, city: str, postal_code: Optional[str] = None) -> Dict:
        """
        Analyse du quartier et des commodités (simulation)
        
        Args:
            city (str): Nom de la ville
            postal_code (Optional[str]): Code postal
            
        Returns:
            Dict: Analyse du quartier
        """
        # Simulation d'une analyse de quartier
        import random
        
        # Scores aléatoires mais cohérents
        scores = {
            'transport': random.randint(6, 9),
            'commerces': random.randint(5, 9),
            'ecoles': random.randint(6, 9),
            'securite': random.randint(6, 8),
            'pollution': random.randint(4, 8),
            'espaces_verts': random.randint(4, 8)
        }
        
        # Score global
        global_score = sum(scores.values()) / len(scores)
        
        # Appréciation
        if global_score >= 8:
            appreciation = "Excellent quartier"
        elif global_score >= 7:
            appreciation = "Très bon quartier"
        elif global_score >= 6:
            appreciation = "Bon quartier"
        else:
            appreciation = "Quartier moyen"
        
        return {
            'city': city,
            'postal_code': postal_code,
            'scores': scores,
            'global_score': round(global_score, 1),
            'appreciation': appreciation,
            'transport_note': "Métro/Bus à proximité" if scores['transport'] >= 7 else "Transport limité",
            'analysis_date': datetime.now().strftime('%Y-%m-%d')
        }

# Fonction utilitaire pour tester le module
def test_price_api():
    """Fonction de test pour l'API de prix"""
    api = PriceAPI()
    
    print("Test de l'API de prix immobiliers...")
    
    # Test de récupération des prix
    city = "Lyon"
    property_type = "apartment"
    
    print(f"Recherche des prix pour {city} ({property_type})")
    
    market_data = api.get_local_prices(city, property_type=property_type)
    print(f"Prix au m²: {market_data.get('price_per_sqm', 'N/A')}€")
    print(f"Source: {market_data.get('source', 'N/A')}")
    print(f"Confiance: {market_data.get('confidence', 'N/A')}")
    if 'p10_m2' in market_data:
        print(f"P10: {market_data.get('p10_m2')}€ | P90: {market_data.get('p90_m2')}€")
    
    # Test de comparaison
    property_price = 200000
    property_surface = 50
    
    comparison = api.compare_property_price(property_price, property_surface, market_data)
    print(f"\nComparaison:")
    print(f"Prix du bien: {comparison.get('property_price_per_sqm', 0):.0f}€/m²")
    print(f"Prix marché: {comparison.get('market_price_per_sqm', 0):.0f}€/m²")
    print(f"Évaluation: {comparison.get('evaluation', 'N/A')}")
    
    # Test DVF indisponible => fallback estimations
    city2 = "Surgères"
    md2 = api.get_local_prices(city2, postal_code="17700", property_type="house")
    print(f"\n[{city2}] Prix: {md2.get('price_per_sqm')}€, Source: {md2.get('source')}, Confiance: {md2.get('confidence')}")

    # Test des tendances
    trends = api.get_historical_trends(city)
    print(f"\nTendance sur 12 mois: {trends.get('trend', 'N/A')} ({trends.get('total_change_percent', 0):+.1f}%)")

if __name__ == "__main__":
    test_price_api()