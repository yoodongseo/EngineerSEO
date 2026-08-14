"""Project credential persistence and encryption helpers."""

import base64
import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from nacl.secret import SecretBox
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.project_credential import ProjectCredential
from app.schemas.credentials import ProjectCredentialCreate, ProjectCredentialSummary, ProjectCredentialUpdate


class CredentialConfigurationError(RuntimeError):
    """Raised when secret storage is used without an encryption key."""


def _secret_box() -> SecretBox:
    if not settings.CREDENTIAL_ENCRYPTION_KEY:
        raise CredentialConfigurationError("CREDENTIAL_ENCRYPTION_KEY is required for credential secret storage")
    key = hashlib.sha256(settings.CREDENTIAL_ENCRYPTION_KEY.encode("utf-8")).digest()
    return SecretBox(key)


def encrypt_secret(secret: str) -> tuple[str, str]:
    encrypted = _secret_box().encrypt(secret.encode("utf-8"))
    nonce = base64.b64encode(encrypted.nonce).decode("ascii")
    ciphertext = base64.b64encode(encrypted.ciphertext).decode("ascii")
    return ciphertext, nonce


def decrypt_secret_value(encrypted_secret: str, nonce_value: str) -> str:
    nonce = base64.b64decode(nonce_value.encode("ascii"))
    ciphertext = base64.b64decode(encrypted_secret.encode("ascii"))
    return _secret_box().decrypt(ciphertext, nonce).decode("utf-8")


def decrypt_secret(credential: ProjectCredential) -> str:
    return decrypt_secret_value(str(credential.encrypted_secret), str(credential.nonce))


def to_credential_summary(credential: ProjectCredential) -> ProjectCredentialSummary:
    return ProjectCredentialSummary(
        ref=str(credential.ref),
        name=str(credential.name),
        credential_type=credential.credential_type,
        username=str(credential.username),
        has_secret=bool(credential.encrypted_secret),
        last_rotated_at=credential.last_rotated_at,
    )


async def list_project_credentials(db: AsyncSession, project_name: str) -> list[ProjectCredentialSummary]:
    result = await db.execute(
        select(ProjectCredential)
        .where(ProjectCredential.project_name == project_name, ProjectCredential.is_active.is_(True))
        .order_by(ProjectCredential.name.asc())
    )
    return [to_credential_summary(credential) for credential in result.scalars().all()]


async def get_project_credential(db: AsyncSession, project_name: str, ref: str) -> ProjectCredential | None:
    result = await db.execute(
        select(ProjectCredential).where(
            ProjectCredential.project_name == project_name,
            ProjectCredential.ref == ref,
            ProjectCredential.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def create_project_credential(
    db: AsyncSession,
    project_name: str,
    payload: ProjectCredentialCreate,
) -> ProjectCredentialSummary:
    ciphertext, nonce = encrypt_secret(payload.secret)
    credential = ProjectCredential(
        project_name=project_name,
        ref=f"cred_{uuid4().hex}",
        name=payload.name,
        credential_type=payload.credential_type,
        username=payload.username,
        encrypted_secret=ciphertext,
        nonce=nonce,
        key_id=settings.CREDENTIAL_ENCRYPTION_KEY_ID,
    )
    db.add(credential)
    await db.flush()
    return to_credential_summary(credential)


async def update_project_credential(
    db: AsyncSession,
    project_name: str,
    ref: str,
    payload: ProjectCredentialUpdate,
) -> ProjectCredentialSummary | None:
    credential = await get_project_credential(db, project_name, ref)
    if credential is None:
        return None
    credential.name = payload.name
    credential.username = payload.username
    if payload.secret is not None:
        ciphertext, nonce = encrypt_secret(payload.secret)
        credential.encrypted_secret = ciphertext
        credential.nonce = nonce
        credential.key_id = settings.CREDENTIAL_ENCRYPTION_KEY_ID
        credential.last_rotated_at = datetime.now(timezone.utc)
    await db.flush()
    return to_credential_summary(credential)


async def delete_project_credential(db: AsyncSession, project_name: str, ref: str) -> bool:
    credential = await get_project_credential(db, project_name, ref)
    if credential is None:
        return False
    credential.is_active = False
    await db.flush()
    return True
