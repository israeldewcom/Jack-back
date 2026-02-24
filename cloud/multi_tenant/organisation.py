from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..db.base import Base

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    subscription_tier = Column(String, default="free")  # free, pro, enterprise
    teams = relationship("Team", back_populates="organization")
    users = relationship("User", back_populates="organization")
    api_keys = relationship("APIKey", back_populates="organization")

class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    organization = relationship("Organization", back_populates="teams")
    members = relationship("User", secondary="team_members")

class TeamMember(Base):
    __tablename__ = "team_members"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), primary_key=True)
    role = Column(String)  # admin, member
