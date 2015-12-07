from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy import create_engine

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))


class Artist(Base):
    __tablename__ = 'artist'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    description = Column(String(250))
    user_id = Column(Integer, ForeignKey('user.id', onupdate="cascade"))
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,
        }


class Painting(Base):
    __tablename__ = 'painting'

    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    description = Column(String(250))
    price = Column(String(20))
    category = Column(String(250))
    filename = Column(String(250))
    artist_id = Column(Integer, ForeignKey('artist.id', onupdate="cascade"))
    artist = relationship(Artist,
        backref=backref('artist',
                         uselist=True,
                         cascade='delete,all'))
    user_id = Column(Integer, ForeignKey('user.id', onupdate="cascade"))
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'description': self.description,
            'id': self.id,
            'price': self.price,
            'category': self.category,
        }

class Comments(Base):
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True)
    content = Column(String(250), nullable=False)
    creator = Column(String(250), nullable=False)
    time = Column(DateTime, default=func.now())
    painting_id = Column(Integer, ForeignKey('painting.id', onupdate="cascade"))
    painting = relationship(Painting,
        backref=backref('painting',
                         uselist=True,
                         cascade='delete,all'))


engine = create_engine('sqlite:///artists.db')


Base.metadata.create_all(engine)