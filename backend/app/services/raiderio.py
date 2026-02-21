"""
Service Raider.io — API publique, aucune clé requise.
Docs : https://raider.io/api
"""

import json
from datetime import datetime

import httpx

API_BASE = "https://raider.io/api/v1"


async def get_character_profile(
    realm: str, name: str, region: str = "eu"
) -> dict | None:
    """
    Récupère le profil Raider.io complet :
    score M+, ranks (world/region/realm), best runs de la saison courante.
    """
    params = {
        "region": region,
        "realm": realm.lower(),
        "name": name,
        "fields": "mythic_plus_scores_by_season:current,mythic_plus_best_runs:all,mythic_plus_ranks",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{API_BASE}/characters/profile", params=params)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()


def parse_raiderio(data: dict | None) -> dict:
    """
    Extrait les champs utiles depuis la réponse Raider.io.
    Retourne un dict prêt à être appliqué sur le modèle Character.
    """
    if not data:
        return {}

    update: dict = {}

    # Score M+ (saison courante)
    seasons = data.get("mythic_plus_scores_by_season", [])
    if seasons:
        update["raiderio_score"] = float(seasons[0].get("scores", {}).get("all", 0))

    # Rangs
    ranks = data.get("mythic_plus_ranks", {})
    overall = ranks.get("overall", {})
    update["raiderio_rank_world"] = overall.get("world") or None
    update["raiderio_rank_region"] = overall.get("region") or None
    update["raiderio_rank_realm"] = overall.get("realm") or None

    # 5 meilleurs runs (on garde les infos essentielles)
    raw_runs = data.get("mythic_plus_best_runs", [])[:5]
    best_runs = [
        {
            "dungeon": run.get("dungeon"),
            "short_name": run.get("short_name"),
            "mythic_level": run.get("mythic_level"),
            "score": run.get("score"),
            "affixes": [a.get("name") for a in run.get("affixes", [])],
            "completed_at": run.get("completed_at"),
        }
        for run in raw_runs
    ]
    update["raiderio_best_runs"] = json.dumps(best_runs, ensure_ascii=False)

    update["raiderio_last_sync_at"] = datetime.utcnow()

    return update
