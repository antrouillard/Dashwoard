"""Routes Crafting — commandes et objectifs de craft par personnage."""

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models.character import Character
from app.models.crafting import AHPrice, CraftingGoal, CraftingGoalReagent, CraftingOrder, CraftingRecipeCache, ProfitabilityResult
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


# ── Hôtel des Ventes — Sync prix + debug ──────────────────────────────────────────

@router.post("/ah-prices/sync")
async def sync_ah_prices(db: Session = Depends(get_db)):
    """
    Récupère les prix de l'Hôtel des Ventes depuis deux sources Blizzard :
    - Commodités EU-wide  (GET /auctions/commodities)
    - Enchères realm-specific Archimonde (GET /connected-realm/{id}/auctions)
    Fusionne les résultats dans `ah_prices` (prix le plus bas gagne).
    """
    import asyncio as _asyncio
    from datetime import datetime as _dt

    # Lancement parallèle des deux fetch
    commodity_fetch, realm_fetch = await _asyncio.gather(
        bz.fetch_commodities_from_api(),
        bz.fetch_realm_auctions_from_api(),
        return_exceptions=True,
    )

    errors = []
    merged: dict[int, tuple[int, str]] = {}   # item_id → (min_price, source)
    merged_qty: dict[int, int] = {}            # item_id → total quantity listed

    # ─ Commodités ──────────────────────────────────────────────────────────
    if isinstance(commodity_fetch, Exception):
        errors.append(f"commodities exception: {commodity_fetch}")
    elif not commodity_fetch["ok"]:
        errors.append(f"commodities HTTP {commodity_fetch.get('http_status')}: {commodity_fetch.get('error')}")
    else:
        for iid, price in commodity_fetch["prices"].items():
            if iid not in merged or price < merged[iid][0]:
                merged[iid] = (price, "commodity")
        for iid, qty in commodity_fetch.get("quantities", {}).items():
            merged_qty[iid] = merged_qty.get(iid, 0) + qty

    # ─ Realm auctions ──────────────────────────────────────────────────────
    realm_cr_id = None
    if isinstance(realm_fetch, Exception):
        errors.append(f"realm exception: {realm_fetch}")
    elif not realm_fetch["ok"]:
        errors.append(f"realm HTTP {realm_fetch.get('http_status')}: {realm_fetch.get('error')}")
    else:
        realm_cr_id = realm_fetch.get("connected_realm_id")
        for iid, price in realm_fetch["prices"].items():
            if iid not in merged or price < merged[iid][0]:
                merged[iid] = (price, "realm")
        for iid, qty in realm_fetch.get("quantities", {}).items():
            merged_qty[iid] = merged_qty.get(iid, 0) + qty

    if not merged:
        raise HTTPException(
            status_code=502,
            detail={"message": "Aucun prix récupéré", "errors": errors},
        )

    # ─ Bulk upsert ─────────────────────────────────────────────────────────
    now = _dt.utcnow()
    for item_id, (min_price, source) in merged.items():
        row = db.get(AHPrice, item_id)
        qty = merged_qty.get(item_id)
        if row:
            row.min_price_copper = min_price
            row.quantity_listed  = qty
            row.source           = source
            row.fetched_at       = now
        else:
            db.add(AHPrice(item_id=item_id, min_price_copper=min_price, quantity_listed=qty, source=source, fetched_at=now))
    db.commit()

    commodity_count = sum(1 for _, s in merged.values() if s == "commodity")
    realm_count     = sum(1 for _, s in merged.values() if s == "realm")

    return {
        "ok":              True,
        "items_upserted":  len(merged),
        "commodity_items": commodity_count,
        "realm_items":     realm_count,
        "realm":           realm_fetch.get("realm") if not isinstance(realm_fetch, Exception) else None,
        "connected_realm_id": realm_cr_id,
        "fetched_at":      now.isoformat(),
        "warnings":        errors if errors else None,
    }


