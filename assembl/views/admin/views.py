from itertools import groupby
from collections import defaultdict

import transaction

from pyramid.view import view_config
from pyramid.renderers import render_to_response
from pyramid.security import authenticated_userid
from pyramid.httpexceptions import HTTPFound

from assembl.models import (
    Discussion, DiscussionPermission, Role, Permission, UserRole,
    LocalUserRole)
from assembl.views.home.views import get_default_context
from assembl.source.models.mail import Mailbox, MailingList
from assembl.auth.models import (
    create_default_permissions, User, Username, AgentProfile, P_ADMIN_DISC, P_SYSADMIN, R_SYSADMIN,
    SYSTEM_ROLES)


@view_config(route_name='discussion_admin', permission="P_SYSADMIN")
def discussion_admin(request):
    user_id = authenticated_userid(request)

    if not user_id:
        return HTTPFound('/login?next_view=/admin/discussions/')

    session = User.db
    user = session.query(User).filter_by(id=user_id).one()

    context = get_default_context()
    context['discussions'] = session.query(Discussion)

    if request.method == 'POST':

        g = lambda x: request.POST.get(x, None)

        (topic, slug, name, host, port,
            ssl, folder, password, username) = (
                g('topic'),
                g('slug'),
                g('mbox_name'),
                g('host'),
                g('port'),
                True if g('ssl') == 'on' else False,
                g('folder'),
                g('password'),
                g('username'),
            )

        discussion = Discussion(
            topic=topic,
            slug=slug
        )

        session.add(discussion)

        create_default_permissions(session, discussion)
        mailbox_class = MailingList if g('mailing_list_address') else Mailbox
        mailbox = mailbox_class(
            name=name,
            host=host,
            port=int(port),
            username=username,
            use_ssl=ssl,
            folder=folder,
            password=password,
        )

        if(g('mailing_list_address')):
            mailbox.post_email_address = g('mailing_list_address')
        mailbox.discussion = discussion
        transaction.commit()

    return render_to_response(
        'admin/discussions.jinja2',
        context,
        request=request)


@view_config(route_name='discussion_permissions', permission="P_ADMIN_DISC")
def discussion_permissions(request):
    user_id = authenticated_userid(request)
    db = Discussion.db()
    discussion_id = int(request.matchdict['discussion_id'])
    discussion = Discussion.get_instance(discussion_id)

    if not discussion:
        raise HTTPNotFound("Discussion with id '%d' not found." % (
            discussion_id,))

    roles = db.query(Role).all()
    roles_by_name = {r.name: r for r in roles}
    role_names = [r.name for r in roles]
    permissions = db.query(Permission).all()
    perms_by_name = {p.name: p for p in permissions}
    permission_names = [p.name for p in permissions]

    disc_perms = db.query(DiscussionPermission).filter_by(
        discussion_id=discussion_id).join(Role, Permission).all()
    disc_perms_as_set = set((dp.role.name, dp.permission.name)
                            for dp in disc_perms)
    disc_perms_dict = {(dp.role.name, dp.permission.name): dp
                       for dp in disc_perms}
    local_roles = db.query(LocalUserRole).filter_by(
        discussion_id=discussion_id).join(Role, User).all()
    local_roles_as_set = set((lur.user.id, lur.role.name)
                             for lur in local_roles)
    local_roles_dict = {(lur.user.id, lur.role.name):lur
                        for lur in local_roles}
    users = set(lur.user for lur in local_roles)

    if request.POST:
        if 'submit_role_permissions' in request.POST:
            for role in role_names:
                if role == R_SYSADMIN:
                    continue
                for permission in permission_names:
                    allowed_text = 'allowed_%s_%s' % (role, permission)
                    if (role, permission) not in disc_perms_as_set and \
                            allowed_text in request.POST:
                        dp = DiscussionPermission(
                            role=roles_by_name[role],
                            permission=perms_by_name[permission],
                            discussion_id=discussion_id)
                        disc_perms_dict[(role, permission)] = dp
                        disc_perms_as_set.add((role, permission))
                        db.add(dp)
                    elif (role, permission) in disc_perms_as_set and \
                            allowed_text not in request.POST:
                        dp = disc_perms_dict[(role, permission)]
                        del disc_perms_dict[(role, permission)]
                        disc_perms_as_set.remove((role, permission))
                        db.delete(dp)
                if not role in SYSTEM_ROLES and\
                    'delete_'+role in request.POST:
                    db.delete(roles_by_name[role])
                    del roles_by_name[role]
                    role_names.remove(role)
        elif 'submit_add_role' in request.POST:
            #TODO: Sanitize role
            role = Role(name='r:'+request.POST['new_role'])
            roles_by_name[role.name] = role
            role_names.append(role.name)
            db.add(role)
        elif 'submit_user_roles' in request.POST:
            user_ids = {u.id for u in users}
            for role in role_names:
                if role == R_SYSADMIN:
                    continue
                prefix = 'has_'+role+'_'
                for name in request.POST:
                    if name.startswith(prefix):
                        user_id = int(name[len(prefix):])
                        if user_id not in user_ids:
                            users.add(User.get_instance(user_id))
                            user_ids.add(user_id)
                for user in users:
                    has_role_text = 'has_%s_%d' % (role, user.id)
                    if (user.id, role) not in local_roles_as_set and \
                            has_role_text in request.POST:
                        lur = LocalUserRole(
                            role=roles_by_name[role],
                            user=user,
                            discussion_id=discussion_id)
                        local_roles.append(lur)
                        local_roles_dict[(user.id, role)] = lur
                        local_roles_as_set.add((user.id, role))
                        db.add(lur)
                    elif (user.id, role) in local_roles_as_set and \
                            has_role_text not in request.POST:
                        lur = local_roles_dict[(user.id, role)]
                        del local_roles_dict[(user.id, role)]
                        local_roles_as_set.remove((user.id, role))
                        local_roles.remove(lur)
                        db.delete(lur)

        elif 'submit_look_for_user' in request.POST:
            search_string = '%' + request.POST['user_search'] + '%'
            other_users = db.query(User).join(AgentProfile).filter(AgentProfile.name.ilike(search_string)).union(
                db.query(User).outerjoin(Username).filter(Username.username.ilike(search_string))).union(
                db.query(User).filter(User.preferred_email.ilike(search_string))).all()
            users.update(other_users)

    def allowed(role, permission):
        if role == R_SYSADMIN:
            return True
        return (role, permission) in disc_perms_as_set

    def has_local_role(user_id, role):
        return (user_id, role) in local_roles_as_set

    context = dict(
        discussion=discussion,
        allowed=allowed,
        roles=role_names,
        permissions=permission_names,
        users=users,
        has_local_role=has_local_role,
        is_system_role=lambda r: r in SYSTEM_ROLES
    )

    return render_to_response(
        'admin/discussion_permissions.jinja2',
        context,
        request=request)


