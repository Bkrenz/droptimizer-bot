from sqlalchemy import create_engine
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, mapped_column
from sqlalchemy.orm import Session

from typing_extensions import Annotated

engine = create_engine('sqlite:///tmp/tmp.db')
session = Session(engine)

str50 = Annotated[str, 50]
intpk = Annotated[int, mapped_column(primary_key=True, autoincrement=True)]

item_fk = Annotated[int, mapped_column(ForeignKey('item.id'))]
player_fk = Annotated[int, mapped_column(ForeignKey('player.id'))]
encounter_fk = Annotated[int, mapped_column(ForeignKey('encounter.id'))]
sim_report_fk = Annotated[int, mapped_column('sim_report.id')]
sim_item_fk = Annotated[int, mapped_column('sim_item.id')]

class Base(DeclarativeBase):
    type_annotation_map = {
        str50: String(50)
    }

def init():
    Base.metadata.create_all(engine)
