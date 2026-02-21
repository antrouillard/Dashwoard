"""
Routes de synchronisation — déclenche les appels à l'API Blizzard et Raider.io
pour mettre à jour les données des personnages en base.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models.account import Account
from app.models.character import Character
from app.models.profession import Profession
from app.services import blizzard as bz
from app.services import raiderio as rio

router = APIRouter(prefix="/sync", tags=["sync"])


def _require_token(account: Account) -> str:
    """Vérifie qu'un token Blizzard valide existe, lève 401 sinon."""
    if not account.blizzard_access_token:
        raise HTTPException(
            status_code=401,
            detail="Compte non connecté à Blizzard. Lance d'abord /auth/login.",
        )
    if account.blizzard_token_expires_at:
        if account.blizzard_token_expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=401,
                detail="Token Blizzard expiré. Reconnecte-toi via /auth/login.",
            )
    return account.blizzard_access_token


async def _sync_one_character(
    char: Character, access_token: str, db: Session
) -> dict:
    """
    Synchronise un personnage depuis l'API Blizzard.
    Retourne un dict avec les champs mis à jour ou une erreur.
    """
    realm = char.realm
    name = char.name

    # Appels en parallèle seraient mieux, mais on reste simple et synchrone
    profile = await bz.get_character_profile(access_token, realm, name)
    if profile is None:
        return {"name": name, "status": "not_found"}

    equipment = await bz.get_character_equipment(access_token, realm, name)
    mythic_data = await bz.get_mythic_profile(access_token, realm, name)
    professions_data = await bz.get_professions(access_token, realm, name)

    # Mise à jour des champs du personnage
    updates = bz.parse_character_update(profile, equipment)
    for field, value in updates.items():
        setattr(char, field, value)

    # Score M+
    char.mythic_score = bz.parse_mythic_score(mythic_data)

    # Professions — on recrée à chaque sync pour rester à jour
    if professions_data:
        db.query(Profession).filter(Profession.character_id == char.id).delete()
        for prof in bz.parse_professions(professions_data):
            db.add(
                Profession(
                    character_id=char.id,
                    name=prof["name"],
                    kp_current=prof["skill_points"],
                    kp_max=prof["max_skill_points"],
                )
            )

    db.add(char)
    return {"name": name, "status": "ok", "ilvl": char.ilvl_equipped, "m+": char.mythic_score}


async def _sync_raiderio_one(char: Character, db: Session) -> dict:
    """Sync Raider.io pour un personnage (API publique, pas de token)."""
    data = await rio.get_character_profile(char.realm, char.name, char.region)
    if data is None:
        return {"name": char.name, "status": "not_found_raiderio"}

    updates = rio.parse_raiderio(data)
    for field, value in updates.items():
        setattr(char, field, value)
    db.add(char)
    return {"name": char.name, "status": "ok", "raiderio_score": char.raiderio_score}


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/account/{account_id}")
async def sync_account(account_id: int, db: Session = Depends(get_db)):
    """
    Synchronise TOUS les personnages d'un compte depuis l'API Blizzard.
    L'utilisateur doit s'être connecté via /auth/login au préalable.
    """
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Compte introuvable")

    access_token = _require_token(account)

    characters = (
        db.query(Character)
        .options(selectinload(Character.professions))
        .filter(Character.account_id == account_id)
        .all()
    )

    results = []
    for char in characters:
        try:
            result = await _sync_one_character(char, access_token, db)
            results.append(result)
        except Exception as e:
            results.append({"name": char.name, "status": "error", "detail": str(e)})

    db.commit()

    synced = sum(1 for r in results if r["status"] == "ok")
    return {
        "synced": synced,
        "total": len(characters),
        "results": results,
        "synced_at": datetime.utcnow(),
    }


@router.post("/character/{character_id}")
async def sync_character(character_id: int, db: Session = Depends(get_db)):
    """Synchronise un seul personnage depuis l'API Blizzard."""
    char = (
        db.query(Character)
        .options(selectinload(Character.professions))
        .filter(Character.id == character_id)
        .first()
    )
    if not char:
        raise HTTPException(status_code=404, detail="Personnage introuvable")

    account = db.query(Account).filter(Account.id == char.account_id).first()
    access_token = _require_token(account)

    try:
        result = await _sync_one_character(char, access_token, db)
        db.commit()
        return result
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/raiderio/account/{account_id}")
async def sync_raiderio_account(account_id: int, db: Session = Depends(get_db)):
    """Sync Raider.io pour tous les personnages d'un compte (API publique, pas de token)."""
    characters = db.query(Character).filter(Character.account_id == account_id).all()
    if not characters:
        raise HTTPException(status_code=404, detail="Aucun personnage sur ce compte")

    results = []
    for char in characters:
        try:
            result = await _sync_raiderio_one(char, db)
            results.append(result)
        except Exception as e:
            results.append({"name": char.name, "status": "error", "detail": str(e)})

    db.commit()
    synced = sum(1 for r in results if r["status"] == "ok")
    return {"synced": synced, "total": len(characters), "results": results}


@router.post("/raiderio/character/{character_id}")
async def sync_raiderio_character(character_id: int, db: Session = Depends(get_db)):
    """Sync Raider.io pour un seul personnage."""
    char = db.query(Character).filter(Character.id == character_id).first()
    if not char:
        raise HTTPException(status_code=404, detail="Personnage introuvable")
    try:
        result = await _sync_raiderio_one(char, db)
        db.commit()
        return result
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
