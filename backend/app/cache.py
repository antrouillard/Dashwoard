from redis import Redis

from app.core.config import settings

_client: Redis | None = None


def get_redis() -> Redis:
    global _client
    if _client is None:
        _client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


def cache_get(key: str) -> str | None:
    return get_redis().get(key)


def cache_set(key: str, value: str, ttl: int = 300) -> None:
    """ttl en secondes (défaut 5 min)."""
    get_redis().setex(key, ttl, value)


def cache_delete(key: str) -> None:
    get_redis().delete(key)
