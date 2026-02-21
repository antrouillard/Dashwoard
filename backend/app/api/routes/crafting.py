"""Routes Crafting — commandes et objectifs de craft par personnage."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models.character import Character
from app.models.crafting import CraftingGoal, CraftingGoalReagent, CraftingOrder, CraftingRecipeCache
from app.schemas.crafting import (
    CraftingGoalCreate,
    CraftingGoalOut,
    CraftingGoalUpdate,
    CraftingOrderCreate,
    CraftingOrderOut,
    CraftingOrderUpdate,
    GoalReagentOut,
    GoalReagentPatch,
    RecipeDetailOut,
    RecipeOut,
    ORDER_STATUSES,
)
from app.services import blizzard as bz
from app.services import wowhead as wh

router = APIRouter(prefix="/crafting", tags=["crafting"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_order(order_id: int, db: Session) -> CraftingOrder:
    order = (
        db.query(CraftingOrder)
        .options(selectinload(CraftingOrder.character))
        .filter(CraftingOrder.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    return order


def _load_goal(goal_id: int, db: Session) -> CraftingGoal:
    goal = (
        db.query(CraftingGoal)
        .options(selectinload(CraftingGoal.character))
        .filter(CraftingGoal.id == goal_id)
        .first()
    )
    if not goal:
        raise HTTPException(status_code=404, detail="Objectif introuvable")
    return goal


def _require_character(character_id: int, db: Session) -> Character:
    char = db.query(Character).filter(Character.id == character_id).first()
    if not char:
        raise HTTPException(status_code=404, detail="Personnage introuvable")
    return char


# ── Commandes ─────────────────────────────────────────────────────────────────

@router.get("/orders", response_model=list[CraftingOrderOut])
def list_orders(
    character_id: int | None = None,
    profession: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Liste les commandes de craft.
    Filtres optionnels : character_id, profession, status.
    """
    q = db.query(CraftingOrder).options(selectinload(CraftingOrder.character))
    if character_id:
        q = q.filter(CraftingOrder.character_id == character_id)
    if profession:
        q = q.filter(CraftingOrder.profession == profession)
    if status:
        q = q.filter(CraftingOrder.status == status)
    return q.order_by(CraftingOrder.created_at.desc()).all()


@router.get("/orders/{order_id}", response_model=CraftingOrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    return _load_order(order_id, db)


@router.post("/orders", response_model=CraftingOrderOut, status_code=201)
async def create_order(payload: CraftingOrderCreate, db: Session = Depends(get_db)):
    _require_character(payload.character_id, db)
    if payload.status not in ORDER_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Statut invalide. Valeurs : {ORDER_STATUSES}",
        )
    data = payload.model_dump()
    # Résolution automatique de item_id depuis recipe_id si manquant
    if data.get("recipe_id") and not data.get("item_id"):
        detail = await bz.get_recipe_detail(data["recipe_id"])
        if detail and detail.get("item_id"):
            data["item_id"] = detail["item_id"]
            if detail.get("item_name"):
                data["item_name"] = detail["item_name"]
        # Fallback Wowhead si Blizzard static indisponible
        if not data.get("item_id") and data.get("item_name"):
            wh_result = await wh.search_item(data["item_name"])
            if wh_result:
                data["item_id"] = wh_result["item_id"]
    order = CraftingOrder(**data)
    db.add(order)
    db.commit()
    db.refresh(order)
    return _load_order(order.id, db)


@router.patch("/orders/{order_id}", response_model=CraftingOrderOut)
def update_order(order_id: int, payload: CraftingOrderUpdate, db: Session = Depends(get_db)):
    order = _load_order(order_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in ORDER_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Statut invalide. Valeurs : {ORDER_STATUSES}",
        )
    for field, value in data.items():
        setattr(order, field, value)
    db.commit()
    db.refresh(order)
    return _load_order(order.id, db)


@router.patch("/orders/{order_id}/advance", response_model=CraftingOrderOut)
def advance_order(order_id: int, db: Session = Depends(get_db)):
    """Avance le statut au suivant : a_faire → en_cours → termine → a_faire."""
    order = _load_order(order_id, db)
    current = order.status if order.status in ORDER_STATUSES else "a_faire"
    order.status = ORDER_STATUSES[(ORDER_STATUSES.index(current) + 1) % len(ORDER_STATUSES)]
    db.commit()
    db.refresh(order)
    return _load_order(order.id, db)


