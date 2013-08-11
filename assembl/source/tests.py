from assembl.tests.base import BaseTest
from assembl.source.models import Email, Mailbox


class PostCase(BaseTest):
    def test_create_post(self):
        # import pdb; pdb.set_trace()

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
        self.session.add(email)
        self.session.flush()
        self.session.refresh(email)
        self.assertEquals(
            len(email.uuid.hex),
            32)
        self.session.close()
