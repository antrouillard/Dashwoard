import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.guild import Guild
from app.schemas.guild import GuildCreate, GuildOut, GuildUpdate

router = APIRouter(prefix="/guilds", tags=["guilds"])


def _serialize_progress(progress) -> str | None:
    if progress is None:
        return None
    return json.dumps([p.model_dump() for p in progress])


@router.get("/", response_model=list[GuildOut])
def list_guilds(db: Session = Depends(get_db)):
    return db.query(Guild).order_by(Guild.name).all()


@router.get("/{guild_id}", response_model=GuildOut)
def get_guild(guild_id: int, db: Session = Depends(get_db)):
    guild = db.query(Guild).filter(Guild.id == guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="Guilde introuvable")
    return guild


@router.post("/", response_model=GuildOut, status_code=201)
def create_guild(payload: GuildCreate, db: Session = Depends(get_db)):
    guild = Guild(**payload.model_dump())
    db.add(guild)
    db.commit()
    db.refresh(guild)
    return guild


@router.patch("/{guild_id}", response_model=GuildOut)
def update_guild(guild_id: int, payload: GuildUpdate, db: Session = Depends(get_db)):
    guild = db.query(Guild).filter(Guild.id == guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="Guilde introuvable")

    data = payload.model_dump(exclude_unset=True)

    if "raid_progress" in data and data["raid_progress"] is not None:
        data["raid_progress"] = json.dumps(data["raid_progress"])

    for field, value in data.items():
        setattr(guild, field, value)

    db.commit()
    db.refresh(guild)
    return guild


@router.delete("/{guild_id}", status_code=204)
def delete_guild(guild_id: int, db: Session = Depends(get_db)):
    guild = db.query(Guild).filter(Guild.id == guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="Guilde introuvable")
    db.delete(guild)
    db.commit()