@router.get("/ah-prices/status")
def get_ah_prices_status(db: Session = Depends(get_db)):
    """
    Retourne le nombre de prix stockés en base (total + par source) et l'horodatage du dernier sync.
    """
    from sqlalchemy import func as sqlfunc
    row = db.query(
        sqlfunc.count(AHPrice.item_id).label("count"),
        sqlfunc.max(AHPrice.fetched_at).label("last_sync"),
    ).one()
    commodity_count = db.query(sqlfunc.count(AHPrice.item_id)).filter(AHPrice.source == "commodity").scalar()
    realm_count     = db.query(sqlfunc.count(AHPrice.item_id)).filter(AHPrice.source == "realm").scalar()
    return {
        "items_count":      row.count,
        "commodity_items":  commodity_count,
        "realm_items":      realm_count,
        "last_sync_at":     row.last_sync.isoformat() if row.last_sync else None,
    }


@router.get("/ah-prices/items")
def get_ah_prices_for_items(ids: str = "", db: Session = Depends(get_db)):
    """
    Retourne les prix AH stockés en base pour une liste d'item_id.
    Paramètre : ids=1234,5678,9012  (ids séparés par virgule)
    Réponse   : { item_id: min_price_copper, ... }
    Utilisé par le frontend pour afficher les prix dans les cartes commandes/objectifs/matières.
    """
    if not ids.strip():
        return {}
    try:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError:
        return {}
    if not id_list:
        return {}
    rows = db.query(AHPrice).filter(AHPrice.item_id.in_(id_list)).all()
    return {row.item_id: row.min_price_copper for row in rows}


@router.get("/debug/ah-price/{item_id}")
async def debug_ah_price(item_id: int, db: Session = Depends(get_db)):
    """
    Route de diagnostic pour un item_id donné :
    - Retourne le prix stocké en base (ah_prices) avec sa source
    - Vérifie dans l'API commodités EU (items stackables)
    - Vérifie dans l'API realm AH Archimonde (équipements)
    - Montre les 3 premières enchères brutes de chaque source
    La DB peut avoir un prix "realm" même si l'item est absent des commodités — c'est normal.
    """
    # ─ Prix en base ──────────────────────────────────────────────────────────
    db_row = db.get(AHPrice, item_id)
    db_info = (
        {
            "min_price_copper": db_row.min_price_copper,
            "source":           db_row.source,
            "fetched_at":       db_row.fetched_at.isoformat(),
        }
        if db_row
        else None
    )

    # ─ Vérification dans les commodités EU (items stackables, namespace dynamic-eu) ──
    commodity_fetch = await bz.fetch_commodities_from_api()
    commodity_result = None
    if commodity_fetch["ok"]:
        price = commodity_fetch["prices"].get(item_id)
        commodity_result = {
            "found_in_api":      price is not None,
            "min_price_copper":  price,
            "note":              "Items stackables EU (consommables, matériaux). Absent = normal pour l'équipement.",
        }

    # ─ Vérification dans le realm AH Archimonde (équipements, enchères spécifiques) ──
    realm_fetch = await bz.fetch_realm_auctions_from_api()
    realm_result = None
    if realm_fetch["ok"]:
        price = realm_fetch["prices"].get(item_id)
        realm_result = {
            "found_in_api":      price is not None,
            "min_price_copper":  price,
            "realm":             realm_fetch.get("realm"),
            "note":              "Enchères realm-specific (équipement, BoE). Absent = item non listé en ce moment.",
        }

    return {
        "item_id":    item_id,
        "db_price":   db_info,
        "explanation": (
            f"Prix en DB provient de '{db_info['source']}'. "
            + ("L'API commodity ne couvre que les items stackables (consommables, matériaux) — "
               "l'absence ici est normale pour l'équipement." if db_info and db_info["source"] == "realm"
               else "")
        ) if db_info else "Aucun prix en DB pour cet item.",
        "commodity_api": {
            "ok":            commodity_fetch["ok"],
            "http_status":   commodity_fetch["http_status"],
            "error":         commodity_fetch["error"],
            "total_auctions": commodity_fetch["total_auctions"],
            "sample_auctions": commodity_fetch["sample_auctions"],
            "item_result":   commodity_result,
        },
        "realm_api": {
            "ok":            realm_fetch.get("ok"),
            "http_status":   realm_fetch.get("http_status"),
            "error":         realm_fetch.get("error"),
            "total_auctions": realm_fetch.get("total_auctions"),
            "sample_auctions": realm_fetch.get("sample_auctions"),
            "item_result":   realm_result,
        },
    }


# ── Analyse de rentabilité (DB-backed) ────────────────────────────────────────────

