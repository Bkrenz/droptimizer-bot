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

    @staticmethod
    def delete_before(cutoff_date: datetime.date) -> int:
        """Delete absences where date_end is before the provided cutoff_date.

        Accepts either a datetime.date or datetime.datetime. Returns the number
        of rows deleted.
        """
        if isinstance(cutoff_date, datetime.datetime):
            cutoff_dt = cutoff_date
        else:
            cutoff_dt = datetime.datetime.combine(cutoff_date, datetime.time.min)

        deleted = session.query(Absence).filter(Absence.date_end < cutoff_dt).delete()
        session.commit()
        return deleted

    @staticmethod
    def count_before(cutoff_date: datetime.date) -> int:
        """Return the number of absences where date_end is before the provided cutoff_date."""
        if isinstance(cutoff_date, datetime.datetime):
            cutoff_dt = cutoff_date
        else:
            cutoff_dt = datetime.datetime.combine(cutoff_date, datetime.time.min)

        count = session.query(Absence).filter(Absence.date_end < cutoff_dt).count()
        return count

    @staticmethod
    def get_for_player_between(player: str, start_dt: datetime.datetime, end_dt: datetime.datetime) -> list:
        """Return absences for `player` that overlap the [start_dt, end_dt] range."""
        result = session.query(Absence).filter(
            Absence.player == player,
            Absence.date_end >= start_dt,
            Absence.date_begin <= end_dt
        ).all()
        return result

    @staticmethod
    def get_all_players() -> list:
        """Return a list of distinct player names present in the absences table."""
        rows = session.query(Absence.player).distinct().all()
        return [r[0] for r in rows]