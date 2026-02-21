from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.account import Account
from app.schemas.account import AccountCreate, AccountOut, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    return db.query(Account).order_by(Account.is_default.desc(), Account.name).all()


@router.get("/default", response_model=AccountOut)
def get_default_account(db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.is_default == True).first()  # noqa: E712
    if not account:
        account = db.query(Account).first()
    if not account:
        raise HTTPException(status_code=404, detail="Aucun compte trouvé")
    return account


@router.get("/{account_id}", response_model=AccountOut)
def get_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    return account


@router.post("/", response_model=AccountOut, status_code=201)
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    # Si c'est le premier compte ou marqué is_default, retirer l'ancien défaut
    if payload.is_default:
        db.query(Account).filter(Account.is_default == True).update({"is_default": False})  # noqa: E712

    account = Account(**payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.patch("/{account_id}", response_model=AccountOut)
def update_account(account_id: int, payload: AccountUpdate, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Compte introuvable")

    data = payload.model_dump(exclude_unset=True)

    if data.get("is_default"):
        db.query(Account).filter(Account.id != account_id, Account.is_default == True).update(  # noqa: E712
            {"is_default": False}
        )

    for field, value in data.items():
        setattr(account, field, value)

    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    db.delete(account)
    db.commit()
