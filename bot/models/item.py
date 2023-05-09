from . import Base, intpk, encounter_fk, str50, session
from sqlalchemy import select
from sqlalchemy.orm import Mapped

from ..apis.blizzard import Blizzard

class Item(Base):
    __tablename__ = 'item'

    id: Mapped[intpk]
    item_id: Mapped[int]
    name: Mapped[str50]
    icon_url: Mapped[str50]
    encounter_id: Mapped[encounter_fk]

    def __repr__(self) -> str:
        return f'<Item: ({self.item_id}) {self.name}>'



    @staticmethod
    def create_item(item_id, encounter_id):
        item_data = Blizzard.get_item_from_id(item_id=item_id)
        item_name = item_data[0]
        item_url = item_data[1]
        new_item = Item(item_id=item_id, name=item_name, icon_url=item_url, encounter_id=encounter_id)
        session.add(new_item)
        session.commit()
        return new_item
    

    @staticmethod
    def get_item_by_id(item_id):
        stmt = select(Item).where(Item.id.is_(item_id))
        return session.scalars(stmt).first()
    

    @staticmethod
    def get_item_by_blizz_id(item_id):
        stmt = select(Item).where(Item.item_id.is_(item_id))
        return session.scalars(stmt).first()
    
    
    @staticmethod
    def get_item_by_name(item_name):
        stmt = select(Item).where(Item.name.contains(item_name))
        return session.scalars(stmt).first()
    

    @staticmethod
    def get_items_from_encounter(encounter_id):
        stmt = select(Item).where(Item.encounter_id.is_(encounter_id))
        return session.scalars(stmt).all()
    

    @staticmethod
    def get_all_items():
        stmt = select(Item)
        return session.scalars(stmt).all()
    

    @staticmethod
    def get_items_by_partial_name(name):
        stmt = select(Item).where(Item.name.contains(name))
        return session.scalars(stmt).all()
