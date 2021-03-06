from datetime import datetime
from itertools import chain
import urllib
import hashlib

from sqlalchemy import (
    Boolean,
    Column,
    String,
    ForeignKey,
    Integer,
    Unicode,
    DateTime,
    Time,
    Binary,
    Index
)

from sqlalchemy.orm import relationship, backref, deferred
from pyramid.security import Everyone, Authenticated

from ..lib import config
from . import Base, DiscussionBoundBase
from ..auth import *


class AgentProfile(Base):
    """
    An agent could be a person, group, bot or computer.
    Profiles describe agents, which have multiple accounts.
    Some agents might also be users of the platforms.
    """
    __tablename__ = "agent_profile"

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(1024))
    type = Column(String(60))
    accounts = relationship('AbstractAgentAccount',
        backref='profile', cascade="all, delete-orphan")

    __mapper_args__ = {
        'polymorphic_identity': 'agent_profile',
        'polymorphic_on': type,
        'with_polymorphic': '*'
    }

    def identity_accounts(self):
        return self.db.query(
            IdentityProviderAccount
            ).join(AbstractAgentAccount
            ).filter_by(profile_id=self.id)

    def email_accounts(self):
        return self.db.query(
            EmailAccount
            ).join(AbstractAgentAccount
            ).filter_by(profile_id=self.id)

    def verified_emails(self):
        # TODO: Filter request? Is there a way to know if preloaded?
        return (e for e in self.email_accounts() if e.verified)

    def display_name(self):
        # TODO: Prefer types?
        for acc in self.accounts:
            name = acc.display_name()
            if name:
                return name
        return self.name

    def merge(self, other_profile):
        session = self.db
        assert not (
            isinstance(other_profile, User) and not isinstance(self, User))
        my_accounts = {a.signature(): a for a in self.accounts}
        for other_account in other_profile.accounts:
            my_account = my_accounts.get(other_account.signature())
            if my_account:
                my_account.merge(other_account)
                session.delete(other_account)
            else:
                other_account.profile = self
        if other_profile.name and not self.name:
            self.name = other_profile.name
        # TODO: similarly for posts
        for action in session.query(Action).filter_by(
            actor_id=other_profile.id).all():
                action.actor = self

    def has_permission(self, verb, subject):
        if self is subject.owner:
            return True

        return self.db.query(Permission).filter_by(
            actor_id=self.id,
            subject_id=subject.id,
            verb=verb,
            allow=True
        ).one()

    def avatar_url(self, size=32, app_url=None, email=None):
        # First implementation: Use the gravatar URL
        if not email:
            accounts = list(self.email_accounts())
            if accounts:
                accounts.sort(key=lambda e: (e.verified, e.preferred))
                email = accounts[-1].email
        default = config.get('avatar.default_image_url') or \
            (app_url and app_url+'/static/img/icon/user.png')
        if not email:
            return default
        else:
            gravatar_default = config.get('avatar.gravatar_default')
            if gravatar_default:
                default = gravatar_default
        args = {'s': str(size)}
        if default:
            args['d'] = default
        gravatar_url_pattern = "http://www.gravatar.com/avatar/%s?%s"
        gravatar_url = gravatar_url_pattern % (
            hashlib.md5(
                email.lower()).hexdigest(), urllib.urlencode(args))
        return gravatar_url

    def serializable(self, use_email=None):
        return {
            '@type': self.external_typename(),
            '@id': self.uri_generic(self.id),
            'name': self.name or self.display_name()
        }


