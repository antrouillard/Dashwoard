# Importer tous les modèles ici garantit que SQLAlchemy
# résout correctement toutes les relations (forward references).
from app.models.account import Account  # noqa: F401
from app.models.character import Character  # noqa: F401
from app.models.guild import Guild  # noqa: F401
from app.models.todo import Todo  # noqa: F401
from app.models.profession import Profession  # noqa: F401
from app.models.crafting import CraftingOrder, CraftingGoal  # noqa: F401
from app.models.market import AhSnapshot  # noqa: F401
from app.models.weekly import WeeklyActivity  # noqa: F401
