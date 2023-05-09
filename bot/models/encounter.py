from . import Base, intpk, str50
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

class Encounter(Base):
    __tablename__ = 'encounter'

    id: Mapped[intpk]
    name: Mapped[str50]
    boss_id: Mapped[int]

    def __repr__(self) -> str:
        return f'<Encounter: ({self.boss_id}) {self.name}>'