def _compute_profitability(
    profession_lower: str,
    recipes: list[dict],
    cache_rows: dict,            # {recipe_id: CraftingRecipeCache}
    ah_prices: dict,             # {item_id: min_price_copper}
    ah_age_h: float | None,
    ah_quantities: dict | None = None,  # {item_id: quantity_listed}
) -> dict:
    """
    Calcule la rentabilité pour toutes les recettes d'une profession.
    Source des réactifs : table `crafting_recipe_cache` (Wowhead).
    Source des prix      : table `ah_prices` (commodités EU).
    Retourne le dict à stocker dans ProfitabilityResult.
    """
    AH_CUT = 0.05
    rows = []
    recipes_with_prices = 0
    ah_qty = ah_quantities or {}

    for recipe in recipes:
        rid = recipe["recipe_id"]
        cached = cache_rows.get(rid)   # peut être None si pas encore en DB

        if cached:
            wowhead_reagents: list[dict] = json.loads(cached.reagents_json) if cached.reagents_json else []
            item_id   = cached.item_id
            item_name = cached.item_name or recipe["name"]
            recipe_name = cached.recipe_name or recipe["name"]
        else:
            wowhead_reagents = []
            item_id          = None
            item_name        = recipe["name"]
            recipe_name      = recipe["name"]

        crafted_count = 1

        # ─ Coût de fabrication ──────────────────────────────────────────
        craft_cost      = 0
        missing_prices: list[str] = []
        reagent_rows    = []

        for r in wowhead_reagents:
            r_item_id = r.get("item_id")
            r_qty     = r.get("quantity", 1)
            r_name    = r.get("item_name") or f"item#{r_item_id}"
            r_unit    = ah_prices.get(r_item_id, 0) if r_item_id else 0
            r_total   = r_unit * r_qty
            r_qty_listed = ah_qty.get(r_item_id) if r_item_id else None

            reagent_rows.append({
                "item_id":            r_item_id,
                "item_name":          r_name,
                "quantity":           r_qty,
                "unit_price_copper":  r_unit,
                "total_price_copper": r_total,
                "quantity_listed":    r_qty_listed,
            })

            if r_unit > 0:
                craft_cost += r_total
            else:
                missing_prices.append(r_name)

        # ─ Prix de vente et profit ────────────────────────────────────
        sell_unit  = ah_prices.get(item_id, 0) if item_id else 0
        sell_total = sell_unit * crafted_count
        sell_net   = int(sell_total * (1 - AH_CUT))
        profit     = sell_net - craft_cost
        margin     = round(profit / craft_cost * 100, 1) if craft_cost > 0 else 0
        sell_qty_listed = ah_qty.get(item_id) if item_id else None

        has_complete = (
            len(missing_prices) == 0
            and sell_unit > 0
            and craft_cost > 0
        )
        if has_complete:
            recipes_with_prices += 1

        rows.append({
            "recipe_id":              rid,
            "recipe_name":            recipe_name,
            "category":               recipe.get("category", ""),
            "tier_name":              recipe.get("tier_name", ""),
            "item_id":                item_id,
            "item_name":              item_name,
            "crafted_count":          crafted_count,
            "reagents":               reagent_rows,
            "craft_cost_copper":      craft_cost,
            "craft_cost_is_partial":  len(missing_prices) > 0,
            "sell_unit_copper":       sell_unit,
            "sell_total_copper":      sell_total,
            "sell_quantity_listed":   sell_qty_listed,
            "profit_copper":          profit,
            "profit_margin_pct":      margin,
            "missing_prices":         missing_prices,
            "has_complete_data":      has_complete,
            "reagents_known":         len(wowhead_reagents) > 0,
        })

    # Tri : 1) données complètes (meilleur profit d'abord)
    #        2) coût partiel connu (craft_cost > 0)
    #        3) aucun prix connu
    def _sort_key(r):
        if r["has_complete_data"]:
            return (0, -r["profit_copper"])
        elif r["craft_cost_copper"] > 0:
            return (1, -r["craft_cost_copper"])
        else:
            return (2, 0)

    rows.sort(key=_sort_key)
    return {
        "rows": rows,
        "recipes_total":       len(recipes),
        "recipes_cached":      len(cache_rows),
        "recipes_with_prices": recipes_with_prices,
        "ah_prices_age_h":     ah_age_h,
    }