@router.delete("/orders/{order_id}", status_code=204)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(CraftingOrder).filter(CraftingOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    db.delete(order)
    db.commit()


# ── Objectifs ─────────────────────────────────────────────────────────────────

@router.get("/goals", response_model=list[CraftingGoalOut])
def list_goals(
    character_id: int | None = None,
    profession: str | None = None,
    db: Session = Depends(get_db),
):
    """Liste les objectifs de craft. Filtres : character_id, profession."""
    q = db.query(CraftingGoal).options(selectinload(CraftingGoal.character))
    if character_id:
        q = q.filter(CraftingGoal.character_id == character_id)
    if profession:
        q = q.filter(CraftingGoal.profession == profession)
    return q.order_by(CraftingGoal.id).all()


# ── Réactifs d'objectifs (quantités possédées) ────────────────────────────

@router.get("/goals/reagents", response_model=list[GoalReagentOut])
def list_goal_reagents(db: Session = Depends(get_db)):
    """Retourne toutes les quantités possédées pour tous les objectifs."""
    return db.query(CraftingGoalReagent).all()


@router.patch("/goals/{goal_id}/reagents/{item_id}", response_model=GoalReagentOut)
def set_goal_reagent(
    goal_id: int,
    item_id: int,
    payload: GoalReagentPatch,
    db: Session = Depends(get_db),
):
    """Upsert la quantité possédée d'un réactif pour un objectif."""
    _load_goal(goal_id, db)  # vérifie que l'objectif existe
    row = (
        db.query(CraftingGoalReagent)
        .filter_by(goal_id=goal_id, item_id=item_id)
        .first()
    )
    if row:
        row.have_qty = payload.have_qty
    else:
        row = CraftingGoalReagent(goal_id=goal_id, item_id=item_id, have_qty=payload.have_qty)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/goals/{goal_id}", response_model=CraftingGoalOut)
def get_goal(goal_id: int, db: Session = Depends(get_db)):
    return _load_goal(goal_id, db)


@router.post("/goals", response_model=CraftingGoalOut, status_code=201)
async def create_goal(payload: CraftingGoalCreate, db: Session = Depends(get_db)):
    _require_character(payload.character_id, db)
    data = payload.model_dump()
    if data.get("recipe_id") and not data.get("item_id"):
        detail = await bz.get_recipe_detail(data["recipe_id"])
        if detail and detail.get("item_id"):
            data["item_id"] = detail["item_id"]
        if not data.get("item_id") and data.get("title"):
            wh_result = await wh.search_item(data["title"])
            if wh_result:
                data["item_id"] = wh_result["item_id"]
    goal = CraftingGoal(**data)
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return _load_goal(goal.id, db)


@router.patch("/goals/{goal_id}", response_model=CraftingGoalOut)
def update_goal(goal_id: int, payload: CraftingGoalUpdate, db: Session = Depends(get_db)):
    goal = _load_goal(goal_id, db)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return _load_goal(goal.id, db)


@router.delete("/goals/{goal_id}", status_code=204)
def delete_goal(goal_id: int, db: Session = Depends(get_db)):
    goal = db.query(CraftingGoal).filter(CraftingGoal.id == goal_id).first()
    if not goal:
        raise HTTPException(status_code=404, detail="Objectif introuvable")
    db.delete(goal)
    db.commit()


# ── Backfill item_id pour les items existants ────────────────────────────────

@router.post("/backfill-item-ids", tags=["crafting"])
async def backfill_item_ids(db: Session = Depends(get_db)):
    """
    Pour tous les orders/goals qui ont un recipe_id mais pas d'item_id,
    résout item_id depuis l'API Blizzard statique et met à jour la base.
    Appeler une seule fois après migration.
    """
    updated = 0

    orders_to_fix = db.query(CraftingOrder).filter(
        CraftingOrder.recipe_id.isnot(None),
        CraftingOrder.item_id.is_(None),
    ).all()
    for order in orders_to_fix:
        detail = await bz.get_recipe_detail(order.recipe_id)
        # Fallback Wowhead si Blizzard static indisponible
        if not detail or not detail.get("item_id"):
            wh_result = await wh.search_item(order.item_name)
            if wh_result:
                order.item_id = wh_result["item_id"]
                db.add(order)
                updated += 1
                continue
        if detail and detail.get("item_id"):
            order.item_id = detail["item_id"]
            if detail.get("item_name"):
                order.item_name = detail["item_name"]
            db.add(order)
            updated += 1

    goals_to_fix = db.query(CraftingGoal).filter(
        CraftingGoal.recipe_id.isnot(None),
        CraftingGoal.item_id.is_(None),
    ).all()
    for goal in goals_to_fix:
        detail = await bz.get_recipe_detail(goal.recipe_id)
        if not detail or not detail.get("item_id"):
            wh_result = await wh.search_item(goal.title)
            if wh_result:
                goal.item_id = wh_result["item_id"]
                db.add(goal)
                updated += 1
                continue
        if detail and detail.get("item_id"):
            goal.item_id = detail["item_id"]
            db.add(goal)
            updated += 1

    db.commit()
    return {"updated": updated, "orders_checked": len(orders_to_fix), "goals_checked": len(goals_to_fix)}


# ── Recettes Blizzard (API statique, pas d'OAuth utilisateur) ─────────────────

@router.get("/professions/{profession_name}/recipes", response_model=list[RecipeOut])
async def list_profession_recipes(profession_name: str):
    """
    Liste toutes les recettes de l'extension la plus récente pour une profession.
    Source : API statique Blizzard (client credentials).
    Mis en cache 24h côté serveur.
    """
    if not profession_name.strip():
        raise HTTPException(status_code=422, detail="Nom de profession vide")
    recipes = await bz.get_profession_recipes(profession_name)
    if not recipes:
        raise HTTPException(
            status_code=404,
            detail=f"Profession '{profession_name}' introuvable ou non supportée. "
                   f"Professions disponibles : {', '.join(bz.PROFESSION_IDS.keys())}",
        )
    return recipes


@router.get("/recipes/cache", response_model=list[RecipeDetailOut])
def get_recipes_cache(db: Session = Depends(get_db)):
    """
    Retourne tous les détails de recettes persistés en base (cache DB).
    Appelé une seule fois au montage du composant React pour pré-peupler recipeDetails
    sans scraper Wowhead à nouveau.
    """
    rows = db.query(CraftingRecipeCache).all()
    return [
        {
            "recipe_id": r.recipe_id,
            "recipe_name": r.recipe_name,
            "item_id": r.item_id,
            "item_name": r.item_name,
            "reagents": json.loads(r.reagents_json),
        }
        for r in rows
    ]


@router.get("/recipes/{recipe_id}", response_model=RecipeDetailOut)
async def get_recipe_detail(recipe_id: int, item_name: str | None = None, db: Session = Depends(get_db)):
    """
    Détails d'une recette : item crafté (item_id + nom) + réactifs via Wowhead.
    1. Vérifie d'abord le cache DB (persisté entre restarts)
    2. Blizzard static API → recipe_name + item_id (si credentials dispo)
    3. Si item_id absent + item_name fourni → Wowhead search_item
    4. Réactifs → toujours via Wowhead scrape (/fr/item={item_id})
    5. Persiste le résultat en DB pour les prochains restarts
    """
    # ─ 1. Cache DB ────────────────────────────────────────────────
    cached = db.query(CraftingRecipeCache).filter_by(recipe_id=recipe_id).first()
    if cached and json.loads(cached.reagents_json):
        return {
            "recipe_id": cached.recipe_id,
            "recipe_name": cached.recipe_name,
            "item_id": cached.item_id,
            "item_name": cached.item_name,
            "reagents": json.loads(cached.reagents_json),
        }

    # ─ 2. Blizzard + Wowhead ───────────────────────────────────────
    detail = await bz.get_recipe_detail(recipe_id)

    # Résolution item_id via Wowhead search si Blizzard n'a pas pu le fournir
    if item_name and (not detail or not detail.get("item_id")):
        wh_result = await wh.search_item(item_name)
        if wh_result:
            if detail:
                detail["item_id"] = wh_result["item_id"]
                detail["item_name"] = wh_result.get("item_name") or item_name
            else:
                detail = {
                    "recipe_id": recipe_id,
                    "recipe_name": item_name,
                    "item_id": wh_result["item_id"],
                    "item_name": wh_result.get("item_name") or item_name,
                    "reagents": [],
                }

    if not detail:
        raise HTTPException(status_code=404, detail="Recette introuvable")

    # Réactifs — toujours depuis Wowhead
    if detail.get("item_id"):
        detail["reagents"] = await wh.get_reagents_by_item(detail["item_id"])

    # ─ 3. Persistance en DB ───────────────────────────────────────
    if detail.get("reagents"):  # ne persiste que si on a des réactifs
        row = cached or CraftingRecipeCache(recipe_id=recipe_id)
        row.item_id      = detail.get("item_id")
        row.item_name    = detail.get("item_name")
        row.recipe_name  = detail.get("recipe_name")
        row.reagents_json = json.dumps(detail["reagents"], ensure_ascii=False)
        db.add(row)
        db.commit()

    return detail


@router.get("/search-item", tags=["crafting"])
async def search_item(q: str):
    """
    Cherche un item WoW par nom sur Wowhead (public, sans credentials).
    Retourne {item_id, item_name} ou 404 si non trouvé.
    Utilisé comme fallback quand l'API Blizzard static n'est pas disponible.
    """
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=422, detail="Requête trop courte")
    result = await wh.search_item(q.strip())
    if not result:
        raise HTTPException(status_code=404, detail=f"Item '{q}' non trouvé sur Wowhead")
    return result


