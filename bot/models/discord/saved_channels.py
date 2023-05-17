from .. import Base, intpk, str50, session
from sqlalchemy import select
from sqlalchemy.orm import Mapped

class SavedChannel(Base):
    __tablename__ = 'saved_channel'

    id: Mapped[intpk]
    guild_id: Mapped[int]
    channel_id: Mapped[int]
    channel_type: Mapped[str50]

    def __repr__(self) -> str:
        return f'<SavedChannel> Guild: {self.guild_id}, Channel ID: {self.channel_id}, Type: {self.channel_type}'
    

    @staticmethod
    def get_channels_by_type(channel_type: str) -> list:
        stmt = select(SavedChannel).where(SavedChannel.channel_type.is_(channel_type))
        return session.scalars(stmt).all()
    

    @staticmethod
    def save_channel(guild_id, channel_id, channel_type) -> None:
        if not SavedChannel.check_channel_registered(channel_id):
            channel = SavedChannel(guild_id=guild_id, channel_id=channel_id, channel_type=channel_type)
            session.add(channel)
            session.commit()
    

    @staticmethod
    def check_channel_registered(channel_id) -> bool:
        stmt = select(SavedChannel).where(SavedChannel.channel_id.is_(channel_id))
        return session.scalars(stmt).first() is not None
