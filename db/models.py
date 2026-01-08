# db/models.py

from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geometry

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    last_known_location = Column(Geometry(geometry_type='POINT', srid=4326), nullable=True)
    guardians = relationship("Guardian", back_populates="user")


class Guardian(Base):
    __tablename__ = "guardians"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    phone_number = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="guardians")


class RiskZone(Base):
    __tablename__ = "risk_zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    zone = Column(Geometry(geometry_type='POLYGON', srid=4326))
    risk_score = Column(Integer)