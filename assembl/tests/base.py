import sys
import unittest
import os
import logging
import transaction
from pkg_resources import get_distribution
from pyramid import testing
from pyramid.paster import get_appsettings
from sqlalchemy.orm import sessionmaker
from sqlalchemy import engine_from_config
from webtest import TestApp

import assembl
# from assembl.db import DBSession


TEST_SETTINGS = 'testing.ini'
ASSEMBL_LOC = get_distribution('assembl').location
TEST_SETTINGS_LOC = os.path.join(ASSEMBL_LOC, TEST_SETTINGS)


def make_session():
    engine = engine_from_config(
        get_appsettings(TEST_SETTINGS_LOC),
        'sqlalchemy.',
        echo=False)
    sess = sessionmaker(bind=engine)
    return sess, sess(), engine


def get_all_tables():
    sess, sess_inst, engine = make_session()
    res = engine.execute(
        'SELECT table_schema,table_name FROM '
        'information_schema.tables WHERE table_schema = '
        '\'public\' ORDER BY table_schema,table_name')
    sess_inst.close()
    return res.fetchall()

        
def drop_tables():
    # engine = sess.bind
    sess, sess_inst, engine = make_session()
    try:
        for row in get_all_tables():
            # cls.logger.info("Dropping table: %s" % row[1])
            engine.execute("drop table \"%s\" cascade" % row[1]) 
    except:
        raise Exception('Error dropping tables: %s' % (
            sys.exc_info()[1]))
    sess_inst.close()

    

def setUp():
    """
    Import me if you want your database to be cleared before going
    through your test cases.
    """
    from assembl.lib.alembic import bootstrap_db
    drop_tables()
    bootstrap_db(TEST_SETTINGS_LOC)


class BaseTest(unittest.TestCase):
    """
    Inherit from me if you want:
    * To have a TestApp instance that you can use to make fake HTTP
      requests (e.g. self.app.get('/')
    * To clear the Database rows between each tests.
    """
    logger = logging.getLogger('testing')
    make_session = staticmethod(make_session)

    def setUp(self):
        app_settings = get_appsettings(TEST_SETTINGS_LOC)
        global_config = {
            '__file__': TEST_SETTINGS_LOC,
            'here': ASSEMBL_LOC,
            }

        self.app = TestApp(assembl.main(
            global_config, **app_settings))

        testing.setUp(
            registry=self.app.app.registry,
            settings=app_settings,
        )
        
        self.clear_rows()
        
    @classmethod
    def clear_rows(cls):
        sess, sess_inst, engine = make_session()

        for row in cls.get_all_tables(engine):
            cls.logger.info("Clearing table: %s" % row[1])
            engine.execute("delete from \"%s\"" % row[1])

        sess_inst.close()


def tearDown():
    pass
