from assembl.tests.base import BaseTest, setUp, tearDown
from assembl.source.models import Email, Mailbox
from assembl.db import DBSession


setUp = setUp
tearDown = tearDown


class PostCase(BaseTest):
    def test_create_post(self):
        # import pdb; pdb.set_trace()
        sess, sess_inst, engine = self.make_session()

        email = Email(
            to_address='the_mailing_list@aol.com',
            from_address='john.doe@aol.com',
            subject='This is a test',
            body='Hello',
            full_message='Hello 123',
            message_id='nothing',
            in_reply_to='zazabb',
            source=Mailbox(
                name='John Does email account',
                host='localhost',
                port='123',
                username='john_doe',
                password='seekret',
                mailbox='INBOX',
                mailing_address='john_doe_mailing_list@aol.com',
                last_imported_email_uid='nothing',
            ),
        )
        sess_inst.add(email)
        sess_inst.flush()
        sess_inst.refresh(email)
        self.assertEquals(
            len(email.uuid.hex),
            32)
        sess_inst.close()
