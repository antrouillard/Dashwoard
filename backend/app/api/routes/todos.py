from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.todo import Todo
from app.models.character import Character
from app.schemas.todo import TodoCreate, TodoOut, TodoUpdate

router = APIRouter(prefix="/todos", tags=["todos"])

STATUS_FLOW = ["a_faire", "en_cours", "termine"]


@router.get("/", response_model=list[TodoOut])
def list_todos(character_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Todo)
    if character_id:
        q = q.filter(Todo.character_id == character_id)
    return q.order_by(Todo.character_id, Todo.id).all()


@router.post("/", response_model=TodoOut, status_code=201)
def create_todo(payload: TodoCreate, db: Session = Depends(get_db)):
    if not db.query(Character).filter(Character.id == payload.character_id).first():
        raise HTTPException(status_code=404, detail="Personnage introuvable")

    todo = Todo(**payload.model_dump())
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return todo


@router.patch("/{todo_id}", response_model=TodoOut)
def update_todo(todo_id: int, payload: TodoUpdate, db: Session = Depends(get_db)):
    todo = db.query(Todo).filter(Todo.id == todo_id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo introuvable")

    if payload.status and payload.status not in STATUS_FLOW:
        raise HTTPException(
            status_code=422,
            detail=f"Statut invalide. Valeurs possibles : {STATUS_FLOW}",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(todo, field, value)

    db.commit()
    db.refresh(todo)
    return todo


@router.patch("/{todo_id}/advance", response_model=TodoOut)
def advance_todo(todo_id: int, db: Session = Depends(get_db)):
    """Avance le statut au suivant dans le cycle : a_faire → en_cours → termine → a_faire."""
    todo = db.query(Todo).filter(Todo.id == todo_id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo introuvable")

    current = todo.status if todo.status in STATUS_FLOW else "a_faire"
    next_status = STATUS_FLOW[(STATUS_FLOW.index(current) + 1) % len(STATUS_FLOW)]
    todo.status = next_status

    db.commit()
    db.refresh(todo)
    return todo


@router.delete("/{todo_id}", status_code=204)
def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    todo = db.query(Todo).filter(Todo.id == todo_id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo introuvable")
    db.delete(todo)
    db.commit()
