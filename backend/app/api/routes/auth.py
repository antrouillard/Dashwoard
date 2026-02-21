"""
Routes OAuth2 Blizzard.
Ces routes sont montées à la RACINE (/auth/...) car le redirect_uri enregistré
chez Blizzard est http://localhost:8000/auth/callback (sans préfixe /api).
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models.account import Account
from app.services import blizzard as bz

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
def login(account_id: int, db: Session = Depends(get_db)):
    """
    Lance le flow OAuth2.
    Redirige le navigateur vers la page de login Blizzard.
    """
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Compte introuvable")

    auth_url = bz.build_auth_url(account_id)
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(code: str, state: str, db: Session = Depends(get_db)):
    """
    Reçoit le code d'autorisation Blizzard, échange contre un token,
    stocke le token et redirige vers le frontend.
    """
    # Récupère le compte (state = account_id)
    try:
        account_id = int(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="State invalide")

    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Compte introuvable")

    # Échange le code contre un token
    try:
        token_data = await bz.exchange_code_for_token(code)
    except Exception:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}?sync_error=token_exchange_failed")

    access_token = token_data.get("access_token")
    expires_in = token_data.get("expires_in", 86400)  # 24h par défaut

    # Récupère le BattleTag
    battletag = await bz.get_battletag(access_token)

    # Stocke le token dans la DB
    account.blizzard_access_token = access_token
    account.blizzard_refresh_token = token_data.get("refresh_token")
    account.blizzard_token_expires_at = datetime.utcnow() + timedelta(
        seconds=expires_in
    )
    if battletag:
        account.blizzard_battletag = battletag

    db.commit()

    # Redirige vers le frontend avec signal de succès + account_id pour auto-sync
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}?sync_success=1&account_id={account_id}"
    )


@router.get("/status/{account_id}")
def auth_status(account_id: int, db: Session = Depends(get_db)):
    """Retourne l'état de connexion Blizzard pour un compte."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Compte introuvable")

    is_connected = bool(account.blizzard_access_token)
    is_expired = False
    if account.blizzard_token_expires_at:
        is_expired = account.blizzard_token_expires_at < datetime.utcnow()

    return {
        "account_id": account_id,
        "is_connected": is_connected and not is_expired,
        "battletag": account.blizzard_battletag,
        "expires_at": account.blizzard_token_expires_at,
    }


@router.delete("/logout/{account_id}")
def logout(account_id: int, db: Session = Depends(get_db)):
    """Supprime le token Blizzard stocké pour un compte."""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Compte introuvable")

    account.blizzard_access_token = None
    account.blizzard_refresh_token = None
    account.blizzard_token_expires_at = None
    db.commit()
    return {"detail": "Déconnecté"}
