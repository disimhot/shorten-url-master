from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, TIMESTAMP, Text, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    registered_at = Column(DateTime, server_default=func.now(), nullable=False)
    role = Column(String, nullable=False,default='user')


class Link(Base):
    __tablename__ = 'link'

    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String, nullable=False)
    short_code = Column(String, unique=True, nullable=False, index=True)
    custom_alias = Column(String, unique=True, nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    clicks = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)

class LinkArchive(Base):
    __tablename__ = "link_archive"
    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String(50))
    original_url = Column(Text)
    deleted_at = Column(DateTime(timezone=True), server_default=func.now())
    reason = Column(String(50), nullable=False)