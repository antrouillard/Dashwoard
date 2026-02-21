"""
Routes activités hebdomadaires.
Le reset WoW EU a lieu le mardi à 09h00 UTC.
"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.weekly import WeeklyActivity

router = APIRouter(prefix="/weekly", tags=["weekly"])


# ── Helpers reset ─────────────────────────────────────────────────────────────

def current_week_start() -> date:
    """Retourne le mardi de la semaine courante (dernier mardi passé)."""
    today = date.today()
    # isoweekday: 1=lundi … 7=dimanche. Mardi = 2
    days_since_tuesday = (today.isoweekday() - 2) % 7
    return today - timedelta(days=days_since_tuesday)


def next_reset() -> datetime:
    """Retourne le prochain reset (mardi 09:00 UTC)."""
    week_start = current_week_start()
    next_tuesday = week_start + timedelta(days=7)
    return datetime(next_tuesday.year, next_tuesday.month, next_tuesday.day, 9, 0, 0)


# ── Schemas inline ────────────────────────────────────────────────────────────

class WeeklyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    character_id: int
    activity_type: str
    detail: str | None = None
    status: str
    week_start_date: date
    created_at: datetime
    updated_at: datetime


class WeeklyCreate(BaseModel):
    character_id: int
    activity_type: str
    detail: str | None = None
    status: str = "a_faire"


class WeeklyUpdate(BaseModel):
    status: str | None = None
    detail: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/")
def list_weekly(
    character_id: int | None = None,
    week: str | None = None,   # "current" (défaut) ou date ISO "2026-02-18"
    db: Session = Depends(get_db),
):
    """
    Liste les activités hebdo.
    - Par défaut, retourne celles de la semaine courante.
    - week=all retourne tout l'historique.
    """
    q = db.query(WeeklyActivity)

    if character_id:
        q = q.filter(WeeklyActivity.character_id == character_id)

    if week != "all":
        target_week = current_week_start()
        if week and week != "current":
            try:
                target_week = date.fromisoformat(week)
            except ValueError:
                raise HTTPException(status_code=400, detail="Format de date invalide (YYYY-MM-DD)")
        q = q.filter(WeeklyActivity.week_start_date == target_week)

    activities = q.order_by(WeeklyActivity.character_id, WeeklyActivity.activity_type).all()

    return {
        "week_start": str(current_week_start()),
        "next_reset": next_reset().isoformat(),
        "activities": [WeeklyOut.model_validate(a) for a in activities],
    }


@router.post("/", response_model=WeeklyOut, status_code=201)
def create_weekly(payload: WeeklyCreate, db: Session = Depends(get_db)):
    activity = WeeklyActivity(
        character_id=payload.character_id,
        activity_type=payload.activity_type,
        detail=payload.detail,
        status=payload.status,
        week_start_date=current_week_start(),
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


@router.patch("/{activity_id}", response_model=WeeklyOut)
def update_weekly(activity_id: int, payload: WeeklyUpdate, db: Session = Depends(get_db)):
    activity = db.query(WeeklyActivity).filter(WeeklyActivity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activité introuvable")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(activity, field, value)

    db.commit()
    db.refresh(activity)
    return activity


@router.patch("/{activity_id}/advance", response_model=WeeklyOut)
def advance_weekly(activity_id: int, db: Session = Depends(get_db)):
    """Cycle le statut : a_faire → en_cours → termine → a_faire."""
    activity = db.query(WeeklyActivity).filter(WeeklyActivity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activité introuvable")

    cycle = {"a_faire": "en_cours", "en_cours": "termine", "termine": "a_faire"}
    activity.status = cycle.get(activity.status, "a_faire")
    db.commit()
    db.refresh(activity)
    return activity


@router.delete("/{activity_id}", status_code=204)
def delete_weekly(activity_id: int, db: Session = Depends(get_db)):
    activity = db.query(WeeklyActivity).filter(WeeklyActivity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activité introuvable")
    db.delete(activity)
    db.commit()


@router.get("/info")
def week_info():
    """Retourne les infos de reset sans avoir besoin de personnages."""
    return {
        "week_start": str(current_week_start()),
        "next_reset": next_reset().isoformat(),
    }