class AbstractAgentAccount(Base):
    """An abstract class for accounts that identify agents"""
    __tablename__ = "abstract_agent_account"
    id = Column(Integer, primary_key=True)
    type = Column(String(60))
    profile_id = Column(
        Integer,
        ForeignKey('agent_profile.id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False)
    def signature(self):
        "Identity of signature implies identity of underlying account"
        return ('abstract_agent_account', self.id)
    def merge(self, other):
        pass
    __mapper_args__ = {
        'polymorphic_identity': 'abstract_agent_account',
        'polymorphic_on': type,
        'with_polymorphic': '*'
    }



class EmailAccount(AbstractAgentAccount):
    """An email account"""
    __tablename__ = "agent_email_account"
    __mapper_args__ = {
        'polymorphic_identity': 'agent_email_account',
    }
    id = Column(Integer, ForeignKey(
        'abstract_agent_account.id',
        ondelete='CASCADE', onupdate='CASCADE'
    ), primary_key=True)
    email = Column(String(100), nullable=False, index=True)
    verified = Column(Boolean(), default=False)
    preferred = Column(Boolean(), default=False)
    active = Column(Boolean(), default=True)

    def display_name(self):
        if self.verified:
            return self.email

    def serialize_profile(self):
        return self.profile.serializable(self.email)

    def signature(self):
        return ('agent_email_account', self.email,)

    def merge(self, other):
        if other.verified:
            self.verified = True

    @staticmethod
    def get_or_make_profile(session, email, name=None):
        emails = list(session.query(EmailAccount).filter_by(
            email=email).all())
        # We do not want unverified user emails
        # This is costly. I should have proper boolean markers
        emails = [e for e in emails if e.verified or not isinstance(e.profile, User)]
        user_emails = [e for e in emails if isinstance(e.profile, User)]
        if user_emails:
            assert len(user_emails) == 1
            return user_emails[0]
        elif emails:
            # should also be 1 but less confident.
            return emails[0]
        else:
            profile = AgentProfile(name=name)
            emailAccount = EmailAccount(email=email, profile=profile)
            session.add(emailAccount)
            return emailAccount


class IdentityProvider(Base):
    """An identity provider (or sometimes a category of identity providers.)"""
    __tablename__ = "identity_provider"
    id = Column(Integer, primary_key=True)
    provider_type = Column(String(20), nullable=False)
    name = Column(String(60), nullable=False)
    # TODO: More complicated model, where trust also depends on realm.
    trust_emails = Column(Boolean, default=False)


class IdentityProviderAccount(AbstractAgentAccount):
    """An account with an external identity provider"""
    __tablename__ = "idprovider_agent_account"
    __mapper_args__ = {
        'polymorphic_identity': 'idprovider_agent_account',
    }
    id = Column(Integer, ForeignKey(
        'abstract_agent_account.id',
        ondelete='CASCADE', onupdate='CASCADE'
    ), primary_key=True)
    provider_id = Column(
        Integer,
        ForeignKey('identity_provider.id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False)
    provider = relationship(IdentityProvider)
    username = Column(String(200))
    domain = Column(String(200))
    userid = Column(String(200))

    def signature(self):
        return ('idprovider_agent_account', self.provider_id, self.username,
                self.domain, self.userid)

    def display_name(self):
        # TODO: format according to provider, ie @ for twitter.
        if self.username:
            name = self.username
        else:
            name = self.userid
        return ":".join((self.provider.provider_type, name))


class User(AgentProfile):
    """
    A Human user.
    """
    __tablename__ = "user"

    __mapper_args__ = {
        'polymorphic_identity': 'user'
    }

    id = Column(
        Integer,
        ForeignKey('agent_profile.id', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True
    )

    preferred_email = Column(Unicode(50))
    verified = Column(Boolean(), default=False)
    password = deferred(Column(Binary(115)))
    timezone = Column(Time(True))
    last_login = Column(DateTime)
    login_failures = Column(Integer, default=0)
    creation_date = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __init__(self, **kwargs):
        if kwargs.get('password'):
            from ..auth.password import hash_password
            kwargs['password'] = hash_password(kwargs['password'])

        super(User, self).__init__(**kwargs)

    def set_password(self, password):
        from ..auth.password import hash_password
        self.password = hash_password(password)

    def check_password(self, password):
        from ..auth.password import verify_password
        return verify_password(password, self.password)

    def get_preferred_email(self):
        if self.preferred_email:
            return self.preferred_email
        emails = list(self.email_accounts())
        # should I allow unverified?
        emails = [e for e in emails if e.verified]
        preferred = [e for e in emails if e.preferred]
        if preferred:
            return preferred[0].email
        if emails:
            return emails[0].email

    def merge(self, other_user):
        super(User, self).merge(other_user)
        if isinstance(other_user, User):
            session = self.db
            if other_user.preferred_email and not self.preferred_email:
                self.preferred_email = other_user.preferred_email
            if other_user.last_login:
                if self.last_login:
                    self.last_login = max(
                        self.last_login, other_user.last_login)
                else:
                    self.last_login = other_user.last_login
            self.creation_date = min(
                self.creation_date, other_user.creation_date)
            if other_user.password and not self.password:
                self.password = other_user.password
                # NOTE: The user may be confused by the implicit change of password
                # when we destroy the second account.
                # Maybe check latest login on either account?
            for extract in other_user.extracts_created:
                extract.creator = self
            for extract in other_user.extracts_owned:
                extract.owner = self
            for role in other_user.roles:
                role.user = self
            for role in other_user.local_roles:
                role.user = self
            if other_user.username and not self.username:
                self.username = other_user.username

    def send_email(self, **kwargs):
        subject = kwargs.get('subject', '')
        body = kwargs.get('body', '')

        # Send email.

    def avatar_url(self, size=32, app_url=None, email=None):
        return super(User, self).avatar_url(
            size, app_url, email or self.preferred_email)

    def display_name(self):
        if self.username:
            return self.username.username
        return super(User, self).display_name()

    def __repr__(self):
        if self.username:
            return "<User '%s'>" % self.username.username
        else:
            return "<User id=%d>" % self.id

    def get_permissions(self, discussion_id):
        from ..auth.util import get_permissions
        return get_permissions(self.id, discussion_id)

    def get_all_permissions(self):
        from ..auth import get_permissions
        from .synthesis import Discussion
        permissions = {
            Discussion.uri_generic(d_id): get_permissions(self.id, d_id)
            for (d_id,) in self.db.query(Discussion.id)}
        return permissions

    def serializable(self, use_email=None):
        ser = super(User, self).serializable()
        ser['username'] = self.display_name()
        #r['email'] = use_email or self.get_preferred_email()
        return ser


class Username(Base):
    "Optional usernames for users"
    __tablename__ = 'username'
    user_id = Column(Integer,
                     ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                     unique=True)
    username = Column(Unicode(20), primary_key=True)
    user = relationship(User, backref=backref('username', uselist=False))

    def get_id_as_str(self):
        return str(self.user_id)

class Role(Base):
    """A role that a user may have in a discussion"""
    __tablename__ = 'role'
    id = Column(Integer, primary_key=True)
    name = Column(String(20), nullable=False)

    @classmethod
    def get_role(klass, session, name):
        return session.query(klass).filter_by(name=name).first()


def populate_default_roles(session):
    roles = {r[0] for r in session.query(Role.name).all()}
    for role in SYSTEM_ROLES - roles:
        session.add(Role(name=role))


class UserRole(Base):
    """roles that a user has globally (eg admin.)"""
    __tablename__ = 'user_role'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
                     index=True)
    user = relationship(User, backref="roles")
    role_id = Column(Integer, ForeignKey('role.id', ondelete='CASCADE', onupdate='CASCADE'))
    role = relationship(Role, lazy="joined")


class LocalUserRole(DiscussionBoundBase):
    """The role that a user has in the context of a discussion"""
    __tablename__ = 'local_user_role'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'))
    user = relationship(User, backref="local_roles")
    discussion_id = Column(Integer, ForeignKey(
        'discussion.id', ondelete='CASCADE'))
    discussion = relationship('Discussion')
    role_id = Column(Integer, ForeignKey('role.id', ondelete='CASCADE', onupdate='CASCADE'))
    role = relationship(Role, lazy="joined")
    # BUG in virtuoso: It will often refuse to create an index
    # whose name exists in another schema. So having this index in
    # schemas assembl and assembl_test always fails.
    # TODO: Bug virtuoso about this,
    # or introduce the schema name in the index name as workaround.
    # __table_args__ = (
    #     Index('user_discussion_idx', 'user_id', 'discussion_id'),)

    def get_discussion_id(self):
        return self.discussion_id

    @classmethod
    def get_discussion_condition(cls, discussion_id):
        return cls.id == discussion_id


class Permission(Base):
    """A permission that a user may have"""
    __tablename__ = 'permission'
    id = Column(Integer, primary_key=True)
    name = Column(String(20), nullable=False)


def populate_default_permissions(session):
    perms = {p[0] for p in session.query(Permission.name).all()}
    for perm in ASSEMBL_PERMISSIONS - perms:
        session.add(Permission(name=perm))


class DiscussionPermission(DiscussionBoundBase):
    """Which permissions are given to which roles for a given discussion."""
    __tablename__ = 'discussion_permission'
    id = Column(Integer, primary_key=True)
    discussion_id = Column(Integer, ForeignKey(
        'discussion.id', ondelete='CASCADE', onupdate='CASCADE'))
    discussion = relationship(
        'Discussion', backref=backref("acls", lazy="joined"))
    role_id = Column(Integer, ForeignKey('role.id', ondelete='CASCADE', onupdate='CASCADE'))
    role = relationship(Role, lazy="joined")
    permission_id = Column(Integer, ForeignKey(
        'permission.id', ondelete='CASCADE', onupdate='CASCADE'))
    permission = relationship(Permission, lazy="joined")

    def role_name(self):
        return self.role.name

    def permission_name(self):
        return self.permission.name

    def get_discussion_id(self):
        return self.discussion_id

    @classmethod
    def get_discussion_condition(cls, discussion_id):
        return cls.id == discussion_id


def create_default_permissions(session, discussion):
    permissions = {p.name: p for p in session.query(Permission).all()}
    roles = {r.name: r for r in session.query(Role).all()}

    def add_perm(permission_name, role_names):
        # Note: Must be called within transaction manager
        for role in role_names:
            session.add(DiscussionPermission(
                discussion=discussion, role=roles[role],
                permission=permissions[permission_name]))
    add_perm(P_READ, [Everyone])
    add_perm(P_ADD_POST,
             [R_PARTICIPANT, R_CATCHER, R_MODERATOR, R_ADMINISTRATOR])
    add_perm(P_EDIT_POST, [R_MODERATOR, R_ADMINISTRATOR])
    add_perm(P_ADD_EXTRACT,
             [R_PARTICIPANT, R_CATCHER, R_MODERATOR, R_ADMINISTRATOR])
    add_perm(P_EDIT_EXTRACT, [R_MODERATOR, R_ADMINISTRATOR])
    add_perm(P_EDIT_MY_EXTRACT, [R_CATCHER, R_MODERATOR, R_ADMINISTRATOR])
    add_perm(P_ADD_IDEA, [R_CATCHER, R_MODERATOR, R_ADMINISTRATOR])
    add_perm(P_EDIT_IDEA, [R_CATCHER, R_MODERATOR, R_ADMINISTRATOR])
    add_perm(P_EDIT_SYNTHESIS, [R_MODERATOR, R_ADMINISTRATOR])
    add_perm(P_SEND_SYNTHESIS, [R_MODERATOR, R_ADMINISTRATOR])
    add_perm(P_ADMIN_DISC, [R_ADMINISTRATOR])
    add_perm(P_SYSADMIN, [R_ADMINISTRATOR])


class Action(DiscussionBoundBase):
    """
    An action that can be taken by an actor.
    """
    __tablename__ = 'action'

    id = Column(Integer, primary_key=True)
    type = Column(Unicode(255), nullable=False)
    creation_date = Column(DateTime, nullable=False, default=datetime.utcnow)

    __mapper_args__ = {
        'polymorphic_identity': 'action',
        'polymorphic_on': type,
        'with_polymorphic': '*'
    }

    actor_id = Column(
        Integer,
        ForeignKey('user.id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False
    )

    actor = relationship(
        "User",
        backref=backref('actions', order_by=creation_date)
    )

    verb = 'did something to'

    def __repr__(self):

        return "<%s '%s'>" % (
            self.__class__.__name__,
            " ".join([
                self.actor.display_name() if self.actor else 'nobody',
                self.verb,
                self.object_type
            ])
        )


class ActionOnPost(Action):
    """
    An action that is taken on a post. (Mixin)
    """

    post_id = Column(
        Integer,
        ForeignKey('content.id', ondelete="CASCADE", onupdate='CASCADE'),
        nullable=False
    )

    post = relationship(
        'Content',
        backref=backref('views')
    )

    object_type = 'post'

    def get_discussion_id(self):
        return self.post.get_discussion_id()

    @classmethod
    def get_discussion_condition(cls, discussion_id):
        return cls.post_id == Post.id & Post.discussion_id == discussion_id

class ViewPost(ActionOnPost):
    """
    A view action on a post.
    """
    __tablename__ = 'action_view_post'
    __mapper_args__ = {
        'polymorphic_identity': 'view_post'
    }

    id = Column(
        Integer,
        ForeignKey('action.id', ondelete="CASCADE", onupdate='CASCADE'),
        primary_key=True
    )

    verb = 'viewed'


class ExpandPost(ActionOnPost):
    """
    An expansion action on a post.
    """
    __tablename__ = 'action_expand_post'
    __mapper_args__ = {
        'polymorphic_identity': 'expand_post'
    }

    id = Column(
        Integer,
        ForeignKey('action.id', ondelete="CASCADE", onupdate='CASCADE'),
        primary_key=True
    )

    verb = 'expanded'


class CollapsePost(ActionOnPost):
    """
    A collapse action on a post.
    """
    __tablename__ = 'action_collapse_post'
    __mapper_args__ = {
        'polymorphic_identity': 'collapse_post'
    }

    id = Column(
        Integer,
        ForeignKey('action.id', ondelete="CASCADE", onupdate='CASCADE'),
        primary_key=True
    )

    verb = 'collapsed'
