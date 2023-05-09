from . import Base, intpk, str50, session
from sqlalchemy import select
from sqlalchemy.orm import Mapped

from ..apis.blizzard import Blizzard

class Encounter(Base):
    __tablename__ = 'encounter'

    id: Mapped[intpk]
    name: Mapped[str50]
    boss_id: Mapped[int]

    def __repr__(self) -> str:
        return f'<Encounter: ({self.boss_id}) {self.name}>'
    

    @staticmethod
    def create_encounter(boss_id):
        boss_data = Blizzard.get_boss_from_id(boss_id)
        new_encounter = Encounter(name=boss_data[0], boss_id=boss_id)
        session.add(new_encounter)
        session.commit()
        return new_encounter
    

    @staticmethod
    def get_encounter_by_id(encounter_id):
        stmt = select(Encounter).where(Encounter.id.is_(encounter_id))
        return session.scalars(stmt).first()
    

    @staticmethod
    def get_encounter_by_blizz_id(encounter_id):
        stmt = select(Encounter).where(Encounter.boss_id.is_(encounter_id))
        return session.scalars(stmt).first()
    
    
    @staticmethod
    def get_encounter_by_name(encounter_name):
        stmt = select(Encounter).where(Encounter.name.is_(encounter_name))
        return session.scalars(stmt).first()