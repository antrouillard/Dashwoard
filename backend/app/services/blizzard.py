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
LOCALE = "fr_FR"


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
