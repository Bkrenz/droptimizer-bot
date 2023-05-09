import functools
from typing import Type
from . import Base, intpk, player_fk, item_fk, session, str50
from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column

from .player import Player
from .item import Item

@functools.total_ordering
class SimItem(Base):
    __tablename__ = 'simitem'

    id: Mapped[intpk]
    player: Mapped[player_fk]
    item: Mapped[item_fk]
    value: Mapped[int]
    difficulty: Mapped[str50]

    def __repr__(self) -> str:
        return f'<SimItem: {Player.get_player_by_id(self.player).name} - {Item.get_item_by_id(self.item).name} - {self.value} - {self.difficulty}>'

    def __eq__(self, __value: object) -> bool:
        return self.value == __value.value
    
    def __lt__(self, __value: object) -> bool:
        return self.value < __value.value

    @staticmethod
    def create_sim_item(player_id, item_id, value, difficulty):
        new_sim_item = SimItem(player=player_id, item=item_id, value=value, difficulty=difficulty)
        session.add(new_sim_item)
        session.commit()
        return new_sim_item
    
    
    @staticmethod
    def update_sim_item(sim_item: Type['SimItem'], value):
        sim_item.value = value
        session.commit()


    @staticmethod
    def get_sim_items_for_item(item_id, difficulty):
        stmt = select(SimItem).where(SimItem.item.is_(item_id)).where(SimItem.difficulty.is_(difficulty))
        return session.scalars(stmt).all()
    

    @staticmethod
    def get_sim_items_for_player(player_id, difficulty):
        stmt = select(SimItem).where(SimItem.player.is_(player_id)).where(SimItem.difficulty.is_(difficulty))
        return session.scalars(stmt).all()
    

    @staticmethod
    def get_sim_item(player_id, item_id, difficulty):
        stmt = select(SimItem).where(SimItem.player.is_(player_id)).where(SimItem.difficulty.is_(difficulty)).where(SimItem.item.is_(item_id))
        return session.scalars(stmt).first()


    @staticmethod
    def get_all_sim_items():
        stmt = select(SimItem)
        return session.scalars(stmt).all()