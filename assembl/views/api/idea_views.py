import json
import transaction

from cornice import Service
from pyramid.httpexceptions import HTTPNotFound, HTTPBadRequest, HTTPNoContent
from assembl.views.api import API_DISCUSSION_PREFIX
from assembl.models import (
    get_named_object, get_database_id, Idea, RootIdea, IdeaLink, Discussion,
    Extract, SubGraphIdeaAssociation, IdeaGraphView, ExplicitSubGraphView,
    TableOfContents, SubGraphIdeaLinkAssociation, Synthesis)
from . import acls
from assembl.auth import (P_READ, P_ADD_IDEA, P_EDIT_IDEA, P_EDIT_SYNTHESIS)
from sqlalchemy import and_
from sqlalchemy.orm import joinedload


ideaviews = Service(
    name='ideas_views', path=API_DISCUSSION_PREFIX + '/ideaviews',
    description="Get IDs of all idea views", renderer='json', acl=acls)

ideaview = Service(
    name='ideas_view', path=API_DISCUSSION_PREFIX + '/ideaviews/{id:.+}',
    description="Get ideas from a single idea view", acl=acls)

ideasets = Service(
    name='ideas_sets', path=API_DISCUSSION_PREFIX + '/ideasets',
    description="", renderer='json', acl=acls)

ideaset = Service(
    name='ideas_view', path=API_DISCUSSION_PREFIX + '/ideasets/{id:.+}',
    description="Get ideas from a single idea set", acl=acls)

ideaset_idea_link = Service(
    name='ideaset_idea_link',
    path=API_DISCUSSION_PREFIX + '/ideasetidealink/{id:.+}',
    description="A link between an idea set and an idea", acl=acls)

ideaset_idealink_link = Service(
    name='ideaset_idealink_link',
    path=API_DISCUSSION_PREFIX + '/ideasetidealinklink/{id:.+}',
    description="A link between an idea set and an idealink", acl=acls)


@ideaviews.get(permission=P_READ)
def get_ideaviews(request):
    discussion_id = request.matchdict['discussion_id']
    ideaviews = IdeaGraphView.db.query(
        IdeaGraphView).filter_by(
            discussion_id=discussion_id).all()
    view_def = request.GET.get('view')

    if view_def:
        return [ideaview.generic_json(view_def) for ideaview in ideaviews]
    else:
        return [ideaview.uri() for ideaview in ideaviews]


@ideaview.get(permission=P_READ)
def get_ideaview(request):
    discussion_id = request.matchdict['discussion_id']
    ideaview_id = request.matchdict['id']
    # special case named views
    if ideaview_id == 'toi':
        ideaview = TableOfContents.db.query(TableOfContents).filter_by(
            discussion_id=discussion_id).first()
    else:
        ideaview = IdeaGraphView.get_instance(ideaview_id)
    view_def = request.GET.get('view')

    if not ideaview:
        raise HTTPNotFound(
            "IdeaGraphView with id '%s' not found." % ideaview_id)

    if not ideaview.discussion_id == int(discussion_id):
        raise HTTPBadRequest("Ideaview and discussion do not match.")

    if view_def:
        return ideaview.generic_json(view_def)
    else:
        return ideaview.generic_json()


@ideaset.get(permission=P_READ)
def get_ideaset(request):
    discussion_id = request.matchdict['discussion_id']
    ideaset_id = request.matchdict['id']
    ideaset = ExplicitSubGraphView.get_instance(ideaset_id)
    view_def = request.GET.get('view')

    if not ideaset:
        raise HTTPNotFound(
            "ExplicitSubGraphView with id '%s' not found." % ideaset_id)

    if not ideaset.discussion_id == int(discussion_id):
        raise HTTPBadRequest("Ideaset and discussion do not match.")

    if view_def:
        return ideaset.generic_json(view_def)
    else:
        return ideaset.generic_json()


@ideasets.post(permission=P_EDIT_SYNTHESIS)  # We need a new permission.
def new_ideaset(request):
    pass


def delete_ideaview(request):
    pass

# this function is used in two deleters
ideaview.delete(permission=P_EDIT_SYNTHESIS)(delete_ideaview)
ideaset.delete(permission=P_EDIT_SYNTHESIS)(delete_ideaview)


@ideaset.post(permission=P_EDIT_SYNTHESIS)  # We need a new permission.
def new_ideaset_link(request):
    # this can create a SubGraphIdeaAssociation or SubGraphIdeaLinkAssociation.
    pass


@ideaset_idea_link.delete(permission=P_EDIT_SYNTHESIS)
def del_ideaset_idea_link(request):
    pass


@ideaset_idealink_link.delete(permission=P_EDIT_SYNTHESIS)
def del_ideaset_idealink_link(request):
    pass


@ideasets.get(permission=P_READ)
def get_ideasets(request):
    discussion_id = request.matchdict['discussion_id']
    ideasets = ExplicitSubGraphView.db.query(
        IdeaGraphView).filter_by(
            discussion_id=discussion_id).join(
                SubGraphIdeaAssociation).all()
    view_def = request.GET.get('view')

    if view_def:
        return [ideaset.generic_json(view_def) for ideaset in ideasets]
    else:
        return [ideaset.uri() for ideaset in ideasets]