# ── Admin / Debug ─────────────────────────────────────────────────────────────

@router.delete("/admin/truncate", summary="Remet à zéro toutes les commandes et objectifs")
def truncate_crafting(db: Session = Depends(get_db)):
    """
    Supprime toutes les lignes de crafting_orders et crafting_goals.
    Réinitialise les auto-increments.
    ⚠️  Irréversible — todas las filas serán eliminadas.
    """
    db.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
    db.execute(text("TRUNCATE TABLE crafting_goal_reagents"))
    db.execute(text("TRUNCATE TABLE crafting_orders"))
    db.execute(text("TRUNCATE TABLE crafting_goals"))
    db.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    db.commit()
    return {"deleted": "crafting_orders + crafting_goals + crafting_goal_reagents truncated"}


@router.post("/admin/clear-recipe-cache", summary="Vide le cache mémoire des recettes Blizzard")
def clear_recipe_cache(db: Session = Depends(get_db)):
    """
    Purge le cache mémoire _recipe_detail_cache, _recipe_list_cache (Blizzard)
    et _recipe_reagents_cache (Wowhead scrape).
    Utile après un correctif du parseur de réactifs, sans avoir à redémarrer le serveur.
    """
    bz._recipe_detail_cache.clear()
    bz._recipe_list_cache.clear()
    wh._recipe_reagents_cache.clear()
    wh._item_search_cache.clear()
    db.query(CraftingRecipeCache).delete()
    db.commit()
    return {"cleared": True}