async def _ensure_recipe_cached(
    recipe_id: int,
    recipe_name: str,
    sem: asyncio.Semaphore,
) -> dict | None:
    """
    Télécharge les détails + réactifs pour une recette.
    Retourne toujours un dict (même si vide) pour permettre la persistance
    et éviter de re-scraper indéfiniment.
    Retourne None uniquement sur exception grave.
    """
    async with sem:
        try:
            detail = await bz.get_recipe_detail(recipe_id)

            # Si Blizzard ne donne pas item_id, fallback sur Wowhead search par nom
            if not detail or not detail.get("item_id"):
                # Certaines recettes ont un préfixe : "Recette : ", "Patron : ", etc.
                search_name = recipe_name
                for prefix in ["Recette : ", "Recipe: ", "Patron : ", "Plans : ", "Schéma : ",
                                "Formule : ", "Technique : ", "Gravure : "]:
                    if search_name.startswith(prefix):
                        search_name = search_name[len(prefix):]
                        break
                wh_result = await wh.search_item(search_name)
                if wh_result:
                    if detail:
                        detail["item_id"]   = wh_result["item_id"]
                        detail["item_name"] = wh_result.get("item_name") or recipe_name
                    else:
                        detail = {
                            "recipe_id":   recipe_id,
                            "recipe_name": recipe_name,
                            "item_id":     wh_result["item_id"],
                            "item_name":   wh_result.get("item_name") or recipe_name,
                        }

            item_id = detail.get("item_id") if detail else None
            reagents: list[dict] = []
            if item_id:
                reagents = await wh.get_reagents_by_item(item_id)

            return {
                "recipe_id":   recipe_id,
                "item_id":     item_id,
                "item_name":   (detail.get("item_name") if detail else None) or recipe_name,
                "recipe_name": (detail.get("recipe_name") if detail else None) or recipe_name,
                "reagents":    reagents,
            }
        except Exception:
            return None


