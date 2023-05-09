from . import Base, intpk, encounter_fk, str50
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Item(Base):
    __tablename__ = 'item'

    id: Mapped[intpk]
    item_id: Mapped[int]
    name: Mapped[str50]
    encounter_id: Mapped[encounter_fk]

    def __repr__(self) -> str:
        return f'<Item: ({self.item_id}) {self.name}>'