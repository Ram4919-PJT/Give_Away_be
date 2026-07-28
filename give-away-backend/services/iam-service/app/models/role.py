import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RoleName

if TYPE_CHECKING:
    from app.models.user import User


class Role(Base):
    __tablename__ = "roles"

    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )

    role_name: Mapped[RoleName] = mapped_column(
        Enum(RoleName, name="role_name_enum"),
        nullable=False,
        unique=True,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    users: Mapped[list["User"]] = relationship(
        back_populates="role",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Role(role_id={self.role_id}, role_name={self.role_name.value})>"