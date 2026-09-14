from enum import StrEnum


class Role(StrEnum):
    ADMIN = "ADMIN"
    OFFICER = "OFFICER"
    SUPERVISOR = "SUPERVISOR"
    AUDITOR = "AUDITOR"


class Permission(StrEnum):
    CONSOLE_ACCESS = "console:access"
    VERIFICATION_WORKFLOW = "verification:workflow"
    CASE_WORK = "case:work"
    OVERSIGHT = "oversight:read"
    ANALYTICS = "analytics:read"
    AUDIT = "audit:read"
    REPORTS = "reports:read"
    USER_MANAGEMENT = "users:manage"
    SYSTEM_CONFIGURATION = "system:configure"

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset(Permission),
    Role.OFFICER: frozenset({Permission.CONSOLE_ACCESS, Permission.VERIFICATION_WORKFLOW, Permission.CASE_WORK, Permission.REPORTS}),
    Role.SUPERVISOR: frozenset({Permission.CONSOLE_ACCESS, Permission.VERIFICATION_WORKFLOW, Permission.CASE_WORK, Permission.OVERSIGHT, Permission.ANALYTICS, Permission.AUDIT, Permission.REPORTS}),
    Role.AUDITOR: frozenset({Permission.CONSOLE_ACCESS, Permission.AUDIT, Permission.REPORTS}),
}


def permissions_for_roles(roles: set[Role]) -> set[Permission]:
    return set().union(*(ROLE_PERMISSIONS.get(role, frozenset()) for role in roles)) if roles else set()
