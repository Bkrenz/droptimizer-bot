import datetime
from . import Base, intpk, str50, session
from sqlalchemy import select, DateTime
from sqlalchemy.orm import Mapped, mapped_column

class Absence(Base):
    __tablename__ = 'absences'

    id: Mapped[intpk]
    player: Mapped[str50]
    date_begin: Mapped[DateTime] = mapped_column(DateTime)
    date_end: Mapped[DateTime] = mapped_column(DateTime)
    note: Mapped[str50]

    def __repr__(self) -> str:
        return f'<Absence> Player: {self.player}, Start: {self.date_begin}, End: {self.date_end}'
    
    def save(self):
        session.add(self)
        session.commit()
    
    @staticmethod
    def get_absences() -> list:
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        result = session.query(Absence).filter(Absence.date_end > yesterday).all()
        return result
    
    def get_absence(id: int):
        result = session.query(Absence).filter(Absence.id == id)
        return result.first()
    
    @staticmethod
    def delete(id: int) -> None:
        session.query(Absence).filter(Absence.id == id).delete()
        session.commit()