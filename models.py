from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

Base = declarative_base()


class Association(Base):
    __tablename__ = 'association'
    realestate_gid = Column(Integer, ForeignKey('realestate.gid'), primary_key=True)
    catchments_gid = Column(Integer, ForeignKey('catchments.gid'), primary_key=True)
    extra_data = Column(String(50))
    catchments = relationship("Catchments", back_populates="realestate")
    realestate = relationship("RealEstate", back_populates="catchments")


class Catchments(Base):
    __tablename__ = 'catchments'
    gid = Column(Integer, primary_key=True)
    use_id = Column(String)
    catch_type = Column(String)
    use_desc = Column(String)
    realestate = relationship("Association", back_populates="catchments")
    geom = Column(Geometry('MULTIPOLYGON', srid=4326))


class Transport(Base):
    __tablename__ = 'transport'
    gid = Column(Integer, primary_key=True)
    geom = Column(Geometry('MULTILINESTRING', srid=4326))


class RealEstate(Base):
    __tablename__ = 'realestate'
    gid = Column(Integer, primary_key=True)
    address = Column(String, unique=True)
    price = Column(String)
    url = Column(String)
    catchments = relationship("Association", back_populates="realestate")
    commute = Column(String)
    noisy = Column(String)
    geom = Column(Geometry('POINT', srid=4326))
