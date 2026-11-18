"""Database connection and session management."""

from typing import Any

from sqlalchemy import MetaData, Table, inspect, select, text

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine_options: dict[str, object] = {"echo": False}

if not settings.DATABASE_URL.startswith("sqlite"):
    engine_options.update({"pool_size": 10, "max_overflow": 20})

engine = create_async_engine(settings.DATABASE_URL, **engine_options)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


async def get_db():
    """Dependency that provides an async database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables on startup."""
    from app import models as _models  # noqa: F401 - registers SQLAlchemy metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _patch_jobs_columns(conn)
        await _patch_inventory_credentials_columns(conn)
        await _patch_inventory_v2_metadata_columns(conn)
        await _patch_inventory_v2_host_columns(conn)


async def _patch_jobs_columns(conn) -> None:
    """Idempotently add additive jobs columns for inventory v2."""

    def _existing_columns(sync_conn) -> set[str]:
        insp = inspect(sync_conn)
        return {col["name"] for col in insp.get_columns("jobs")}

    existing = await conn.run_sync(_existing_columns)

    statements: list[str] = []
    if "inventory_source_type" not in existing:
        statements.append("ALTER TABLE jobs ADD COLUMN inventory_source_type VARCHAR(40)")
    if "managed_inventory_id" not in existing:
        statements.append("ALTER TABLE jobs ADD COLUMN managed_inventory_id UUID")
    if "managed_inventory_revision" not in existing:
        statements.append("ALTER TABLE jobs ADD COLUMN managed_inventory_revision INTEGER")
    if "target_scope" not in existing:
        statements.append("ALTER TABLE jobs ADD COLUMN target_scope VARCHAR(20) NOT NULL DEFAULT 'inventory'")
    if "target_group_name" not in existing:
        statements.append("ALTER TABLE jobs ADD COLUMN target_group_name VARCHAR(255)")
    if "target_host_name" not in existing:
        statements.append("ALTER TABLE jobs ADD COLUMN target_host_name VARCHAR(255)")

    for stmt in statements:
        await conn.execute(text(stmt))


async def _patch_inventory_credentials_columns(conn) -> None:
    """Idempotently add additive inventory credential columns for become secrets."""

    def _existing_columns(sync_conn) -> set[str]:
        insp = inspect(sync_conn)
        return {col["name"] for col in insp.get_columns("inventory_credentials")}

    existing = await conn.run_sync(_existing_columns)

    statements: list[str] = []
    if "encrypted_become_secret" not in existing:
        statements.append("ALTER TABLE inventory_credentials ADD COLUMN encrypted_become_secret TEXT")
    if "become_nonce" not in existing:
        statements.append("ALTER TABLE inventory_credentials ADD COLUMN become_nonce VARCHAR(128)")
    if "become_username" not in existing:
        statements.append("ALTER TABLE inventory_credentials ADD COLUMN become_username VARCHAR(255)")

    for stmt in statements:
        await conn.execute(text(stmt))


async def _patch_inventory_v2_host_columns(conn) -> None:
    """Idempotently add additive inventory v2 host columns for host-centric editing."""

    def _existing_columns(sync_conn) -> set[str]:
        insp = inspect(sync_conn)
        return {col["name"] for col in insp.get_columns("managed_inventory_v2_hosts")}

    existing = await conn.run_sync(_existing_columns)

    statements: list[str] = []
    if "host_key" not in existing:
        statements.append("ALTER TABLE managed_inventory_v2_hosts ADD COLUMN host_key VARCHAR(120)")

    for stmt in statements:
        await conn.execute(text(stmt))

    if conn.dialect.name == "postgresql":
        await conn.execute(text("ALTER TABLE managed_inventory_v2_hosts ALTER COLUMN group_id DROP NOT NULL"))

    await conn.execute(
        text(
            """
            UPDATE managed_inventory_v2_hosts AS host
            SET host_key = host.name
            WHERE host.host_key IS NULL OR host.host_key = ''
            """
        )
    )
    await conn.execute(
        text(
            """
            INSERT INTO managed_inventory_v2_host_memberships (id, inventory_id, group_id, host_id, position)
            SELECT ('00000000-0000-4000-8000-' || substr(md5(host.id::text || host.group_id::text), 1, 12))::uuid, grp.inventory_id, host.group_id, host.id, host.position
            FROM managed_inventory_v2_hosts AS host
            JOIN managed_inventory_v2_groups AS grp ON grp.id = host.group_id
            WHERE host.group_id IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM managed_inventory_v2_host_memberships AS membership
                WHERE membership.inventory_id = grp.inventory_id
                  AND membership.group_id = host.group_id
                  AND membership.host_id = host.id
              )
            """
            if conn.dialect.name == "postgresql"
            else
            """
            INSERT INTO managed_inventory_v2_host_memberships (id, inventory_id, group_id, host_id, position)
            SELECT lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))), 2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))), 2) || '-' || lower(hex(randomblob(6))), grp.inventory_id, host.group_id, host.id, host.position
            FROM managed_inventory_v2_hosts AS host
            JOIN managed_inventory_v2_groups AS grp ON grp.id = host.group_id
            WHERE host.group_id IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM managed_inventory_v2_host_memberships AS membership
                WHERE membership.inventory_id = grp.inventory_id
                  AND membership.group_id = host.group_id
                  AND membership.host_id = host.id
              )
            """
        )
    )


