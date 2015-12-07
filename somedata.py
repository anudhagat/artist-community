from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base, Artist, Painting, User, Comments

engine = create_engine('sqlite:///artists.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


def addDB(object):

    session.add(object)
    session.commit()

# Create dummy user
user1 = User(name="Robo Barista", email="tinnyTim@udacity.com",
             picture='../../../static/blank_user.gif')
addDB(user1)


# Artists and Paintings created by User1
artist1 = Artist(user_id=user1.id, name="Vincent Van Gogh",
                 description=("Vincent Willem van Gogh was a Dutch and post-"
                              "Impressionist painter whose work had a far-"
                              "reaching influence on 20th-century art."))
addDB(artist1)
artist2 = Artist(user_id=user1.id, name="Claude Monet",
                 description=("Oscar-Claude Monet was a founder of French "
                              "Impressionist painting, and the most consistent"
                              " and prolific practitioner of the movement's "
                              "philosophy of expressing one's perceptions "
                              "before nature, especially as applied to "
                              "plein-air landscape painting."))
addDB(artist2)

artist3 = Artist(user_id=user1.id, name="Leonardo Da Vinci",
                 description="Renaissance Artist")
addDB(artist3)

artist4 = Artist(user_id=user1.id, name="Johannes Vermeer",
                 description=("Johannes Vermeer was a Dutch painter who "
                              "specialized in domestic interior scenes."))
addDB(artist4)

painting1 = Painting(user_id=user1.id, name="Sunflowers",
                     description=("Part of two series of still life paintings "
                                  "by Van Gogh.The earlier series executed in "
                                  "Paris in 1887 depicts the flowers lying on "
                                  "the ground, while the second set executed a"
                                  " year later in Arles shows bouquets of "
                                  "sunflowers in a vase."),
                     price="1,000,000,000", category="Still Life",
                     filename="static/images/01.jpg", artist_id=artist1.id)

addDB(painting1)

comment1 = Comments(content="This is my favorite Van Gogh painting!",
                    creator=user1.name, painting_id=painting1.id)
addDB(comment1)

comment2 = Comments(content="Interesting composition.",
                    creator=user1.name, painting_id=painting1.id)
addDB(comment2)

painting2 = Painting(user_id=user1.id, name="Starry Night",
                     description=("This painting depicts the view from the "
                                  "east-facing window of his asylum room at "
                                  "Saint-Remy-de-Provence, just before "
                                  "sunrise, with the addition of an idealized "
                                  "village."),
                     price="750,000,000", category="Landscape",
                     filename="static/images/02.jpg", artist_id=artist1.id)

addDB(painting2)

comment3 = Comments(content="Thick brush strokes!",
                    creator=user1.name, painting_id=painting2.id)
addDB(comment3)

comment4 = Comments(content="The use of yellow makes the painting shine.",
                    creator=user1.name, painting_id=painting2.id)
addDB(comment4)

painting3 = Painting(user_id=user1.id, name="Mona Lisa",
                     description="Portrait of a Lady",
                     price="750,000,000", category="Portrait",
                     filename="static/images/03.jpg", artist_id=artist3.id)
addDB(painting3)

painting4 = Painting(user_id=user1.id, name="Girl with a Pearl Earring",
                     description=("Portrait of a girl with a headscarf "
                                  "and a pearl earring."),
                     price="750,000,000", category="Portrait",
                     filename="static/images/06.jpg", artist_id=artist4.id)
addDB(painting4)

comment5 = Comments(content="What a smile.",
                    creator=user1.name, painting_id=painting3.id)
addDB(comment5)
comment6 = Comments(content="The scarf frames her face well.",
                    creator=user1.name, painting_id=painting4.id)
addDB(comment6)

print "Added artists, paintings and comments!"
