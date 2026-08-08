OWNER = "owner"
ADMIN = "admin"
MEMBER = "member"


def can_view_family(user):
    return user.role in (OWNER, ADMIN, MEMBER)


def can_invite(user):
    return user.role in (OWNER, ADMIN)


def can_remove_members(user):
    return user.role in (OWNER, ADMIN)


def can_delete_family(user):
    return user.role == OWNER


def can_transfer_ownership(user):
    return user.role == OWNER


def can_change_roles(user):
    # Not in the Step 2 matrix explicitly, but Step 7/8 both frame
    # promote/demote/transfer as owner-only actions ("Owner clicks
    # Promote"), so role changes are restricted to the owner.
    return user.role == OWNER


def can_create_geofences(user):
    return user.role in (OWNER, ADMIN, MEMBER)


def can_send_sos(user):
    return user.role in (OWNER, ADMIN, MEMBER)