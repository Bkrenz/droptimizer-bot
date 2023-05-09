from . import Base, intpk, str50, session
from typing_extensions import Annotated
from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column

class Player(Base):
    __tablename__ = 'player'

    id: Mapped[intpk]
    name: Mapped[str50]
    spec: Mapped[str50]

    def __repr__(self) -> str:
        return f'<{self.name} - {self.spec}>'
    

    @staticmethod
    def get_player(stmt):
        result = session.scalars(stmt)
        player = result.first()
        return player

    @staticmethod
    def get_player_by_name(name):
        stmt = select(Player).where(Player.name.is_(name))
        return Player.get_player(stmt)

    @staticmethod
    def get_player_by_id(id):
        stmt = select(Player).where(Player.id.is_(id))
        return Player.get_player(stmt)
    
    @staticmethod
    def create_player(name, spec):
        player = Player(name=name, spec=spec)
        session.add(player)
        session.commit()
        return player