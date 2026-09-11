"""Single Motor (async MongoDB) client + the index set from BUILD_SPEC section 4.7.
Nothing here builds ad-hoc query fragments from client input — endpoints must
go through repositories/ with whitelisted filters (spec section 5.2)."""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncIOMotorClient(settings.mongodb_uri, tls=True)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[get_settings().mongodb_db]


async def ping() -> bool:
    """Used by GET /readyz — does not raise, returns False on any failure."""
    try:
        await get_client().admin.command("ping")
        return True
    except Exception:
        return False


async def ensure_indexes() -> None:
    db = get_db()
    await db.users.create_index("email", unique=True)

    await db.sites.create_index("site_code", unique=True, sparse=True)
    await db.sites.create_index("name")
    await db.sites.create_index("client")
    await db.sites.create_index("search_text")

    await db.elevators.create_index([("site_id", 1), ("elevator_id", 1)], unique=True, sparse=True)
    await db.elevators.create_index("site_id")

    await db.surveys.create_index("survey_number", unique=True)
    await db.surveys.create_index([("site_id", 1), ("updated_at", -1)])
    await db.surveys.create_index([("elevator_id", 1), ("updated_at", -1)])
    await db.surveys.create_index([("status", 1), ("updated_at", -1)])
    await db.surveys.create_index([("created_by.user_id", 1), ("updated_at", -1)])
    await db.surveys.create_index("rf.summary.overall.verdict")
    await db.surveys.create_index(
        [("survey_number", "text"), ("header.site_name_snapshot", "text"),
         ("header.client_snapshot", "text")],
        name="surveys_text_search",
    )

    await db.files.create_index("owner_id")
    await db.audit_events.create_index([("entity_id", 1), ("at", -1)])
