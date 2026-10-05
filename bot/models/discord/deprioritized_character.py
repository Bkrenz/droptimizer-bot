from sqlalchemy import String, UniqueConstraint, delete, select
from sqlalchemy.orm import Mapped, mapped_column

from .. import Base, intpk, session


class DeprioritizedCharacter(Base):
    __tablename__ = 'deprioritized_character'
    __table_args__ = (UniqueConstraint('guild_id', 'character_name'),)

    id: Mapped[intpk]
    guild_id: Mapped[int]
    character_name: Mapped[str] = mapped_column(String(64))

    @staticmethod
    def add(guild_id: int, character_name: str) -> bool:
        normalized_name = character_name.strip().casefold()
        existing = session.scalars(
            select(DeprioritizedCharacter).where(
                DeprioritizedCharacter.guild_id == guild_id,
                DeprioritizedCharacter.character_name == normalized_name,
            )
        ).first()
        if existing is not None:
            return False

        session.add(DeprioritizedCharacter(guild_id=guild_id, character_name=normalized_name))
        session.commit()
        return True

    @staticmethod
    def remove(guild_id: int, character_name: str) -> bool:
        normalized_name = character_name.strip().casefold()
        result = session.execute(
            delete(DeprioritizedCharacter).where(
                DeprioritizedCharacter.guild_id == guild_id,
                DeprioritizedCharacter.character_name == normalized_name,
            )
        )
        session.commit()
        return bool(result.rowcount)

    @staticmethod
    def get_for_guild(guild_id: int) -> set[str]:
        names = session.scalars(
            select(DeprioritizedCharacter.character_name).where(
                DeprioritizedCharacter.guild_id == guild_id,
            )
        ).all()
        return set(names)