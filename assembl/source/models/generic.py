from datetime import datetime

from sqlalchemy.orm import relationship, backref
from sqlalchemy import (
    Column,
    Integer,
    UnicodeText,
    String,
    DateTime,
    ForeignKey,
)

from assembl.lib.sqla import Base as SQLAlchemyBaseModel


class Source(SQLAlchemyBaseModel):
    """
    A Discussion Source is where commentary that is handled in the form of
    Assembl posts comes from. 

    A discussion source should have a method for importing all content, as well
    as only importing new content. Maybe the standard interface for this should
    be `source.import()`.
    """
    __tablename__ = "source"

    id = Column(Integer, primary_key=True)
    name = Column(UnicodeText, nullable=False)
    type = Column(String(60), nullable=False)

    creation_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_import = Column(DateTime)

    discussion_id = Column(Integer, ForeignKey(
        'discussion.id', 
        ondelete='CASCADE'
    ))

    discussion = relationship(
        "Discussion", 
        backref=backref('sources', order_by=creation_date)
    )

    __mapper_args__ = {
        'polymorphic_identity': 'source',
        'polymorphic_on': type
    }

    def serializable(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "creation_date": self.creation_date.isoformat(),
            "last_import": self.last_import.isoformat(),
            "discussion_id": self.discussion_id,
        }

    def __repr__(self):
        return "<Source %s>" % repr(self.name)


class Content(SQLAlchemyBaseModel):
    """
    Content is a polymorphic class to describe what is imported from a Source.
    """
    __tablename__ = "content"

    id = Column(Integer, primary_key=True)
    type = Column(String(60), nullable=False)
    creation_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    import_date = Column(DateTime, default=datetime.utcnow)

    source_id = Column(Integer, ForeignKey('source.id', ondelete='CASCADE'))
    source = relationship(
        "Source",
        backref=backref('contents', order_by=import_date)
    )

    post = relationship("Post", uselist=False)

    __mapper_args__ = {
        'polymorphic_identity': 'content',
        'polymorphic_on': 'type',
        'with_polymorphic':'*'
    }

    def __init__(self, *args, **kwargs):
        super(Content, self).__init__(*args, **kwargs)
        from .post import Post
        self.post = self.post or Post(content=self)

    def serializable(self):
        return {
            "id": self.id,
            "type": self.type,
            "creation_date": self.creation_date.isoformat(),
            "import_date": self.import_date.isoformat(),
            "source_id": self.source_id,
            "post_id": self.post.id,
        }

    def __repr__(self):
        return "<Content %s>" % repr(self.type)

    def get_body(self):
        return ""

    def get_title(self):
        return ""
