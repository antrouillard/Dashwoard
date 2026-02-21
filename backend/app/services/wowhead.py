"""
Service Wowhead — recherche d'items et résolution de noms.
Utilise les endpoints publics Wowhead (pas de credentials requis).
"""

import re
import httpx

WOWHEAD_BASE = "https://www.wowhead.com"
WOWHEAD_LOCALE = "fr"

# Cache mémoire nom → item_id (pas de TTL, les IDs Wowhead sont stables)
_item_search_cache: dict[str, int | None] = {}
# Cache mémoire recipe_id → liste de réactifs
_recipe_reagents_cache: dict[int, list[dict]] = {}


async def search_item(name: str, locale: str = WOWHEAD_LOCALE) -> dict | None:
    """
    Cherche un item par nom sur Wowhead et retourne {item_id, item_name}.
    Utilise l'endpoint de suggestions publiques (pas de credentials).
    Retourne None si aucun résultat trouvé.
    """
    key = f"{locale}:{name.lower().strip()}"
    if key in _item_search_cache:
        cached = _item_search_cache[key]
        return {"item_id": cached, "item_name": name} if cached else None

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{WOWHEAD_BASE}/{locale}/search/suggestions-template",
            params={"q": name},
            headers={"User-Agent": "Mozilla/5.0 (compatible; WoWDashboard/1.0)"},
        )
        if not resp.is_success:
            return None

        data = resp.json()

    # La réponse a la forme : {"results": [{"id": 239711, "name": "...", "typeName": "Objet", "type": 6, ...}]}
    # typeName FR : "Objet" = item, "Sort" = spell, "Succès" = achievement, "Quête" = quest
    # typeName EN : "Item", "Spell", "Achievement", "Quest"
    # Wowhead type codes : 6 = item / object, 3 = spell — mais "type" seul n'est pas fiable
    # car certains sorts utilitaires ont aussi type==6. On filtre d'abord par typeName explicite.
    _SKIP_TYPES = frozenset({
        "Sort", "Spell", "Enchantment",
        "Succès", "Achievement",
        "Quête", "Quest",
        "Zone", "Personnage nommé", "Guilde",
    })
    _ITEM_TYPES = frozenset({"Objet", "Item", "object", "item", "Object"})

    for result in data.get("results", []):
        type_name = result.get("typeName", "")
        result_type = result.get("type")
        # Exclure explicitement les types non-item
        if type_name in _SKIP_TYPES:
            continue
        # Accepter si c'est un type item connu, ou si type==6 et pas explicitement exclus
        if type_name in _ITEM_TYPES or result_type == 6:
            item_id = result.get("id")
            item_name = result.get("name", name)
            if item_id:
                _item_search_cache[key] = item_id
                return {"item_id": item_id, "item_name": item_name}

    _item_search_cache[key] = None
    return None


async def get_item_detail(item_id: int, locale: str = WOWHEAD_LOCALE) -> dict | None:
    """
    Retourne les détails d'un item via l'endpoint XML de Wowhead.
    Format : {item_id, name, quality (0-7), icon}
    """
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{WOWHEAD_BASE}/{locale}/item={item_id}&xml",
            headers={"User-Agent": "Mozilla/5.0 (compatible; WoWDashboard/1.0)"},
        )
        if not resp.is_success:
            return None

    # Parse l'XML minimal pour récupérer nom et qualité
    import re as _re
    text = resp.text
    name_match = _re.search(r"<name><!\[CDATA\[(.+?)\]\]></name>", text)
    quality_match = _re.search(r'<quality id="(\d+)"', text)
    icon_match = _re.search(r"<icon[^>]*><!\[CDATA\[(.+?)\]\]></icon>", text)

    return {
        "item_id": item_id,
        "name": name_match.group(1) if name_match else None,
        "quality": int(quality_match.group(1)) if quality_match else None,
        "icon": icon_match.group(1) if icon_match else None,
        "url": f"{WOWHEAD_BASE}/{locale}/item={item_id}",
    }


async def get_reagents_by_item(item_id: int) -> list[dict]:
    """
    Récupère les réactifs de base d'un item depuis la page Wowhead.

    La page ne rend pas le tableau en HTML statique — les données sont dans un
    bloc JS embarqué :
      new Listview({..., id: 'created-by-spell', ...,
        data: [{"creates":[item_id,1,1], "reagents":[[rid,qty],...], ...}]})

    On extrait le bloc `data:[...]` de ce Listview et on parse le champ `reagents`.
    Les noms sont résolus via l'endpoint XML Wowhead (/fr/item={id}&xml).

    Retourne [{item_id, item_name, quantity}]. Cache en mémoire.
    """
    if item_id in _recipe_reagents_cache:
        return _recipe_reagents_cache[item_id]

    reagents: list[dict] = []

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                f"{WOWHEAD_BASE}/fr/item={item_id}",
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
                    ),
                    "Accept-Language": "fr-FR,fr;q=0.9",
                },
            )
        if not resp.is_success:
            _recipe_reagents_cache[item_id] = []
            return []

        html = resp.text

        # ── 1. Localiser le bloc Listview "created-by-spell" dans le JS ──────
        # Pattern : new Listview({...id: 'created-by-spell'...data: [...]...})
        # On cherche depuis "created-by-spell" jusqu'à la fin du Listview call.
        listview_m = re.search(
            r"new Listview\(\{[^}]{0,500}?id:\s*'created-by-spell'(.{0,50000}?)\}\s*\);",
            html,
            re.DOTALL,
        )
        if not listview_m:
            _recipe_reagents_cache[item_id] = []
            return []

        listview_block = listview_m.group(1)

        # ── 2. Extraire le tableau data:[...] ─────────────────────────────────
        # Il contient les objets spell avec "reagents":[[id,qty],...]
        data_m = re.search(r"data:\s*(\[.*)", listview_block, re.DOTALL)
        if not data_m:
            _recipe_reagents_cache[item_id] = []
            return []

        # Extraire l'array JSON en comptant les crochets
        raw = data_m.group(1)
        depth = 0
        end = 0
        for i, ch in enumerate(raw):
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        data_str = raw[:end]

        # ── 3. Trouver le champ "reagents" dans cette chaîne ─────────────────
        # Format : "reagents":[[236761,20],[...]]  ou  reagents:[[236761,20]]
        reagents_m = re.search(
            r'"?reagents"?\s*:\s*(\[\[.*?\]\])',
            data_str,
            re.DOTALL,
        )
        if not reagents_m:
            _recipe_reagents_cache[item_id] = []
            return []

        pairs = re.findall(r'\[(\d+)\s*,\s*(\d+)\]', reagents_m.group(1))

        for rid_str, qty_str in pairs:
            reagents.append({
                "item_id": int(rid_str),
                "item_name": None,
                "quantity": int(qty_str),
            })

    except Exception:
        pass

    # ── 4. Résolution des noms via XML Wowhead ────────────────────────────────
    for r in reagents:
        if not r["item_id"]:
            continue
        try:
            async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
                xresp = await client.get(
                    f"{WOWHEAD_BASE}/fr/item={r['item_id']}&xml",
                    headers={"User-Agent": "Mozilla/5.0"},
                )
            if xresp.is_success:
                nm = re.search(r"<name><!\[CDATA\[(.+?)\]\]></name>", xresp.text)
                if nm:
                    r["item_name"] = nm.group(1)
        except Exception:
            pass

    _recipe_reagents_cache[item_id] = reagents
    return reagents

