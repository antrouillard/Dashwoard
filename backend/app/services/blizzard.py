"""
Service Blizzard API — gère l'OAuth2 et tous les appels à l'API WoW.
Docs : https://develop.battle.net/documentation/world-of-warcraft/profile-apis
"""

import re
from datetime import datetime, timedelta

import httpx

from app.core.config import settings

# ── Constantes ────────────────────────────────────────────────────────────────

OAUTH_BASE = "https://oauth.battle.net"
API_BASE = f"https://{settings.BLIZZARD_REGION}.api.blizzard.com"
NAMESPACE = f"profile-{settings.BLIZZARD_REGION}"
STATIC_NAMESPACE   = f"static-{settings.BLIZZARD_REGION}"
DYNAMIC_NAMESPACE  = f"dynamic-{settings.BLIZZARD_REGION}"
LOCALE = "fr_FR"

# ── Mapping noms FR (tels que retournés par Blizzard) → profession ID ─────────
# Ces IDs sont stables — ils ne changent pas entre extensions.
PROFESSION_IDS: dict[str, int] = {
    # Noms français (retournés par Blizzard avec locale=fr_FR)
    "alchimie": 171,
    "forge": 164,
    "enchantement": 333,
    "ingénierie": 202,
    "joaillerie": 755,
    "travail du cuir": 165,
    "couture": 197,
    "calligraphie": 773,
    "cuisine": 185,
    "pêche": 356,
    "herboristerie": 182,
    "mine": 186,
    "dépeçage": 393,
    "archéologie": 794,
    # Noms anglais (fallback si le profil a été synchro avec locale=en_US)
    "alchemy": 171,
    "blacksmithing": 164,
    "enchanting": 333,
    "engineering": 202,
    "jewelcrafting": 755,
    "leatherworking": 165,
    "tailoring": 197,
    "inscription": 773,
    "cooking": 185,
    "fishing": 356,
    "herbalism": 182,
    "mining": 186,
    "skinning": 393,
    "archaeology": 794,
}

# ── Cache mémoire pour le token applicatif et les recettes ────────────────────
_app_token_cache: dict = {"token": None, "expires_at": None}
_recipe_list_cache: dict[str, tuple[list, datetime]] = {}   # {profession: ([recipes], cached_at)}
_recipe_detail_cache: dict[int, dict] = {}                  # {recipe_id: detail}
_RECIPE_CACHE_TTL = timedelta(hours=24)

# Noms de pseudo-recettes (en-têtes de section Blizzard, ex: « Section I », « Appendice IV »)
_FAKE_RECIPE_RE = re.compile(r'\b(Section|Appendice)\s+[IVXLCDM]+\b', re.IGNORECASE)


# ── Helpers ───────────────────────────────────────────────────────────────────