@router.post("/profitability/analyze")
async def analyze_profitability(profession: str, num_tiers: int = 1, db: Session = Depends(get_db)):
    """
    Lance le calcul de rentabilité pour un métier.
    1. Récupère la liste des recettes Blizzard pour chaque tier demandé.
    2. Pour toute recette absente du cache DB, scrape Wowhead en parallèle
       (semaphore = 5 requêtes simultanées max) et persiste en DB.
    3. Calcule la rentabilité via `crafting_recipe_cache` + `ah_prices`.
    4. Stocke le résultat dans `profitability_results`.

    num_tiers : 1=TWW seul, 2=TWW+DF, 0=toutes extensions.
    """
    from datetime import datetime
    from sqlalchemy import func as sqlfunc

    profession_lower = profession.lower().strip()
    recipes = await bz.get_profession_recipes(profession_lower, num_tiers=num_tiers)
    if not recipes:
        raise HTTPException(
            status_code=404,
            detail=f"Profession '{profession}' introuvable ou sans recettes.",
        )

    recipe_ids = [r["recipe_id"] for r in recipes]

    # ─ Étape 1 : recettes déjà en cache DB (toutes les entrées existantes) ─────────
    existing = (
        db.query(CraftingRecipeCache)
        .filter(CraftingRecipeCache.recipe_id.in_(recipe_ids))
        .all()
    )

    def _needs_rescrape(row) -> bool:
        """Retourne True si l'entrée doit être re-scrapée."""
        # Pas d'item_id → premier scrape a échoué (ex: Blizzard ne donne pas item_id)
        if not row.item_id:
            return True
        # Réactifs vides → Wowhead n'a pas trouvé la section created-by-spell
        reagents = json.loads(row.reagents_json) if row.reagents_json else []
        if not reagents:
            return True
        # Noms manquants dans les réactifs → résolution XML avait échoué
        if any(not r.get("item_name") for r in reagents):
            return True
        return False

    # Recettes complètement absentes de la DB
    existing_map = {e.recipe_id: e for e in existing}
    cached_ids = set(existing_map.keys())
    missing = [r for r in recipes if r["recipe_id"] not in cached_ids]
    # Recettes présentes en DB mais incomplètes (item_id null, réactifs vides, noms null)
    stale = [r for r in recipes if r["recipe_id"] in cached_ids
             and _needs_rescrape(existing_map[r["recipe_id"]])]
    missing = missing + stale

    # ─ Étape 2 : scrape Wowhead en parallèle pour les recettes manquantes/obsolètes ────
    recipes_scraped = 0
    recipes_refreshed = len(stale)
    if missing:
        sem = asyncio.Semaphore(10)  # max 10 requêtes Wowhead simultanées
        tasks = [_ensure_recipe_cached(r["recipe_id"], r["name"], sem) for r in missing]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result_item in results:
            if not isinstance(result_item, dict):
                continue
            rid = result_item["recipe_id"]
            row = db.get(CraftingRecipeCache, rid)
            if row is None:
                row = CraftingRecipeCache(recipe_id=rid)
                db.add(row)
            row.item_id       = result_item["item_id"]
            row.item_name     = result_item["item_name"]
            row.recipe_name   = result_item["recipe_name"]
            row.reagents_json = json.dumps(result_item["reagents"], ensure_ascii=False)
            recipes_scraped  += 1
        if recipes_scraped:
            db.commit()

    # ─ Étape 3 : cache complet rechargé (tous les recipe_id, même sans réactifs) ───
    cache_rows_list = (
        db.query(CraftingRecipeCache)
        .filter(CraftingRecipeCache.recipe_id.in_(recipe_ids))
        .all()
    )
    cache_rows = {c.recipe_id: c for c in cache_rows_list}

    # ─ Étape 4 : prix AH ─────────────────────────────────────────────────────
    ah_price_rows = db.query(AHPrice).all()
    ah_prices     = {row.item_id: row.min_price_copper for row in ah_price_rows}
    ah_quantities = {row.item_id: row.quantity_listed for row in ah_price_rows if row.quantity_listed is not None}
    last_sync = db.query(sqlfunc.max(AHPrice.fetched_at)).scalar()
    ah_age_h: float | None = None
    if last_sync:
        ah_age_h = round((datetime.utcnow() - last_sync).total_seconds() / 3600, 2)

    # ─ Étape 5 : calcul ──────────────────────────────────────────────────────
    result = _compute_profitability(
        profession_lower, recipes, cache_rows, ah_prices, ah_age_h, ah_quantities
    )

    # ─ Étape 6 : persistance ─────────────────────────────────────────────────
    prow = db.get(ProfitabilityResult, profession_lower)
    now  = datetime.utcnow()
    if prow:
        prow.results_json        = json.dumps(result["rows"], ensure_ascii=False)
        prow.computed_at         = now
        prow.recipes_total       = result["recipes_total"]
        prow.recipes_with_prices = result["recipes_with_prices"]
        prow.ah_prices_age_h     = result["ah_prices_age_h"]
    else:
        prow = ProfitabilityResult(
            profession           = profession_lower,
            results_json         = json.dumps(result["rows"], ensure_ascii=False),
            recipes_total        = result["recipes_total"],
            recipes_with_prices  = result["recipes_with_prices"],
            ah_prices_age_h      = result["ah_prices_age_h"],
        )
        db.add(prow)
    db.commit()

    return {
        "ok":                    True,
        "profession":            profession_lower,
        "recipes_total":         result["recipes_total"],
        "recipes_cached":        result["recipes_cached"],
        "recipes_scraped":       recipes_scraped,
        "recipes_refreshed":     recipes_refreshed,
        "recipes_with_prices":   result["recipes_with_prices"],
        "ah_prices_count":       len(ah_prices),
        "ah_prices_age_h":       ah_age_h,
        "rows_count":            len(result["rows"]),
        "computed_at":           prow.computed_at.isoformat(),
    }


@router.get("/profitability")
def get_crafting_profitability(profession: str, db: Session = Depends(get_db)):
    """
    Retourne les résultats d'analyse de rentabilité mis en cache en base.
    Lancer POST /profitability/analyze pour forcer un recalcul.
    """
    profession_lower = profession.lower().strip()
    prow = db.get(ProfitabilityResult, profession_lower)
    if not prow:
        return {
            "rows": [],
            "meta": {
                "cached": False,
                "message": "Aucune analyse en base — lancer POST /profitability/analyze d'abord.",
            },
        }

    return {
        "rows":       json.loads(prow.results_json),
        "meta": {
            "cached":             True,
            "computed_at":        prow.computed_at.isoformat(),
            "recipes_total":      prow.recipes_total,
            "recipes_with_prices": prow.recipes_with_prices,
            "ah_prices_age_h":    prow.ah_prices_age_h,
        },
    }


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
