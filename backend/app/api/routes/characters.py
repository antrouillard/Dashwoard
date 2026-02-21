from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models.character import Character
from app.models.account import Account
from app.schemas.character import CharacterCreate, CharacterOut, CharacterUpdate

router = APIRouter(prefix="/characters", tags=["characters"])


def _get_or_404(character_id: int, db: Session) -> Character:
    char = (
        db.query(Character)
        .options(selectinload(Character.todos), selectinload(Character.professions))
        .filter(Character.id == character_id)
        .first()
    )
    if not char:
        raise HTTPException(status_code=404, detail="Personnage introuvable")
    return char


@router.get("/", response_model=list[CharacterOut])
def list_characters(account_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Character).options(
        selectinload(Character.todos), selectinload(Character.professions)
    )
    if account_id:
        q = q.filter(Character.account_id == account_id)
    return q.order_by(Character.name).all()


@router.get("/{character_id}", response_model=CharacterOut)
def get_character(character_id: int, db: Session = Depends(get_db)):
    return _get_or_404(character_id, db)


@router.post("/", response_model=CharacterOut, status_code=201)
def create_character(payload: CharacterCreate, db: Session = Depends(get_db)):
    # Vérifier que le compte existe
    if not db.query(Account).filter(Account.id == payload.account_id).first():
        raise HTTPException(status_code=404, detail="Compte introuvable")

    char = Character(**payload.model_dump())
    db.add(char)
    db.commit()
    db.refresh(char)
    return _get_or_404(char.id, db)


@router.patch("/{character_id}", response_model=CharacterOut)
def update_character(character_id: int, payload: CharacterUpdate, db: Session = Depends(get_db)):
    char = _get_or_404(character_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(char, field, value)
    db.commit()
    db.refresh(char)
    return _get_or_404(char.id, db)


@router.delete("/{character_id}", status_code=204)
def delete_character(character_id: int, db: Session = Depends(get_db)):
    char = db.query(Character).filter(Character.id == character_id).first()
    if not char:
        raise HTTPException(status_code=404, detail="Personnage introuvable")
    db.delete(char)
    db.commit()