def realm_slug(realm_name: str) -> str:
    """Convertit un nom de royaume en slug Blizzard (ex: 'Hyjal' → 'hyjal')."""
    slug = realm_name.lower()
    slug = re.sub(r"[''`]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    return slug


def char_slug(name: str) -> str:
    """Nom de personnage en minuscules pour l'URL."""
    return name.lower().strip()


# ── OAuth2 ────────────────────────────────────────────────────────────────────


def build_auth_url(account_id: int) -> str:
    """Retourne l'URL de redirection vers Blizzard pour l'OAuth2."""
    params = {
        "client_id": settings.BLIZZARD_CLIENT_ID,
        "redirect_uri": settings.BLIZZARD_REDIRECT_URI,
        "response_type": "code",
        "scope": "wow.profile",
        "state": str(account_id),
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{OAUTH_BASE}/authorize?{query}"


async def exchange_code_for_token(code: str) -> dict:
    """Échange un code d'autorisation contre un access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{OAUTH_BASE}/token",
            auth=(settings.BLIZZARD_CLIENT_ID, settings.BLIZZARD_CLIENT_SECRET),
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.BLIZZARD_REDIRECT_URI,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def get_battletag(access_token: str) -> str | None:
    """Récupère le BattleTag de l'utilisateur connecté."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{OAUTH_BASE}/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("battletag")
    return None


# ── Appels API WoW ────────────────────────────────────────────────────────────


async def _get(access_token: str, path: str, extra_params: dict | None = None) -> dict | None:
    """GET authentifié sur l'API WoW. Retourne None en cas d'erreur 404."""
    params = {"namespace": NAMESPACE, "locale": LOCALE}
    if extra_params:
        params.update(extra_params)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_BASE}{path}",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()


async def get_character_profile(
    access_token: str, realm: str, name: str
) -> dict | None:
    """
    Profil complet d'un personnage : ilvl, level, classe, race, faction, or (money en copper).
    Requiert le scope wow.profile.
    """
    path = f"/profile/wow/character/{realm_slug(realm)}/{char_slug(name)}"
    return await _get(access_token, path)


async def get_character_equipment(
    access_token: str, realm: str, name: str
) -> dict | None:
    """Equipement du personnage pour l'ilvl équipé précis."""
    path = f"/profile/wow/character/{realm_slug(realm)}/{char_slug(name)}/equipment"
    return await _get(access_token, path)


async def get_mythic_profile(
    access_token: str, realm: str, name: str
) -> dict | None:
    """Score M+ (current_mythic_rating.rating)."""
    path = f"/profile/wow/character/{realm_slug(realm)}/{char_slug(name)}/mythic-keystone-profile"
    return await _get(access_token, path)


async def get_professions(
    access_token: str, realm: str, name: str
) -> dict | None:
    """Professions du personnage avec niveaux de compétence."""
    path = f"/profile/wow/character/{realm_slug(realm)}/{char_slug(name)}/professions"
    return await _get(access_token, path)


# ── Parsers ───────────────────────────────────────────────────────────────────


def parse_character_update(profile: dict, equipment: dict | None) -> dict:
    """
    Extrait les champs utiles d'un profil Blizzard pour mettre à jour notre Character.
    """
    update: dict = {}

    # Niveau
    if level := profile.get("level"):
        update["level"] = level

    # Race
    if race := profile.get("race", {}).get("name"):
        update["race"] = race

    # Faction
    if faction := profile.get("faction", {}).get("name"):
        update["faction"] = faction

    # Classe
    if class_name := profile.get("character_class", {}).get("name"):
        update["class_name"] = class_name

    # Spécialisation active
    if spec := profile.get("active_spec", {}).get("name"):
        update["spec"] = spec

    # ilvl moyen (depuis le profil)
    if avg_ilvl := profile.get("average_item_level"):
        update["ilvl"] = avg_ilvl
    if eq_ilvl := profile.get("equipped_item_level"):
        update["ilvl_equipped"] = eq_ilvl

    # Or (en copper — Blizzard n'expose money que pour les chars du compte connecté)
    if "money" in profile:
        update["gold"] = profile["money"]

    # Genre
    if gender := profile.get("gender", {}).get("name"):
        update["gender"] = gender

    update["last_sync_at"] = datetime.utcnow()
    return update


def parse_mythic_score(mythic_data: dict | None) -> float:
    """Extrait le score M+ depuis la réponse Blizzard."""
    if not mythic_data:
        return 0.0
    # Nouvelle API (BfA+)
    if rating := mythic_data.get("current_mythic_rating", {}).get("rating"):
        return round(float(rating), 1)
    # Ancienne API fallback
    try:
        return round(float(mythic_data["current_period"]["scores"]["all"]), 1)
    except (KeyError, TypeError):
        return 0.0


def parse_professions(professions_data: dict | None) -> list[dict]:
    """
    Retourne une liste de dicts {name, skill_points, max_skill_points, category}
    depuis la réponse Blizzard.
    """
    if not professions_data:
        return []

    results = []
    for section_key in ("primaries", "secondaries"):
        for prof in professions_data.get(section_key, []):
            prof_name = prof.get("profession", {}).get("name", "")
            # Tiers de compétence (Dragonflight, TWW…)
            for tier in prof.get("tiers", []):
                results.append(
                    {
                        "name": prof_name,
                        "skill_points": tier.get("skill_points", 0),
                        "max_skill_points": tier.get("max_skill_points", 100),
                        "category": section_key.removesuffix("ies") + "y",
                    }
                )
                break  # on ne prend que le tier courant (le plus récent)
    return results


# ── API statique (client credentials — pas d'OAuth utilisateur) ──────────────


async def get_app_token() -> str:
    """
    Retourne un token Blizzard via client credentials.
    Utilisé pour l'API statique (recettes, items...) sans connexion utilisateur.
    Mis en cache mémoire jusqu'à expiration.
    """
    now = datetime.utcnow()
    if _app_token_cache["token"] and _app_token_cache["expires_at"] and _app_token_cache["expires_at"] > now:
        return _app_token_cache["token"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{OAUTH_BASE}/token",
            auth=(settings.BLIZZARD_CLIENT_ID, settings.BLIZZARD_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
        )
        resp.raise_for_status()
        data = resp.json()

    _app_token_cache["token"] = data["access_token"]
    # On retire 60s de marge pour éviter les expiration race conditions
    _app_token_cache["expires_at"] = now + timedelta(seconds=data.get("expires_in", 86400) - 60)
    return _app_token_cache["token"]


async def _get_static(path: str, extra_params: dict | None = None) -> dict | None:
    """GET authentifié sur l'API statique Blizzard (namespace=static-{region})."""
    token = await get_app_token()
    params = {"namespace": STATIC_NAMESPACE, "locale": LOCALE}
    if extra_params:
        params.update(extra_params)

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{API_BASE}{path}",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()


async def _get_dynamic(path: str, extra_params: dict | None = None) -> dict | None:
    """
    GET authentifié sur l'API dynamique Blizzard (namespace=dynamic-{region}).
    Utilisé pour les données temps-réel : hôtel des ventes, enchères, etc.
    """
    token = await get_app_token()
    params = {"namespace": DYNAMIC_NAMESPACE, "locale": LOCALE}
    if extra_params:
        params.update(extra_params)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{API_BASE}{path}",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()


async def get_profession_recipes(profession_name: str, num_tiers: int = 1) -> list[dict]:
    """
    Retourne la liste des recettes pour une profession.
    Format : [{recipe_id, name, category, tier_name, tier_id}]
    Résultat mis en cache mémoire 24h (les recettes ne changent qu'à chaque patch).

    num_tiers : nombre de tiers à inclure par ordre décroissant (le plus grand id en premier).
      1 = extension actuelle seulement (TWW)
      2 = TWW + Dragonflight
      0 = tous les tiers
    """
    key = profession_name.lower().strip()

    # Cache hit (inclut num_tiers pour éviter des résultats incorrects en cache)
    cache_key = f"{key}::{num_tiers}"
    if cache_key in _recipe_list_cache:
        recipes, cached_at = _recipe_list_cache[cache_key]
        if datetime.utcnow() - cached_at < _RECIPE_CACHE_TTL:
            return recipes

    profession_id = PROFESSION_IDS.get(key)
    if not profession_id:
        return []

    # Récupère les tiers de la profession
    prof_data = await _get_static(f"/data/wow/profession/{profession_id}")
    if not prof_data:
        return []

    skill_tiers = prof_data.get("skill_tiers", [])
    if not skill_tiers:
        return []

    # Tri décroissant par id (TWW > DF > SL ...)
    sorted_tiers = sorted(skill_tiers, key=lambda t: t["id"], reverse=True)
    tiers_to_fetch = sorted_tiers if num_tiers == 0 else sorted_tiers[:num_tiers]

    recipes: list[dict] = []
    for tier_meta in tiers_to_fetch:
        tier_data = await _get_static(
            f"/data/wow/profession/{profession_id}/skill-tier/{tier_meta['id']}"
        )
        if not tier_data:
            continue
        tier_name = tier_meta.get("name", str(tier_meta["id"]))
        for category in tier_data.get("categories", []):
            cat_name = category.get("name", "")
            for recipe in category.get("recipes", []):
                name = recipe["name"]
                if _FAKE_RECIPE_RE.search(name):
                    continue  # pseudo-recette (en-tête de section Blizzard)
                recipes.append({
                    "recipe_id": recipe["id"],
                    "name": name,
                    "category": cat_name,
                    "tier_name": tier_name,
                    "tier_id": tier_meta["id"],
                })

    recipes.sort(key=lambda r: (-r["tier_id"], r["name"]))
    _recipe_list_cache[cache_key] = (recipes, datetime.utcnow())
    return recipes


async def get_recipe_detail(recipe_id: int) -> dict | None:
    """
    Retourne les détails d'une recette : item crafté (id + nom) + réactifs.
    Mis en cache mémoire indéfiniment (les recettes ne changent pas en cours de patch).

    Note : certaines recettes craftent plusieurs items ou des items conditionnels
    (Alliance vs Horde) — on prend le premier disponible.
    """
    if recipe_id in _recipe_detail_cache:
        return _recipe_detail_cache[recipe_id]

    data = await _get_static(f"/data/wow/recipe/{recipe_id}")
    if not data:
        # Blizzard static API indisponible (pas de credentials) — on renvoie None,
        # la route crafting utilisera Wowhead search comme fallback.
        return None

    # L'item crafté peut être dans "crafted_item" ou "alliance_crafted_item" etc.
    crafted = (
        data.get("crafted_item")
        or data.get("alliance_crafted_item")
        or data.get("horde_crafted_item")
    )

    result: dict = {
        "recipe_id": recipe_id,
        "recipe_name": data.get("name"),
        "item_id": None,
        "item_name": None,
        "reagents": [],
    }

    if crafted:
        result["item_id"] = crafted.get("item", {}).get("id")
        result["item_name"] = crafted.get("item", {}).get("name") or data.get("name")

    # Les réactifs Wowhead sont récupérés dans la route — pas ici.
    _recipe_detail_cache[recipe_id] = result
    return result


# ── Hôtel des Ventes ────────────────────────────────────────────────────────────────


async def get_connected_realm_id(realm: str) -> int:
    """
    Résout le slug d'un royaume en ID de connected-realm Blizzard.
    Ex : 'archimonde' → 609
    Utilise GET /data/wow/realm/{slug}?namespace=dynamic-{region}
    """
    slug = realm_slug(realm)
    token = await get_app_token()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{API_BASE}/data/wow/realm/{slug}",
            headers={"Authorization": f"Bearer {token}"},
            params={"namespace": DYNAMIC_NAMESPACE, "locale": LOCALE},
        )
    resp.raise_for_status()
    data = resp.json()
    cr_href: str = data["connected_realm"]["href"]
    # href = "https://eu.api.blizzard.com/data/wow/connected-realm/609?..."
    m = re.search(r"/connected-realm/(\d+)", cr_href)
    if not m:
        raise ValueError(f"Impossible de parser le connected-realm ID depuis : {cr_href}")
    return int(m.group(1))


async def fetch_realm_auctions_from_api(realm: str | None = None) -> dict:
    """
    Récupère les enchères non-commodity (équipement, etc.) d'un connected realm.
    Utilise GET /data/wow/connected-realm/{id}/auctions.
    Prix = buyout ÷ quantity  (buyout = 0 → enchere sur offre, ignorée).
    Retourne le même format que fetch_commodities_from_api() +
      "realm" et "connected_realm_id".
    """
    if realm is None:
        realm = settings.BLIZZARD_REALM

    result: dict = {
        "ok": False,
        "http_status": None,
        "error": None,
        "total_auctions": 0,
        "sample_auctions": [],
        "prices": {},
        "quantities": {},
        "realm": realm,
        "connected_realm_id": None,
    }

    try:
        cr_id = await get_connected_realm_id(realm)
        result["connected_realm_id"] = cr_id

        token = await get_app_token()
        # Les enchères de realm peuvent peser 40-80 Mo — timeout généreux
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.get(
                f"{API_BASE}/data/wow/connected-realm/{cr_id}/auctions",
                headers={"Authorization": f"Bearer {token}"},
                params={"namespace": DYNAMIC_NAMESPACE},
            )
        result["http_status"] = resp.status_code
        if not resp.is_success:
            result["error"] = f"HTTP {resp.status_code}: {resp.text[:300]}"
            return result

        data = resp.json()
    except Exception as exc:
        result["error"] = str(exc)
        return result

    auctions = data.get("auctions", [])
    result["total_auctions"] = len(auctions)
    result["sample_auctions"] = auctions[:3]

    prices: dict[int, int] = {}
    quantities: dict[int, int] = {}
    for auction in auctions:
        item_id  = auction.get("item", {}).get("id")
        buyout   = auction.get("buyout", 0)  # 0 = offre pure, pas de prix direct
        quantity = auction.get("quantity", 1) or 1
        if not item_id or buyout <= 0:
            continue
        unit_price = buyout // quantity
        if unit_price > 0:
            if item_id not in prices or unit_price < prices[item_id]:
                prices[item_id] = unit_price
            quantities[item_id] = quantities.get(item_id, 0) + quantity

    result["ok"]         = True
    result["prices"]     = prices
    result["quantities"] = quantities
    return result


async def fetch_commodities_from_api() -> dict:
    """
    Appelle directement l'endpoint Blizzard GET /data/wow/auctions/commodities.
    Retourne un dict de debug + les prix parsés :
    {
        "ok": bool,
        "http_status": int,
        "error": str | None,
        "total_auctions": int,
        "sample_auctions": list,     # 3 premières entrées brutes
        "prices": {item_id: min_unit_price_copper},
    }
    Utilisé à la fois par la route de sync et la route de debug.
    """
    result: dict = {
        "ok": False,
        "http_status": None,
        "error": None,
        "total_auctions": 0,
        "sample_auctions": [],
        "prices": {},
        "quantities": {},
    }

    try:
        token = await get_app_token()
        params = {"namespace": DYNAMIC_NAMESPACE}  # pas de locale pour les commodités
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(
                f"{API_BASE}/data/wow/auctions/commodities",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
            )
        result["http_status"] = resp.status_code
        if not resp.is_success:
            result["error"] = f"HTTP {resp.status_code}: {resp.text[:300]}"
            return result

        data = resp.json()
    except Exception as exc:
        result["error"] = str(exc)
        return result

    auctions = data.get("auctions", [])
    result["total_auctions"] = len(auctions)
    result["sample_auctions"] = auctions[:3]  # apercu de la structure réelle

    # Calcul du prix minimum et de la quantité totale listée par item
    prices: dict[int, int] = {}
    quantities: dict[int, int] = {}
    for auction in auctions:
        item_id    = auction.get("item", {}).get("id")
        unit_price = auction.get("unit_price")   # commodity → prix par unité
        quantity   = auction.get("quantity", 1) or 1
        if item_id and unit_price and unit_price > 0:
            if item_id not in prices or unit_price < prices[item_id]:
                prices[item_id] = unit_price
            quantities[item_id] = quantities.get(item_id, 0) + quantity

    result["ok"]         = True
    result["prices"]     = prices
    result["quantities"] = quantities
    return result
