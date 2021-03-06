import re
import quopri
from itertools import groupby, chain
from collections import defaultdict
import traceback

from datetime import datetime
import anyjson as json
from sqlalchemy.orm import relationship, backref, aliased
from sqlalchemy.sql import text
from pyramid.security import Allow, ALL_PERMISSIONS
from sqlalchemy import (
    Column,
    Boolean,
    Integer,
    String,
    Float,
    Unicode,
    UnicodeText,
    DateTime,
    ForeignKey,
    event,
    and_,
)
from sqlalchemy.ext.associationproxy import association_proxy
from virtuoso.vmapping import PatternIriClass

from assembl.lib.utils import slugify
from . import DiscussionBoundBase
from ..lib.virtuoso_mapping import QuadMapPatternS
from .generic import (PostSource, Content)
from .post import (Post, SynthesisPost)
from .mail import IMAPMailbox
from ..auth import (
    CrudPermissions, P_READ, R_SYSADMIN, P_ADMIN_DISC, P_EDIT_IDEA,
    P_EDIT_EXTRACT, P_EDIT_SYNTHESIS, P_ADD_IDEA, P_ADD_EXTRACT,
    P_EDIT_MY_EXTRACT, Authenticated, Everyone)
from .auth import (
    DiscussionPermission, Role, Permission, AgentProfile, User,
    UserRole, LocalUserRole, ViewPost)
from ..namespaces import (
    SIOC, CATALYST, IDEA, ASSEMBL, DCTERMS, OA, QUADNAMES)
from assembl.views.traversal import AbstractCollectionDefinition


class Discussion(DiscussionBoundBase):
    """
    A Discussion
    """
    __tablename__ = "discussion"
    rdf_class = CATALYST.Conversation

    id = Column(Integer, primary_key=True,
                info={'rdf': QuadMapPatternS(None, ASSEMBL.db_id)})

    topic = Column(UnicodeText, nullable=False,
                   info={'rdf': QuadMapPatternS(None, DCTERMS.title)})

    slug = Column(Unicode, nullable=False, unique=True, index=True)

    creation_date = Column(DateTime, nullable=False, default=datetime.utcnow,
                           info={'rdf': QuadMapPatternS(None, DCTERMS.created)})

    def read_post_ids(self, user_id):
        return (x[0] for x in self.db.query(Post.id).join(
            ViewPost
        ).filter(
            Post.discussion_id == self.id,
            ViewPost.actor_id == user_id,
            ViewPost.post_id == Post.id
        ))

    def get_read_posts_ids_preload(self, user_id):
        return json.dumps([
            Post.uri_generic(id) for id in self.read_post_ids(user_id)])

    def import_from_sources(self, only_new=True):
        for source in self.sources:
            # refetch after calling
            source = PostSource.db.merge(source)
            try:
                source.import_content(only_new=only_new)
            except:
                traceback.print_exc()

    def __init__(self, *args, **kwargs):
        super(Discussion, self).__init__(*args, **kwargs)
        self.db.add(self)
        self.db.flush()
        self.root_idea = RootIdea(discussion_id=self.id)
        table_of_contents = TableOfContents(discussion=self)
        synthesis = Synthesis(discussion=self)
        self.db.add(table_of_contents)
        self.db.add(synthesis)

    def serializable(self):
        return {
            "@id": self.uri(),
            "@type": self.external_typename(),
            "topic": self.topic,
            "slug": self.slug,
            "creation_date": self.creation_date.isoformat(),
            "root_idea": self.root_idea.uri()
        }

    def get_discussion_id(self):
        return self.id

    @classmethod
    def get_discussion_condition(cls, discussion_id):
        return cls.id == discussion_id

    def get_next_synthesis(self):
        next_synthesis = self.db().query(Synthesis).filter(
            and_(Synthesis.discussion_id == self.id,
                 Synthesis.published_in_post == None)
        ).all()
        #There should only be a single next synthesis
        assert len(next_synthesis) == 1
        return next_synthesis[0]

    def get_last_published_synthesis(self):
        return self.db().query(Synthesis).filter(
            Synthesis.discussion_id == self.id and
            Synthesis.published_in_post != None
        ).order_by(Synthesis.published_in_post.creation_date.desc()
                   ).first()

    def get_permissions_by_role(self):
        roleperms = self.db().query(Role.name, Permission.name).select_from(
            DiscussionPermission).join(Role, Permission).filter(
                DiscussionPermission.discussion_id == self.id).all()
        roleperms.sort()
        byrole = groupby(roleperms, lambda (r, p): r)
        return {r: [p for (r2, p) in rps] for (r, rps) in byrole}

    def get_roles_by_permission(self):
        permroles = self.db().query(Permission.name, Role.name).select_from(
            DiscussionPermission).join(Role, Permission).filter(
                DiscussionPermission.discussion_id == self.id).all()
        permroles.sort()
        byperm = groupby(permroles, lambda (p, r): p)
        return {p: [r for (p2, r) in prs] for (p, prs) in byperm}

    def get_readers(self):
        session = self.db()
        users = session.query(User).join(
            UserRole, Role, DiscussionPermission, Permission).filter(
                DiscussionPermission.discussion_id == self.id and
                Permission.name == P_READ
            ).union(self.db().query(User).join(
                LocalUserRole, Role, DiscussionPermission, Permission).filter(
                    DiscussionPermission.discussion_id == self.id and
                    LocalUserRole.discussion_id == self.id and
                    Permission.name == P_READ)).all()
        if session.query(DiscussionPermission).join(
            Role, Permission).filter(
                DiscussionPermission.discussion_id == self.id and
                Permission.name == P_READ and
                Role.name == Authenticated).first():
            pass  # add a pseudo-authenticated user???
        if session.query(DiscussionPermission).join(
            Role, Permission).filter(
                DiscussionPermission.discussion_id == self.id and
                Permission.name == P_READ and
                Role.name == Everyone).first():
            pass  # add a pseudo-anonymous user?
        return users

    def get_all_agents_preload(self):
        from assembl.views.api.agent import _get_agents_real
        return json.dumps(_get_agents_real(discussion=self))

    def get_readers_preload(self):
        return json.dumps([user.serializable() for user in self.get_readers()])

    def get_ideas_preload(self):
        from assembl.views.api.idea import _get_ideas_real
        return json.dumps(_get_ideas_real(discussion=self))

    def get_idea_links(self):
        return Idea.get_all_idea_links(self.id)

    def get_idea_and_links(self):
        return chain(self.ideas, self.get_idea_links())

    def get_top_ideas(self):
        return self.db().query(Idea).filter(
            Idea.discussion_id == self.id).filter(
                ~Idea.source_links.any()).all()

    def get_related_extracts_preload(self):
        from assembl.views.api.extract import _get_extracts_real
        return json.dumps(_get_extracts_real(discussion=self))

    def get_user_permissions(self, user_id):
        from ..auth.util import get_permissions
        return get_permissions(user_id, self.id)

    def get_user_permissions_preload(self, user_id):
        return json.dumps(self.get_user_permissions(user_id))

    # Properties as a route context
    __parent__ = None

    @property
    def __name__(self):
        return self.slug

    @property
    def __acl__(self):
        acls = [(Allow, dp.role.name, dp.permission.name) for dp in self.acls]
        acls.append((Allow, R_SYSADMIN, ALL_PERMISSIONS))
        return acls

    def __repr__(self):
        return "<Discussion %s>" % repr(self.topic)


