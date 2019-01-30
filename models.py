from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from geoalchemy2 import Geometry

Base = declarative_base()


class Catchments(Base):
    __tablename__ = 'catchments'
    gid = Column(Integer, primary_key=True)
    use_id = Column(String)
    catch_type = Column(String)
    use_desc = Column(String)
    geom = Column(Geometry('MULTIPOLYGON', srid=4326))


class Transport(Base):
    __tablename__ = 'transport'
    gid = Column(Integer, primary_key=True)
    geom = Column(Geometry('MULTILINESTRING', srid=4326))


class RealEstate(Base):
    __tablename__ = 'realestate'
    gid = Column(Integer, primary_key=True)
    address = Column(String)
    price = Column(String)
    url = Column(String)
    catchment = Column(String)
    commute = Column(String)
    noisy = Column(String)
    geom = Column(Geometry('POINT', srid=4326))