@router.get("/debug/recipe-raw/{recipe_id}", summary="Dump brut de l'API Blizzard pour une recette")
async def debug_recipe_raw(recipe_id: int):
    """
    Retourne directement la réponse brute de l'API Blizzard static pour /data/wow/recipe/{id}.
    Permet de voir la vraie structure JSON (tous les champs de réactifs) pour déboguer.
    """
    # Bypass le cache
    data = await bz._get_static(f"/data/wow/recipe/{recipe_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Recette introuvable (Blizzard API indisponible ou recette inexistante)")
    keys_summary = {k: type(v).__name__ for k, v in data.items()}
    return {
        "recipe_id": recipe_id,
        "keys_present": keys_summary,
        "raw": data,
    }


@router.get("/debug/recipe-wowhead/{item_id}", summary="Test du scraping Wowhead pour les réactifs (via item_id)")
async def debug_recipe_wowhead(item_id: int):
    """
    Diagnostic pas-à-pas du scraping Wowhead /fr/item={item_id}.
    """
    import re
    import httpx

    result: dict = {"item_id": item_id, "steps": {}}

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                f"https://www.wowhead.com/fr/item={item_id}",
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36",
                    "Accept-Language": "fr-FR,fr;q=0.9",
                },
            )
        result["steps"]["http_status"] = resp.status_code
        result["steps"]["http_ok"] = resp.is_success
        if not resp.is_success:
            return result
        html = resp.text
        result["steps"]["html_length"] = len(html)
    except Exception as e:
        result["steps"]["http_error"] = str(e)
        return result

    # Étape 2 : trouver le Listview JS "created-by-spell"
    listview_m = re.search(
        r"new Listview\(\{[^}]{0,500}?id:\s*'created-by-spell'(.{0,50000}?)\}\s*\);",
        html, re.DOTALL,
    )
    result["steps"]["listview_found"] = listview_m is not None
    if not listview_m:
        snippet_m = re.search(r".{0,100}created.by.spell.{0,300}", html, re.DOTALL)
        result["steps"]["created_by_snippet"] = snippet_m.group(0) if snippet_m else None
        return result

    listview_block = listview_m.group(1)
    result["steps"]["listview_block_preview"] = listview_block[:500]

    # Étape 3 : extraire data:[...]
    data_m = re.search(r"data:\s*(\[.*)", listview_block, re.DOTALL)
    result["steps"]["data_found"] = data_m is not None
    if not data_m:
        return result

    raw = data_m.group(1)
    depth, end = 0, 0
    for i, ch in enumerate(raw):
        if ch == "[": depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    data_str = raw[:end]
    result["steps"]["data_str_preview"] = data_str[:500]

    # Étape 4 : trouver reagents
    reagents_m = re.search(r'"?reagents"?\s*:\s*(\[\[.*?\]\])', data_str, re.DOTALL)
    result["steps"]["reagents_field_found"] = reagents_m is not None
    if reagents_m:
        result["steps"]["reagents_raw"] = reagents_m.group(1)

    # Résultat final
    wh._recipe_reagents_cache.pop(item_id, None)
    reagents = await wh.get_reagents_by_item(item_id)
    result["reagents_found"] = len(reagents)
    result["reagents"] = reagents
    return result
