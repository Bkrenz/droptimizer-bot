from . import Base, intpk, player_fk, str50, session
from .player import Player
from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import select


class SimReport(Base):
    __tablename__ = 'sim_report'

    id: Mapped[intpk]
    player_id: Mapped[player_fk]
    report_link: Mapped[str50]
    report_type: Mapped[str50]
    report_date: Mapped[DateTime] = mapped_column(DateTime)

    def __repr__(self) -> str:
        return f'<SimReport - Player: {self.player_id} - {self.report_type} - Link: {self.report_link}>'
    
    
    @staticmethod
    def add_new_report(id, link, type, date):
        new_report = SimReport(player_id = id, report_link = link, report_type = type, report_date = date)
        session.add(new_report)
        session.commit()
        return new_report

    @staticmethod
    def get_reports():
        stmt = select(SimReport)
        result = session.scalars(stmt)
        return result.all()