def slugify_topic_if_slug_is_empty(discussion, topic, oldvalue, initiator):
    """
    if the target doesn't have a slug, slugify the topic and use that.
    """
    if not discussion.slug:
        discussion.slug = slugify(topic)


event.listen(Discussion.topic, 'set', slugify_topic_if_slug_is_empty)


class IdeaGraphView(DiscussionBoundBase):
    """
    A view on the graph of idea.
    """
    __tablename__ = "idea_graph_view"
    rdf_class = IDEA.Map

    type = Column(String(60), nullable=False)
    id = Column(Integer, primary_key=True,
                info={'rdf': QuadMapPatternS(None, ASSEMBL.db_id)})

    creation_date = Column(DateTime, nullable=False, default=datetime.utcnow,
        info= {'rdf': QuadMapPatternS(None, DCTERMS.created)})

    discussion_id = Column(
        Integer,
        ForeignKey('discussion.id', ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        info = {'rdf': QuadMapPatternS(None, SIOC.has_container, Discussion.iri_class().apply())}
    )
    discussion = relationship('Discussion', backref="views")

    __mapper_args__ = {
        'polymorphic_identity': 'idea_graph_view',
        'polymorphic_on': 'type',
        'with_polymorphic': '*'
    }

    def copy(self):
        retval = self.__class__()
        retval.discussion = self.discussion
        return retval

    def get_discussion_id(self):
        return self.discussion_id

    @classmethod
    def get_discussion_condition(cls, discussion_id):
        return cls.discussion_id == discussion_id

    crud_permissions = CrudPermissions(P_ADMIN_DISC)


class SubGraphIdeaAssociation(DiscussionBoundBase):
    __tablename__ = 'sub_graph_idea_association'
    id = Column(Integer, primary_key=True)
    sub_graph_id = Column(Integer, ForeignKey(
        'explicit_sub_graph_view.id', ondelete="CASCADE", onupdate="CASCADE"),
        index=True, nullable=False)
    sub_graph = relationship("ExplicitSubGraphView", backref="idea_assocs")
    idea_id = Column(Integer, ForeignKey(
        'idea.id', ondelete="CASCADE", onupdate="CASCADE"), index=True)
    # reference to the "Idea" object for proxying
    idea = relationship("Idea")

    def __init__(self, idea=None, sub_graph=None):
        self.idea = idea
        self.sub_graph = sub_graph

    def get_discussion_id(self):
        if self.sub_graph:
            return self.sub_graph.get_discussion_id()
        else:
            return IdeaGraphView.get(id=self.sub_graph_id).get_discussion_id()

    @classmethod
    def get_discussion_condition(cls, discussion_id):
        from . import ExplicitSubGraphView
        return cls.sub_graph_id == IdeaGraphView.id & \
            IdeaGraphView.discussion_id == discussion_id

    crud_permissions = CrudPermissions(P_ADMIN_DISC)

class SubGraphIdeaLinkAssociation(DiscussionBoundBase):
    __tablename__ = 'sub_graph_idea_link_association'
    id = Column(Integer, primary_key=True)

    sub_graph_id = Column(Integer, ForeignKey(
        'explicit_sub_graph_view.id', ondelete="CASCADE", onupdate="CASCADE"),
        index=True, nullable=False)
    sub_graph = relationship("ExplicitSubGraphView", backref="idealink_assocs")

    idea_link_id = Column(Integer, ForeignKey(
        'idea_idea_link.id', ondelete="CASCADE", onupdate="CASCADE"),
        index=True)

    # reference to the "IdeaLink" object for proxying
    idea_link = relationship("IdeaLink")

    def __init__(self, idea_link=None, sub_graph=None):
        self.idea_link = idea_link
        self.sub_graph = sub_graph

    def get_discussion_id(self):
        if self.sub_graph:
            return self.sub_graph.get_discussion_id()
        else:
            return IdeaGraphView.get(id=self.sub_graph_id).get_discussion_id()

    @classmethod
    def get_discussion_condition(cls, discussion_id):
        from . import ExplicitSubGraphView
        return cls.sub_graph_id == IdeaGraphView.id & \
            IdeaGraphView.discussion_id == discussion_id

    crud_permissions = CrudPermissions(P_ADMIN_DISC)

class ExplicitSubGraphView(IdeaGraphView):
    """
    A view where the Ideas and/or ideaLinks have been explicitly selected.

    Note that ideaLinks may point to ideas that are not in the graph.  They
    should be followed transitively (if their nature is compatible) to reach
    every idea in graph as if they were directly linked.
    """
    __tablename__ = "explicit_sub_graph_view"

    id = Column(Integer, ForeignKey(
        'idea_graph_view.id',
        ondelete='CASCADE',
        onupdate='CASCADE'
    ), primary_key=True)

    ideas_associations = relationship(SubGraphIdeaAssociation,
                                      cascade="all, delete-orphan")

    # proxy the 'idea' attribute from the 'ideas_associations' relationship
    # for direct access
    ideas = association_proxy('ideas_associations', 'idea')

    idea_links_associations = relationship(SubGraphIdeaLinkAssociation,
                                           cascade="all, delete-orphan")

    # proxy the 'idea_link' attribute from the 'idea_links_associations'
    # relationship for direct access
    idea_links = association_proxy('idea_links_associations', 'idea_link')

    __mapper_args__ = {
        'polymorphic_identity': 'explicit_sub_graph_view',
    }

    def copy(self):
        retval = IdeaGraphView.copy(self)
        retval.ideas = self.ideas
        return retval

    @classmethod
    def extra_collections(cls):
        class IdeaCollectionDefinition(AbstractCollectionDefinition):
            def __init__(self, cls):
                super(IdeaCollectionDefinition, self).__init__(cls, Idea)

            def decorate_query(self, query, parent_instance):
                query = query.join(SubGraphIdeaAssociation, self.owner_class)
                return query

            def decorate_instance(self, instance, parent_instance, assocs):
                for inst in assocs[:]:
                    if isinstance(inst, Idea):
                        assocs.append(SubGraphIdeaAssociation(
                            idea=inst, sub_graph=parent_instance))
                    elif isinstance(inst, IdeaLink):
                        assocs.append(SubGraphIdeaLinkAssociation(
                                idea_link=inst, sub_graph=parent_instance))

            def contains(self, parent_instance, instance):
                return SubGraphIdeaAssociation.db.query(
                    SubGraphIdeaAssociation).filter_by(
                        idea=instance,
                        sub_graph=parent_instance
                    ).count() > 0

        class IdeaLinkCollectionDefinition(AbstractCollectionDefinition):
            def __init__(self, cls):
                super(IdeaLinkCollectionDefinition, self).__init__(cls, IdeaLink)

            def decorate_query(self, query, parent_instance):
                return query.join(
                    SubGraphIdeaLinkAssociation, self.owner_class)

            def decorate_instance(self, instance, parent_instance, assocs):
                assocs.append(
                    SubGraphIdeaLinkAssociation(
                        idea_link=instance, sub_graph=parent_instance))

            def contains(self, parent_instance, instance):
                return SubGraphIdeaAssociation.db.query(
                    SubGraphIdeaLinkAssociation).filter_by(
                        idea_link=instance,
                        sub_graph=parent_instance
                    ).count() > 0

        return {'ideas': IdeaCollectionDefinition(cls),
                'idea_links': IdeaLinkCollectionDefinition(cls)}

    crud_permissions = CrudPermissions(P_ADMIN_DISC)

class TableOfContents(IdeaGraphView):
    """
    Represents a Table of Ideas.

    A ToI in Assembl is used to organize the core ideas of a discussion in a
    threaded hierarchy.
    """
    __tablename__ = "table_of_contents"

    id = Column(Integer, ForeignKey(
        'idea_graph_view.id',
        ondelete='CASCADE',
        onupdate='CASCADE'
    ), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'table_of_contents',
    }

    def serializable(self):
        return {
            "@id": self.uri_generic(self.id),
            "@type": self.external_typename(),
            "topic": self.topic,
            "slug": self.slug,
            "table_of_contents_id":
            TableOfContents.uri_generic(self.table_of_contents_id),
            "synthesis_id":
            Synthesis.uri_generic(self.synthesis_id)
        }

    def get_discussion_id(self):
        return self.discussion.id

    @classmethod
    def get_discussion_condition(cls, discussion_id):
        return cls.discussion_id == discussion_id

    def get_idea_links(self):
        return self.discussion.get_idea_links()

    def get_ideas(self):
        return self.discussion.ideas

    def __repr__(self):
        return "<TableOfContents %s>" % repr(self.discussion.topic)


class Synthesis(ExplicitSubGraphView):
    """
    A synthesis of the discussion.  A selection of ideas, associated with
    comments, sent periodically to the discussion.

    A synthesis only has link's to ideas before publication (as it is edited)
    Once published, if freezes the links by copying tombstoned versions of
    each link in the discussion.
    """
    __tablename__ = "synthesis"

    id = Column(Integer, ForeignKey(
        'explicit_sub_graph_view.id',
        ondelete='CASCADE',
        onupdate='CASCADE'
    ), primary_key=True)

    subject = Column(UnicodeText)
    introduction = Column(UnicodeText)
    conclusion = Column(UnicodeText)

    __mapper_args__ = {
        'polymorphic_identity': 'synthesis',
    }

    def copy(self):
        retval = ExplicitSubGraphView.copy(self)
        retval.subject = self.subject
        retval.introduction = self.introduction
        retval.conclusion = self.conclusion
        return retval

    def publish(self):
        """ Publication is the end of a synthesis's lifecycle.
        It creates a new next_synthesis, copied from this one.
        Return's the new discussion next_synthesis """
        next_synthesis = self.copy()
        self.db.add(next_synthesis)

        #Copy tombstoned versions of all idea links in the current discussion
        links = Idea.get_all_idea_links(self.discussion_id)
        for link in links:
            new_link = link.copy()
            new_link.is_tombstone = True
            self.idea_links.append(new_link)
        self.db.add(self)
        return next_synthesis

    @property
    def is_next_synthesis(self):
        return self.discussion.get_next_synthesis() == self;

    def get_discussion_id(self):
        return self.discussion_id

    @classmethod
    def get_discussion_condition(cls, discussion_id):
        return cls.discussion_id == discussion_id

    def __repr__(self):
        return "<Synthesis %s>" % repr(self.subject)

    crud_permissions = CrudPermissions(P_EDIT_SYNTHESIS)


class Idea(DiscussionBoundBase):
    """
    A core concept taken from the associated discussion
    """
    __tablename__ = "idea"
    rdf_class = CATALYST.Idea
    #rdf_class_id = Column(IRI_ID)
    ORPHAN_POSTS_IDEA_ID = 'orphan_posts'
    sqla_type = Column(String(60), nullable=False)

    long_title = Column(
        UnicodeText,
        info= {'rdf': QuadMapPatternS(None, DCTERMS.alternative)})
    short_title = Column(UnicodeText,
        info= {'rdf': QuadMapPatternS(None, DCTERMS.title)})
    definition = Column(UnicodeText,
        info= {'rdf': QuadMapPatternS(None, DCTERMS.description)})
    hidden = Column(Boolean, default=False)

    id = Column(Integer, primary_key=True,
                info= {'rdf': QuadMapPatternS(None, ASSEMBL.db_id)})
    creation_date = Column(
        DateTime, nullable=False, default=datetime.utcnow,
        info = {'rdf': QuadMapPatternS(None, DCTERMS.created)})

    discussion_id = Column(Integer, ForeignKey(
        'discussion.id',
        ondelete='CASCADE',
        onupdate='CASCADE'),
        nullable=False,
        index=True,
        info = {'rdf': QuadMapPatternS(None, SIOC.has_container, Discussion.iri_class().apply())})

    discussion = relationship(
        "Discussion",
        backref=backref('ideas', order_by=creation_date)
    )

    widget_id = Column(Integer, ForeignKey('widget.id'))
    widget = relationship("Widget", backref=backref('ideas', order_by=creation_date))

    __mapper_args__ = {
        'polymorphic_identity': 'idea',
        'polymorphic_on': sqla_type,
        # Not worth it for now, as the only other class is RootIdea, and there
        # is only one per discussion - benoitg 2013-12-23
        #'with_polymorphic': '*'
    }

    # @classmethod
    # def special_quad_patterns(cls, alias_manager):
    #     return [QuadMapPatternS(None, 
    #         RDF.type, IriClass(VirtRDF.iri_id).apply('rdf_class_id')),
    #         name=QUADNAMES.class_Idea_class)]

    @property
    def children(self):
        return [cl.target for cl in self.target_links]

    @property
    def parents(self):
        return [cl.source for cl in self.source_links]

    @property
    def widget_add_post_endpoint(self):
        if self.widget_id:
            # TODO: How to get the widget's root idea? That may vary on a per-widget basis.
            return 'local:Discussion/%d/widgets/%d/main_idea_view/-/ideas/%d/children/%d/widgetposts' % (
                self.discussion_id, self.widget_id, self.parents[0].id, self.id)


    def get_all_ancestors(self):
        """ Get all ancestors of this idea by following source links.  
        This is naive and slow, but not used very much for now.
        TODO:  Rewrite once we migrate to virtuoso"""
        sql = '''SELECT * FROM idea JOIN (
                  SELECT source_id FROM (
                    SELECT transitive t_in (1) t_out (2) t_distinct T_NO_CYCLES
                        source_id, target_id FROM idea_idea_link WHERE is_tombstone=0) ia
                  JOIN idea AS dag_idea ON (ia.source_id = dag_idea.id)
                  WHERE dag_idea.discussion_id = :discussion_id
                  AND ia.target_id=:idea_id) x on (id=source_id)'''
        ancestors = self.db().query(Idea).from_statement(text(sql).bindparams(
            discussion_id= self.discussion_id, idea_id= self.id))

        return ancestors.all()
    
    def get_order_from_first_parent(self):
        return self.source_links[0].order if self.source_links else None

    def get_first_parent_uri(self):
        return Idea.uri_generic(
            self.source_links[0].source_id
        ) if self.source_links else None

    @staticmethod
    def _get_idea_dag_statement(skip_where=False):
        """requires root_idea_id and discussion_id parameters"""
        if skip_where:
            where_clause = \
                '''(SELECT root_idea.id FROM root_idea
                    JOIN idea ON (idea.id = root_idea.id)
                    WHERE idea.discussion_id=:discussion_id)'''
        else:
            where_clause = ':root_idea_id'
        return """(SELECT source_id, target_id FROM (
            SELECT transitive t_in (1) t_out (2) t_distinct T_NO_CYCLES
                        source_id, target_id FROM idea_idea_link WHERE is_tombstone=0
                UNION SELECT id as source_id, id as target_id FROM idea
            ) ia
            JOIN idea AS dag_idea ON (ia.source_id = dag_idea.id)
            WHERE dag_idea.discussion_id = :discussion_id 
                AND ia.source_id = %s)
            AS idea_dag""" % (where_clause,)

    @staticmethod
    def _get_related_posts_statement_no_select(select, skip_where):
        return """%s FROM %s
JOIN idea_content_link ON (idea_content_link.idea_id = idea_dag.target_id)
JOIN idea_content_positive_link
    ON (idea_content_positive_link.id = idea_content_link.id)
JOIN post AS root_posts ON (idea_content_link.content_id = root_posts.id)
JOIN post ON (
    (post.ancestry <> ''
    AND post.ancestry LIKE root_posts.ancestry || cast(root_posts.id as varchar) || ',' || '%%'
    )
    OR post.id = root_posts.id
)
""" % (select, Idea._get_idea_dag_statement(skip_where))

    @staticmethod
    def _get_related_posts_statement(skip_where=False):
        return Idea._get_related_posts_statement_no_select(
            "SELECT DISTINCT post.id as post_id", skip_where)

    @staticmethod
    def _get_count_related_posts_statement():
        return Idea._get_related_posts_statement_no_select(
            "SELECT COUNT(DISTINCT post.id) as total_count", False)

    @staticmethod
    def _get_orphan_posts_statement_no_select(select):
        """ Requires discussion_id bind parameters """
        return select + """
FROM post
JOIN content ON (
    content.id = post.id
    AND content.discussion_id = :discussion_id
)
EXCEPT corresponding BY (post_id)
""" + Idea._get_related_posts_statement(True)

    @staticmethod
    def _get_count_orphan_posts_statement():
        """ Requires discussion_id bind parameters """
        return "SELECT COUNT(post_id) as total_count from (%s) orphans" % (
            Idea._get_orphan_posts_statement())

    @staticmethod
    def _get_orphan_posts_statement():
        """ Requires discussion_id bind parameters """
        return Idea._get_orphan_posts_statement_no_select("SELECT post.id as post_id")

    @property
    def num_posts(self):
        """ This is extremely naive and slow, but as this is all temp code
        until we move to a graph database, it will probably do for now """
        result = self.db.execute(text(
            Idea._get_count_related_posts_statement()),
            {"root_idea_id": self.id, "discussion_id": self.discussion_id})
        return int(result.first()['total_count'])

    @property
    def num_read_posts(self):
        """ Worse than above... but temporary """
        connection = self.db().connection()
        user_id = connection.info.get('userid', None)
        if not user_id:
            return 0
        join = """JOIN action ON (action.post_id = post.id)
                  JOIN action_view_post ON (action.id = action_view_post.id)
                  WHERE action.actor_id = :user_id"""

        result = self.db.execute(text(
            Idea._get_count_related_posts_statement() + join),
            {"root_idea_id": self.id, "user_id": user_id,
             "discussion_id": self.discussion_id})
        return int(result.first()['total_count'])

    def get_discussion_id(self):
        return self.discussion_id

    @classmethod
    def get_discussion_condition(cls, discussion_id):
        return cls.discussion_id == discussion_id

    def get_num_children(self):
        return len(self.children)

    def is_in_next_synthesis(self):
        next_synthesis = self.discussion.get_next_synthesis()
        return True if self in next_synthesis.ideas else False

    def __repr__(self):
        if self.short_title:
            return "<Idea %d %s>" % (self.id or -1, repr(self.short_title))

        return "<Idea %d>" % (self.id or -1,)

    @classmethod
    def invalidate_ideas(cls, discussion_id, post_id):
        raise NotImplemented()

    @classmethod
    def idea_counts(cls, discussion_id, post_id, user_id):
        "Given a post and a user, give the total and read count of posts for each affected idea"
        stmt1 = """SELECT idea.id, root_post.id FROM idea 
            JOIN idea_content_link ON (idea_content_link.idea_id = idea.id)
            JOIN idea_content_positive_link
                ON (idea_content_positive_link.id = idea_content_link.id)
            JOIN post AS root_post ON (idea_content_link.content_id = root_post.id)
            WHERE root_post.id = :post_id OR root_post.id IN
            (SELECT parent_id, id FROM (
                    SELECT transitive t_in (1) t_out (2) T_DISTINCT T_NO_CYCLES
                        parent_id, id FROM post
                    UNION SELECT id AS parent_id, id FROM POST
                    ) pa 
                JOIN content USING (id) WHERE id = :post_id AND content.discussion_id = :discussion_id)"""
        roots = defaultdict(list)
        for idea_id, post_id in cls.db().execute(text(stmt1).params(
            {'post_id': post_id,
             "discussion_id": discussion_id})):
            roots[idea_id].append(post_id)
        result = []
        common_params = dict(discussion_id=discussion_id, user_id=user_id)
        for idea_id, post_ids in roots.iteritems():
            stmt2 = ' UNION '.join(["""
                SELECT  pa.id as post_id, action_view_post.id as view_id FROM (
                    SELECT transitive t_in (1) t_out (2) T_DISTINCT T_NO_CYCLES
                        parent_id, id FROM post
                    UNION SELECT id AS parent_id, id FROM POST
                    ) pa 
                JOIN content USING (id) 
                LEFT JOIN action ON (action.post_id = pa.id
                                     AND action.actor_id = :user_id)
                LEFT JOIN action_view_post ON (action.id = action_view_post.id)
                WHERE parent_id = :post_id_%d AND content.discussion_id= :discussion_id
                """ % n for n in range(len(post_ids))])
            stmt2 = "SELECT COUNT(x.post_id), COUNT(x.view_id) FROM (%s) x" % (stmt2,)
            params = {'post_id_'+str(n): post_id for n, post_id in enumerate(post_ids)}
            params.update(common_params)
            cpost, cview = list(cls.db().execute(text(stmt2).params(params))).pop()
            result.append((idea_id, cpost, cview))
        stmt3 = """SELECT MIN(root_idea.id) as idea_id,
            COUNT(DISTINCT post.id) as total_count,
            COUNT(DISTINCT action_view_post.id) as read_count
            FROM root_idea
            JOIN idea ON (idea.id = root_idea.id)
            CROSS JOIN post
            JOIN content ON (post.id = content.id)
            LEFT JOIN action ON (action.post_id = post.id AND action.actor_id = :user_id)
            LEFT JOIN action_view_post ON (action.id = action_view_post.id)
            WHERE idea.discussion_id = :discussion_id
            AND content.discussion_id = :discussion_id"""
        result.append(list(cls.db().execute(text(stmt3).params(common_params))).pop())
        return result

    @classmethod
    def get_all_idea_links(cls, discussion_id):
        target = aliased(cls)
        source = aliased(cls)
        return cls.db().query(
            IdeaLink).join(
                source, source.id == IdeaLink.source_id).join(
                    target, target.id == IdeaLink.target_id).filter(
                        target.discussion_id == discussion_id).filter(
                            source.discussion_id == discussion_id).filter(
                                IdeaLink.is_tombstone == False).all()

    @classmethod
    def extra_collections(cls):
        class ChildIdeaCollectionDefinition(AbstractCollectionDefinition):
            def __init__(self, cls):
                super(ChildIdeaCollectionDefinition, self).__init__(cls, Idea)

            def decorate_query(self, query, parent_instance):
                return query.join(IdeaLink,
                    IdeaLink.source_id == parent_instance.id)

            def decorate_instance(self, instance, parent_instance, assocs):
                assocs.append(IdeaLink(
                        source=parent_instance, target=instance))

            def contains(self, parent_instance, instance):
                return IdeaLink.db.query(
                    IdeaLink).filter_by(
                        source=parent_instance, target=instance
                    ).count() > 0

        class LinkedPostCollectionDefinition(AbstractCollectionDefinition):
            def __init__(self, cls):
                super(LinkedPostCollectionDefinition, self).__init__(cls, Content)

            def decorate_query(self, query, parent_instance):
                return query.join(
                    IdeaRelatedPostLink, self.owner_class)

            def decorate_instance(self, instance, parent_instance, assocs):
                # This is going to spell trouble: Sometimes we'll have creator,
                # other times creator_id
                assocs.append(
                    IdeaRelatedPostLink(
                        content=instance, idea=parent_instance,
                        creator_id=instance.creator_id))

            def contains(self, parent_instance, instance):
                return IdeaRelatedPostLink.db.query(
                    IdeaRelatedPostLink).filter_by(
                        content=instance, idea=parent_instance
                    ).count() > 0

        class WidgetPostCollectionDefinition(AbstractCollectionDefinition):
            def __init__(self, cls):
                super(WidgetPostCollectionDefinition, self).__init__(cls, Content)

            def decorate_query(self, query, parent_instance):
                return query.join(
                    IdeaContentWidgetLink, self.owner_class)

            def decorate_instance(self, instance, parent_instance, assocs):
                # This is going to spell trouble: Sometimes we'll have creator,
                # other times creator_id
                assocs.append(
                    IdeaContentWidgetLink(
                        content=instance, idea=parent_instance,
                        creator_id=instance.creator_id))
                instance.hidden = True

            def contains(self, parent_instance, instance):
                return IdeaContentWidgetLink.db.query(
                    IdeaContentWidgetLink).filter_by(
                        content=instance, idea=parent_instance
                    ).count() > 0

        return {'children': ChildIdeaCollectionDefinition(cls),
                'linkedposts': LinkedPostCollectionDefinition(cls),
                'widgetposts': WidgetPostCollectionDefinition(cls)}

    crud_permissions = CrudPermissions(
            P_ADD_IDEA, P_READ, P_EDIT_IDEA, P_ADMIN_DISC,
            P_ADMIN_DISC, P_ADMIN_DISC)

class RootIdea(Idea):
    """
    The root idea.  It represents the discussion.

    If has implicit links to all content and posts in the discussion.
    """
    __tablename__ = "root_idea"

    id = Column(Integer, ForeignKey(
        'idea.id',
        ondelete='CASCADE',
        onupdate='CASCADE'
    ), primary_key=True)

    root_for_discussion = relationship(
        'Discussion',
        backref=backref('root_idea', uselist=False),
    )

    __mapper_args__ = {
        'polymorphic_identity': 'root_idea',
    }

    @property
    def num_posts(self):
        """ In the root idea, this is the count of all mesages in the system """
        result = self.db.query(Post).filter(
            Post.discussion_id == self.discussion_id
        ).count()
        return int(result)

    @property
    def num_orphan_posts(self):
        "The number of posts unrelated to any idea in the current discussion"
        result = self.db.execute(text(
            Idea._get_count_orphan_posts_statement()).params(
                discussion_id=self.discussion_id))
        return int(result.first()['total_count'])
    
    @property
    def num_synthesis_posts(self):
        """ In the root idea, this is the count of all mesages in the system """
        result = self.db.query(SynthesisPost).filter(
            Post.discussion_id == self.discussion_id
        ).count()
        return int(result)

    def discussion_topic(self):
        return self.discussion.topic

    crud_permissions = CrudPermissions(P_ADMIN_DISC)


class IdeaLink(DiscussionBoundBase):
    """
    A generic link between two ideas

    If a parent-child relation, the parent is the source, the child the target
    """
    __tablename__ = 'idea_idea_link'
    rdf_class = IDEA.DirectedIdeaRelation
    id = Column(Integer, primary_key=True,
                info= {'rdf': QuadMapPatternS(None, ASSEMBL.db_id)})
    source_id = Column(Integer, ForeignKey(
            'idea.id', ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False, index=True,
        info= {'rdf': QuadMapPatternS(None, IDEA.source_idea, Idea.iri_class().apply())})
    target_id = Column(Integer, ForeignKey(
        'idea.id', ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False, index=True,
        info= {'rdf': QuadMapPatternS(None, IDEA.destination_idea, Idea.iri_class().apply())})
    source = relationship(
        'Idea', 
        primaryjoin="and_(Idea.id==IdeaLink.source_id, "
                        "IdeaLink.is_tombstone==False)",
        backref=backref('target_links', cascade="all, delete-orphan"),
        foreign_keys=(source_id))
    target = relationship(
        'Idea',
        primaryjoin="and_(Idea.id==IdeaLink.target_id, "
                        "IdeaLink.is_tombstone==False)",
        backref=backref('source_links', cascade="all, delete-orphan"),
        foreign_keys=(target_id))
    order = Column(Float, nullable=False, default=0.0,
        info= {'rdf': QuadMapPatternS(None, ASSEMBL.link_order)})
    is_tombstone = Column(Boolean, nullable=False, default=False, index=True)

    @classmethod
    def special_quad_patterns(cls, alias_manager):
        return [QuadMapPatternS(
            Idea.iri_class().apply(cls.source_id),
            IDEA.InclusionRelation,
            Idea.iri_class().apply(cls.target_id),
            name=QUADNAMES.idea_inclusion_reln)]

    def copy(self):
        retval = self.__class__(source_id=self.source_id,
                                target_id=self.target_id,
                                is_tombstone=self.is_tombstone
                                )
        self.db.add(retval)
        return retval

    def get_discussion_id(self):
        if self.source:
            return self.source.get_discussion_id()
        else:
            return Idea.get(id=self.source_id).get_discussion_id()

    @classmethod
    def get_discussion_condition(cls, discussion_id):
        return cls.source_id == Idea.id & Idea.discussion_id == discussion_id

    crud_permissions = CrudPermissions(
            P_ADD_IDEA, P_READ, P_EDIT_IDEA, P_EDIT_IDEA,
            P_EDIT_IDEA, P_EDIT_IDEA)

class IdeaContentLink(DiscussionBoundBase):
    """
    Abstract class representing a generic link between an idea and a Content
    (typically a Post)
    """
    __tablename__ = 'idea_content_link'
    # TODO: How to express the implied link as RDF? Remember not reified, unless extract.

    id = Column(Integer, primary_key=True,
                info= {'rdf': QuadMapPatternS(None, ASSEMBL.db_id)})
    type = Column(String(60))

    # This is nullable, because in the case of extracts, the idea can be
    # attached later.
    idea_id = Column(Integer, ForeignKey('idea.id'),
                     nullable=True, index=True)
    idea = relationship('Idea', active_history=True)

    content_id = Column(Integer, ForeignKey(
        'content.id', ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False, index=True)
    content = relationship(Content)

    order = Column(Float, nullable=False, default=0.0)

    creation_date = Column(DateTime, nullable=False, default=datetime.utcnow,
        info= {'rdf': QuadMapPatternS(None, DCTERMS.created)})

    creator_id = Column(
        Integer,
        ForeignKey('agent_profile.id'),
        nullable=False,
    )

    creator = relationship(
        'AgentProfile', foreign_keys=[creator_id], backref='extracts_created')

    __mapper_args__ = {
        'polymorphic_identity': 'idea_content_link',
        'polymorphic_on': type,
        'with_polymorphic': '*'
    }

    def get_discussion_id(self):
        if self.idea:
            return self.idea.get_discussion_id()
        elif self.idea_id:
            return Idea.get(id=self.idea_id).get_discussion_id()

    @classmethod
    def get_discussion_condition(cls, discussion_id):
        return cls.idea_id == Idea.id & Idea.discussion_id == discussion_id

    crud_permissions = CrudPermissions(
            P_ADD_IDEA, P_READ, P_EDIT_IDEA, P_EDIT_IDEA,
            P_EDIT_IDEA, P_EDIT_IDEA)

@event.listens_for(IdeaContentLink.idea, 'set', propagate=True, active_history=True)
def idea_content_link_idea_set_listener(target, value, oldvalue, initiator):
    print "idea_content_link_idea_set_listener for target: %s set to %s, was %s" % (target, value, oldvalue)
    if oldvalue is not None:
        oldvalue.send_to_changes()
        for ancestor in oldvalue.get_all_ancestors():
            ancestor.send_to_changes()
    if value is not None:
        value.send_to_changes()
        for ancestor in value.get_all_ancestors():
            ancestor.send_to_changes()


class IdeaContentWidgetLink(IdeaContentLink):
    """
    A link between an idea and a Content limited to a widget view.
    Such links should not be traversed.
    """
    __tablename__ = 'idea_content_widget_link'

    id = Column(Integer, ForeignKey(
        'idea_content_link.id',
        ondelete='CASCADE', onupdate='CASCADE'
    ), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'idea_content_widget_link',
    }


class IdeaContentPositiveLink(IdeaContentLink):
    """
    A normal link between an idea and a Content.
    Such links should be traversed.
    """
    __tablename__ = 'idea_content_positive_link'

    id = Column(Integer, ForeignKey(
        'idea_content_link.id',
        ondelete='CASCADE', onupdate='CASCADE'
    ), primary_key=True)

    @classmethod
    def special_quad_patterns(cls, alias_manager):
        return [QuadMapPatternS(
            Content.iri_class().apply(IdeaContentLink.content_id),
            ASSEMBL.postLinkedToIdea,
            Idea.iri_class().apply(IdeaContentLink.idea_id),
            name=QUADNAMES.assembl_postLinkedToIdea)]

    __mapper_args__ = {
        'polymorphic_identity': 'idea_content_positive_link',
    }


class IdeaRelatedPostLink(IdeaContentPositiveLink):
    """
    A post that is relevant, as a whole, to an idea, without having a specific
    extract harvested.
    """
    __tablename__ = 'idea_related_post_link'

    id = Column(Integer, ForeignKey(
        'idea_content_positive_link.id',
        ondelete='CASCADE', onupdate='CASCADE'
    ), primary_key=True)

    @classmethod
    def special_quad_patterns(cls, alias_manager):
        return [QuadMapPatternS(
            Content.iri_class().apply(IdeaContentLink.content_id),
            ASSEMBL.postRelatedToIdea,
            Idea.iri_class().apply(IdeaContentLink.idea_id),
            name=QUADNAMES.assembl_postRelatedToIdea)]

    __mapper_args__ = {
        'polymorphic_identity': 'idea_related_post_link',
    }


class Extract(IdeaContentPositiveLink):
    """
    An extracted part of a Content. A quotation to be referenced by an `Idea`.
    """
    __tablename__ = 'extract'
    rdf_class = CATALYST.Excerpt

    id = Column(Integer, ForeignKey(
            'idea_content_positive_link.id',
            ondelete='CASCADE', onupdate='CASCADE'
        ), primary_key=True, info= {
            'rdf': QuadMapPatternS(None, ASSEMBL.db_id)})

    body = Column(UnicodeText, nullable=False)

    discussion_id = Column(Integer, ForeignKey(
        'discussion.id', ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False, index=True,
        info = {'rdf': QuadMapPatternS(None, CATALYST.relevantToConversation,
            Discussion.iri_class().apply())})
    discussion = relationship('Discussion', backref='extracts')

    @classmethod
    def extra_iri_classes(cls):
        return {
            "graph": PatternIriClass(
                ASSEMBL.extract_graph_iri,
                'http://%{WSHostName}U/data/extract_graph/%d',
                ('id', Integer, False))
        }

    @classmethod
    def special_quad_patterns0(cls, alias_manager):
        graph_iri = cls.extra_iri_classes()["graph"]
        relextract_alias = alias_manager.add_class_alias(cls)
        relideacontentlink = alias_manager.add_class_alias(IdeaContentLink, [
            IdeaContentLink.idea_id != None, IdeaContentLink.id == relextract_alias.id])
        return [
            QuadMapPatternS(cls.iri_class().apply(relextract_alias.id),
                CATALYST.expressesIdea,
                Idea.iri_class().apply(relideacontentlink.idea_id),
                name=QUADNAMES.catalyst_expressesIdea),
            QuadMapPatternS(
                cls.iri_class().apply(cls.id),
                OA.hasBody,
                graph_iri.apply(cls.id),
                name=QUADNAMES.oa_hasBody),
            QuadMapPatternS(
                Content.iri_class().apply(relideacontentlink.content_id),
                ASSEMBL.postExtractRelatedToIdea,
                Idea.iri_class().apply(relideacontentlink.idea_id),
                graph=graph_iri.apply(cls.id),
                name=QUADNAMES.assembl_postExtractRelatedToIdea)
            ]


    annotation_text = Column(UnicodeText)

    owner_id = Column(
        Integer,
        ForeignKey('agent_profile.id'),
        nullable=False,
    )

    owner = relationship(
        'AgentProfile', foreign_keys=[owner_id], backref='extracts_owned')

    extract_source = relationship(Content, backref="extracts")
    extract_ideas = relationship(Idea, backref="extracts")

    __mapper_args__ = {
        'polymorphic_identity': 'extract',
    }
    @property
    def target(self):
        retval = {
                '@type': self.content.external_typename()
                }
        if isinstance(self.content, Post):
            retval['@id'] = Post.uri_generic(self.content.id)
        elif self.content.type == 'webpage':
            retval['url'] = self.content.url
        return retval

    def serializable(self):
        json = {
            '@id': self.uri_generic(self.id),
            '@type': self.external_typename(),
            'annotator_schema_version': 'v1.0',
            'quote': self.body,
            'ranges': [tfi.__json__() for tfi
                       in self.text_fragment_identifiers],
            'target': self.target,
            'created': self.creation_date.isoformat(),
            'idCreator': AgentProfile.uri_generic(self.creator_id),
            #'user': self.creator.get_uri(),
            'text': self.annotation_text,
        }
        if self.idea_id:
            json['idIdea'] = Idea.uri_generic(self.idea_id)
            #json['text'] += '<a href="%s">%s</a>' % (
            #   self.idea.get_uri(), self.idea.short_title)
        if isinstance(self.content, Post):
            json['idPost'] = Post.uri_generic(self.content.id)  # legacy
            #json['url'] = self.post.get_uri()
        elif self.content.type == 'webpage':
            json['uri'] = self.content.url
        return json

    def __repr__(self):
        return "<Extract %d %s>" % (self.id or -1, repr(self.body[:20]))

    def get_target(self):
        return self.content

    def get_post(self):
        if isinstance(self.content, Post):
            return self.content

    def infer_text_fragment(self):
        return self._infer_text_fragment_inner(
            self.content.get_title(), self.content.get_body(),
            self.get_post().id)

    def _infer_text_fragment_inner(self, title, body, post_id):
        body = IMAPMailbox.sanitize_html(body, [])
        quote = self.body.replace("\r", "")
        try:
            # for historical reasons
            quote = quopri.decodestring(quote)
        except:
            pass
        quote = IMAPMailbox.sanitize_html(quote, [])
        if quote != self.body:
            self.body = quote
        quote = quote.replace("\n", "")
        start = body.find(quote)
        lookin = 'message-body'
        if start < 0:
            xpath = "//div[@id='%s']/div[class='post_title']" % (post_id)
            start = title.find(quote)
            if start < 0:
                return None
            lookin = 'message-subject'
        xpath = "//div[@id='message-%s']//div[@class='%s']" % (
            Post.uri_generic(post_id), lookin)
        tfi = self.db.query(TextFragmentIdentifier).filter_by(
            extract=self).first()
        if not tfi:
            tfi = TextFragmentIdentifier(extract=self)
        tfi.xpath_start = tfi.xpath_end = xpath
        tfi.offset_start = start
        tfi.offset_end = start+len(quote)
        return tfi

    def get_discussion_id(self):
        return self.discussion_id

    @classmethod
    def get_discussion_condition(cls, discussion_id):
        return cls.discussion_id == discussion_id

    crud_permissions = CrudPermissions(
            P_ADD_EXTRACT, P_READ, P_EDIT_EXTRACT, P_EDIT_EXTRACT,
            P_EDIT_MY_EXTRACT, P_EDIT_MY_EXTRACT)

class IdeaContentNegativeLink(IdeaContentLink):
    """
    A negative link between an idea and a Content.  Such links mean that
    a transitive context should be considered broken.  Used for thread breaking
    """
    __tablename__ = 'idea_content_negative_link'

    id = Column(Integer, ForeignKey(
        'idea_content_link.id',
        ondelete='CASCADE', onupdate='CASCADE'
    ), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'idea_content_negative_link',
    }


class IdeaThreadContextBreakLink(IdeaContentNegativeLink):
    """
    Used for a Post the inherits an Idea from an ancester in the thread.
    It indicates that from this point on in the thread, this idea is no longer
    discussed.
    """
    __tablename__ = 'idea_thread_context_break_link'

    id = Column(Integer, ForeignKey(
        'idea_content_negative_link.id',
        ondelete='CASCADE', onupdate='CASCADE'
    ), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'idea_thread_context_break_link',
    }


class TextFragmentIdentifier(DiscussionBoundBase):
    __tablename__ = 'text_fragment_identifier'
    rdf_class = CATALYST.ExcerptTarget

    id = Column(Integer, primary_key=True,
                info= {'rdf': QuadMapPatternS(None, ASSEMBL.db_id)})
    extract_id = Column(Integer, ForeignKey(
        Extract.id, ondelete="CASCADE"), index=True)
    xpath_start = Column(String)
    offset_start = Column(Integer)
    xpath_end = Column(String)
    offset_end = Column(Integer)
    extract = relationship(Extract, backref='text_fragment_identifiers')

    @classmethod
    def special_quad_patterns(cls, alias_manager):
        return [
            QuadMapPatternS(
                Extract.iri_class().apply(cls.extract_id),
                OA.hasTarget,
                cls.iri_class().apply(cls.id),
                name=QUADNAMES.oa_hasTarget),
            # TODO: Paths!
            # QuadMapPatternS(OA.hasSource,
            #     Extract.iri_class().apply((cls.extract_id, Extract.content_id)),
            #     name=QUADNAMES.catalyst_expressesIdea),
            ]

    xpath_re = re.compile(
        r'xpointer\(start-point\(string-range\(([^,]+),([^,]+),([^,]+)\)\)'
        r'/range-to\(string-range\(([^,]+),([^,]+),([^,]+)\)\)\)')

    def __string__(self):
        return ("xpointer(start-point(string-range(%s,'',%d))/"
                "range-to(string-range(%s,'',%d)))" % (
                self.xpath_start, self.offset_start,
                self.xpath_end, self.offset_end))

    def __json__(self):
        return {"start": self.xpath_start, "startOffset": self.offset_start,
                "end": self.xpath_end, "endOffset": self.offset_end}

    @classmethod
    def from_xpointer(cls, extract_id, xpointer):
        m = cls.xpath_re.match(xpointer)
        if m:
            try:
                (xpath_start, start_text, offset_start,
                    xpath_end, end_text, offset_end) = m.groups()
                offset_start = int(offset_start)
                offset_end = int(offset_end)
                xpath_start = xpath_start.strip()
                assert xpath_start[0] in "\"'"
                xpath_start = xpath_start.strip(xpath_start[0])
                xpath_end = xpath_end.strip()
                assert xpath_end[0] in "\"'"
                xpath_end = xpath_end.strip(xpath_end[0])
                return TextFragmentIdentifier(
                    extract_id=extract_id,
                    xpath_start=xpath_start, offset_start=offset_start,
                    xpath_end=xpath_end, offset_end=offset_end)
            except:
                pass
        return None

    def get_discussion_id(self):
        if self.extract:
            return self.extract.get_discussion_id()
        elif self.extract_id:
            return Extract.get(id=self.extract_id).get_discussion_id()

    @classmethod
    def get_discussion_condition(cls, discussion_id):
        return cls.extract_id == IdeaContentLink.id & \
            IdeaContentLink.idea_id == Idea.id & \
            Idea.discussion_id == discussion_id

    crud_permissions = CrudPermissions(
            P_ADD_EXTRACT, P_READ, P_EDIT_EXTRACT, P_EDIT_EXTRACT,
            P_EDIT_MY_EXTRACT, P_EDIT_MY_EXTRACT)