@view_config(route_name='general_permissions', permission="P_SYSADMIN")
def general_permissions(request):
    user_id = authenticated_userid(request)
    db = Discussion.db()

    roles = db.query(Role).all()
    roles_by_name = {r.name: r for r in roles}
    role_names = [r.name for r in roles]
    permissions = db.query(Permission).all()
    perms_by_name = {p.name: p for p in permissions}
    permission_names = [p.name for p in permissions]

    user_roles = db.query(UserRole).join(Role, User).all()
    user_roles_as_set = set((lur.user.id, lur.role.name)
                             for lur in user_roles)
    user_roles_dict = {(lur.user.id, lur.role.name):lur
                        for lur in user_roles}
    users = set(lur.user for lur in user_roles)

    if request.POST:
        if 'submit_user_roles' in request.POST:
            user_ids = {u.id for u in users}
            for role in role_names:
                if role == R_SYSADMIN:
                    continue
                prefix = 'has_'+role+'_'
                for name in request.POST:
                    if name.startswith(prefix):
                        user_id = int(name[len(prefix):])
                        if user_id not in user_ids:
                            users.add(User.get_instance(user_id))
                            user_ids.add(user_id)
                for user in users:
                    has_role_text = 'has_%s_%d' % (role, user.id)
                    if (user.id, role) not in user_roles_as_set and \
                            has_role_text in request.POST:
                        ur = UserRole(
                            role=roles_by_name[role],
                            user=user)
                        user_roles.append(ur)
                        user_roles_dict[(user.id, role)] = ur
                        user_roles_as_set.add((user.id, role))
                        db.add(ur)
                    elif (user.id, role) in user_roles_as_set and \
                            has_role_text not in request.POST:
                        ur = user_roles_dict[(user.id, role)]
                        del user_roles_dict[(user.id, role)]
                        user_roles_as_set.remove((user.id, role))
                        user_roles.remove(ur)
                        db.delete(ur)

        elif 'submit_look_for_user' in request.POST:
            search_string = '%' + request.POST['user_search'] + '%'
            other_users = db.query(User).join(AgentProfile).filter(AgentProfile.name.ilike(search_string)).union(
                db.query(User).outerjoin(Username).filter(Username.username.ilike(search_string))).union(
                db.query(User).filter(User.preferred_email.ilike(search_string))).all()
            users.update(other_users)

    def has_role(user_id, role):
        return (user_id, role) in user_roles_as_set

    context = dict(
        roles=role_names,
        permissions=permission_names,
        users=users,
        has_role=has_role,
        is_system_role=lambda r: r in SYSTEM_ROLES
    )

    return render_to_response(
        'admin/global_permissions.jinja2',
        context,
        request=request)