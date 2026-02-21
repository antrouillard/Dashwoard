from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # reconnecte si la connexion est tombée
    pool_recycle=3600,        # recycle les connexions toutes les heures
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency FastAPI : injecte une session DB et la ferme après la requête."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Crée toutes les tables si elles n'existent pas encore."""
    from app.models import account, character, guild, todo, profession, crafting, market  # noqa: F401
    Base.metadata.create_all(bind=engine)