async def _patch_inventory_v2_metadata_columns(conn) -> None:
    """Idempotently add additive inventory v2 display metadata columns."""

    def _existing_columns(sync_conn, table_name: str) -> set[str]:
        insp = inspect(sync_conn)
        return {col["name"] for col in insp.get_columns(table_name)}

    inventory_existing = await conn.run_sync(_existing_columns, "managed_inventories_v2")
    group_existing = await conn.run_sync(_existing_columns, "managed_inventory_v2_groups")

    statements: list[str] = []
    if "description" not in inventory_existing:
        statements.append("ALTER TABLE managed_inventories_v2 ADD COLUMN description TEXT NOT NULL DEFAULT ''")
    if "tags" not in inventory_existing:
        if conn.dialect.name == "postgresql":
            statements.append("ALTER TABLE managed_inventories_v2 ADD COLUMN tags JSON NOT NULL DEFAULT '[]'::json")
        else:
            statements.append("ALTER TABLE managed_inventories_v2 ADD COLUMN tags JSON NOT NULL DEFAULT '[]'")
    if "badges" not in inventory_existing:
        if conn.dialect.name == "postgresql":
            statements.append("ALTER TABLE managed_inventories_v2 ADD COLUMN badges JSON NOT NULL DEFAULT '[]'::json")
        else:
            statements.append("ALTER TABLE managed_inventories_v2 ADD COLUMN badges JSON NOT NULL DEFAULT '[]'")
    if "tags" not in group_existing:
        if conn.dialect.name == "postgresql":
            statements.append("ALTER TABLE managed_inventory_v2_groups ADD COLUMN tags JSON NOT NULL DEFAULT '[]'::json")
        else:
            statements.append("ALTER TABLE managed_inventory_v2_groups ADD COLUMN tags JSON NOT NULL DEFAULT '[]'")

    for stmt in statements:
        await conn.execute(text(stmt))

    def _normalize_string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        normalized: list[str] = []
        for item in value:
            if isinstance(item, str):
                stripped = item.strip()
                if stripped:
                    normalized.append(stripped)
        return normalized

    def _preview_tag(value: Any) -> str | None:
        if not isinstance(value, dict):
            return None
        preview_zone = value.get("_preview_zone")
        if not isinstance(preview_zone, str):
            return None
        stripped = preview_zone.strip()
        return stripped or None

    def _backfill_metadata(sync_conn) -> None:
        metadata = MetaData()
        inventories = Table("managed_inventories_v2", metadata, autoload_with=sync_conn)
        groups = Table("managed_inventory_v2_groups", metadata, autoload_with=sync_conn)

        for row in sync_conn.execute(select(inventories.c.id, inventories.c.tags, inventories.c.badges)).mappings():
            tags = _normalize_string_list(row["tags"])
            badges = _normalize_string_list(row["badges"])

            if not tags and badges:
                sync_conn.execute(
                    inventories.update().where(inventories.c.id == row["id"]).values(tags=badges)
                )
            elif tags and not badges:
                sync_conn.execute(
                    inventories.update().where(inventories.c.id == row["id"]).values(badges=tags)
                )

        for row in sync_conn.execute(select(groups.c.id, groups.c.tags, groups.c.group_vars)).mappings():
            tags = _normalize_string_list(row["tags"])
            preview_tag = _preview_tag(row["group_vars"])
            if not tags and preview_tag:
                sync_conn.execute(
                    groups.update().where(groups.c.id == row["id"]).values(tags=[preview_tag])
                )

    await conn.run_sync(_backfill_metadata)
