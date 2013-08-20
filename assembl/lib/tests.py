from colander import Invalid
from sqlalchemy.orm import relationship, backref, aliased
from sqlalchemy import (
    Column, 
    Integer, 
    Unicode, 
    ForeignKey,
)
from colanderalchemy import SQLAlchemySchemaNode
from .models import ValidateMeta
from assembl.tests.base import BaseTest
from assembl.lib.sqla import Base as SQLAlchemyBaseModel


class SampleModel(SQLAlchemyBaseModel):
    __metaclass__ = ValidateMeta
    __tablename__ = 'sample'
    id = Column(Integer, primary_key=True)
    topic = Column(Unicode(255), nullable=False)
    
class SampleModel2(SQLAlchemyBaseModel):
    __metaclass__ = ValidateMeta
    __tablename__ = 'sample_2'
    __ca_field_overrides__ = {
        'topic': {
            'name': 'the_topic',
        },
        'id': {
            'name': 'the_id',
        }
    }
    id = Column(Integer, primary_key=True)
    topic = Column(
        Unicode(255),
        nullable=False,
        )
    gerbil = Column(
        Unicode(255),
        nullable=False,
        )

class SampleOther(SQLAlchemyBaseModel):
    __metaclass__ = ValidateMeta
    __tablename__ = 'other'
    id = Column(Integer, primary_key=True)
    
class SampleModel3(SQLAlchemyBaseModel):
    __metaclass__ = ValidateMeta
    __tablename__ = 'sample_3'
    __ca_field_overrides__ = {
        'topic': {
            'name': 'the_topic',
        },
        'id': {
            'name': 'the_id',
        }
    }
    id = Column(Integer, primary_key=True)
    topic = Column(
        Unicode(255),
        nullable=False,
        )
    other_id = Column(Integer, ForeignKey('other.id', ondelete='CASCADE'))
    other = relationship(SampleOther, uselist=False)

class SampleRelatedModel(SQLAlchemyBaseModel):
    __metaclass__ = ValidateMeta
    __tablename__ = 'sample_related'
    id = Column(Integer, primary_key=True)

    sample_id = Column(Integer, ForeignKey('sample_3.id', ondelete='CASCADE'))
    sample = relationship(SampleModel3, uselist=False)


class ValidationTest(BaseTest):
    def test_validation(self):
        ca = SampleModel.__ca__

        data = {
            'id': 12,
            'topic': None,
        }
        self.assertRaises(Invalid, ca.deserialize, data)

        data = {
            'id': 12,
            'topic': 'truc',
        }
        data_dict = ca.deserialize(data)
        inst = SampleModel(**data_dict)

        self.assertEquals(inst.id, 12)
        self.assertEquals(inst.topic, 'truc')

            
    def test_validation_override(self):
        from assembl.lib.sqla import Base as SQLAlchemyBaseModel

        ca = SampleModel2.__ca__

        data = {
            'id': 12,
            'topic': 'truc',
            'gerbil': 'wak',
        }
        self.assertRaises(Invalid, ca.deserialize, data)

        sample_inst = SampleModel2(
            topic='asd',
            id=12,
            gerbil='wak',
        )

        res = ca.dictify(sample_inst)
        self.assertEquals(res['the_topic'], sample_inst.topic)
        self.assertEquals(res['the_id'], sample_inst.id)
        self.assertEquals(res['gerbil'], sample_inst.gerbil)

        data = {
            'the_id': 12,
            'the_topic': 'truc',
            'gerbil': 'wak',
        }

        new_obj = SampleModel2.__ca__.objectify(data)
        self.assertEquals(new_obj.id, 12)
        self.assertEquals(new_obj.topic, 'truc')
        self.assertEquals(new_obj.gerbil, 'wak')

        data = {
            'the_id': 12,
            'topic': 'truc',
            'gerbil': 'wak',
        }

        self.assertRaises(
            Invalid, SampleModel2.__ca__.objectify, data)


    def test_validation_relation(self):

        from assembl.lib.sqla import Base as SQLAlchemyBaseModel

        ca = SampleModel3.__ca__

        data = {
            'id': 12,
            'topic': 'truc',
        }
        self.assertRaises(Invalid, ca.deserialize, data)

        sample_inst = SampleModel3(
            topic='asd',
            id=12,
        )

        res = ca.dictify(sample_inst)
        self.assertEquals(res['the_topic'], sample_inst.topic)
        self.assertEquals(res['the_id'], sample_inst.id)

        data = {
            'the_id': 12,
            'the_topic': 'truc',
        }

        new_obj = SampleModel3.__ca__.objectify(data)
        self.assertEquals(new_obj.id, 12)
        self.assertEquals(new_obj.topic, 'truc')

        data = {
            'the_id': 12,
            'topic': 'truc',
        }

        self.assertRaises(
            Invalid, SampleModel3.__ca__.objectify, data)

