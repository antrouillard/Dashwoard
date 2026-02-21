"""
seed.py – Peuple la base avec les données de mockData.js (version Python).
Lance : python seed.py
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.db import SessionLocal, create_tables
from app.models.account import Account
from app.models.character import Character
from app.models.guild import Guild
from app.models.todo import Todo
from app.models.profession import Profession
from app.models.crafting import CraftingOrder, CraftingGoal
from app.models.weekly import WeeklyActivity
from datetime import date


def seed():
    create_tables()
    db = SessionLocal()

    try:
        # ── Compte ────────────────────────────────────────────────────────────
        account = db.query(Account).filter(Account.name == "Harmonie").first()
        if not account:
            account = Account(name="Harmonie", realm="Hyjal", region="eu", is_default=True)
            db.add(account)
            db.flush()
            print("✓ Compte Harmonie créé")

        # ── Guilde ────────────────────────────────────────────────────────────
        guild = db.query(Guild).filter(Guild.name == "Unnamed", Guild.realm == "Hyjal").first()
        if not guild:
            guild = Guild(
                name="Unnamed",
                realm="Hyjal",
                region="eu",
                faction="Alliance",
                raid_name="Citadelle du Flamboiement",
                member_count=28,
                raid_progress=json.dumps([
                    {"label": "Normal", "done": 9, "total": 9},
                    {"label": "Heroique", "done": 7, "total": 9},
                    {"label": "Mythique", "done": 2, "total": 9},
                ]),
            )
            db.add(guild)
            db.flush()
            print("✓ Guilde créée")

        # ── Personnages ───────────────────────────────────────────────────────
        chars_data = [
            {
                "name": "Ilyara", "role": "Heal", "spec": "Evoker", "class_name": "Evoker",
                "ilvl": 489, "ilvl_equipped": 487, "mythic_score": 3120,
                "gold": 4120000 * 100,  # en copper (4.12M gold)
                "time_played_seconds": 360000,
                "professions": [
                    {"name": "Herboristerie", "kp_current": 0, "kp_max": 0},
                    {"name": "Alchimie", "kp_current": 190, "kp_max": 240, "bonus": "+14% rendement"},
                ],
                "todos": [
                    {"label": "M+ 18 pour vault", "status": "a_faire"},
                    {"label": "Commander 3 crafts", "status": "en_cours"},
                    {"label": "Farm herbes 30 min", "status": "a_faire"},
                ],
            },
            {
                "name": "Kaelith", "role": "DPS", "spec": "Mage", "class_name": "Mage",
                "ilvl": 482, "ilvl_equipped": 480, "mythic_score": 2985,
                "gold": 2650000 * 100,
                "time_played_seconds": 280000,
                "professions": [
                    {"name": "Enchantement", "kp_current": 152, "kp_max": 240, "bonus": "Proc de souffle"},
                    {"name": "Couture", "kp_current": 0, "kp_max": 0},
                ],
                "todos": [
                    {"label": "World boss", "status": "termine"},
                    {"label": "Enchant bagues", "status": "a_faire"},
                ],
            },
            {
                "name": "Thorar", "role": "Tank", "spec": "Warrior", "class_name": "Warrior",
                "ilvl": 491, "ilvl_equipped": 490, "mythic_score": 3260,
                "gold": 6050000 * 100,
                "time_played_seconds": 520000,
                "professions": [
                    {"name": "Minage", "kp_current": 0, "kp_max": 0},
                    {"name": "Forge", "kp_current": 210, "kp_max": 260, "bonus": "Recettes mythiques"},
                ],
                "todos": [
                    {"label": "Raid heroique", "status": "en_cours"},
                    {"label": "Commandes forge", "status": "a_faire"},
                    {"label": "Farm minerais", "status": "a_faire"},
                ],
            },
            {
                "name": "Elyss", "role": "DPS", "spec": "Hunter", "class_name": "Hunter",
                "ilvl": 477, "ilvl_equipped": 475, "mythic_score": 2840,
                "gold": 1480000 * 100,
                "time_played_seconds": 190000,
                "professions": [
                    {"name": "Depouillement", "kp_current": 0, "kp_max": 0},
                    {"name": "Travail du cuir", "kp_current": 0, "kp_max": 0},
                ],
                "todos": [],
            },
        ]

        for cdata in chars_data:
            char = db.query(Character).filter(
                Character.name == cdata["name"],
                Character.account_id == account.id
            ).first()

            if not char:
                char = Character(
                    name=cdata["name"],
                    realm="Hyjal",
                    region="eu",
                    role=cdata["role"],
                    spec=cdata["spec"],
                    class_name=cdata["class_name"],
                    ilvl=cdata["ilvl"],
                    ilvl_equipped=cdata["ilvl_equipped"],
                    mythic_score=cdata["mythic_score"],
                    gold=cdata["gold"],
                    time_played_seconds=cdata["time_played_seconds"],
                    account_id=account.id,
                    guild_id=guild.id,
                )
                db.add(char)
                db.flush()

                for pdata in cdata["professions"]:
                    db.add(Profession(character_id=char.id, **pdata))

                for tdata in cdata["todos"]:
                    db.add(Todo(character_id=char.id, **tdata))

                print(f"✓ Personnage {char.name} créé")

        # ── Activités hebdo (exemple sur Ilyara) ─────────────────────────────
        ilyara = db.query(Character).filter(Character.name == "Ilyara").first()
        if ilyara and not db.query(WeeklyActivity).filter(WeeklyActivity.character_id == ilyara.id).first():
            weekly = [
                {"activity_type": "Vault guild", "detail": "6/9 key + 2 raids", "status": "en_cours"},
                {"activity_type": "Catalyseur", "detail": "2 charges restantes", "status": "a_faire"},
                {"activity_type": "World boss", "detail": "3 persos termines", "status": "termine"},
                {"activity_type": "Quetes metiers", "detail": "4/8 persos", "status": "a_faire"},
            ]
            for w in weekly:
                db.add(WeeklyActivity(
                    character_id=ilyara.id,
                    week_start_date=date.today(),
                    **w
                ))
            print("✓ Activités hebdo créées")

        db.commit()
        print("\n✅ Seed terminé avec succès.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Erreur : {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
