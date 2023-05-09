import datetime
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
    def get_reports(days = 14):
        # Currently setup to only care about reports submitted in the last two weeks by default,
        # though this is open to change.  
        two_weeks_ago = datetime.datetime.now() - datetime.timedelta(days)
        result = session.query(SimReport).filter(SimReport.report_date > two_weeks_ago).all()
        return result