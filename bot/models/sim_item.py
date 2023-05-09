from . import Base, intpk, player_fk, item_fk
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

class SimItem(Base):
    __tablename__ = 'simitem'

    id: Mapped[intpk]
    player: Mapped[player_fk]
    item: Mapped[item_fk]
    value: Mapped[int]