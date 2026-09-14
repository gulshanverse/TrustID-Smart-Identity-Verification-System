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
    DOCUMENT_CREATE = "document:create"
    DOCUMENT_READ = "document:read"
    DOCUMENT_DELETE = "document:delete"
    CASE_ASSIGN = "case:assign"
    CASE_DECIDE = "case:decide"
    CASE_RESOLVE = "case:resolve"

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset(Permission),
    Role.OFFICER: frozenset({Permission.CONSOLE_ACCESS, Permission.VERIFICATION_WORKFLOW, Permission.CASE_WORK, Permission.CASE_DECIDE, Permission.ANALYTICS, Permission.REPORTS, Permission.DOCUMENT_CREATE, Permission.DOCUMENT_READ, Permission.DOCUMENT_DELETE}),
    Role.SUPERVISOR: frozenset({Permission.CONSOLE_ACCESS, Permission.VERIFICATION_WORKFLOW, Permission.CASE_WORK, Permission.CASE_ASSIGN, Permission.CASE_DECIDE, Permission.CASE_RESOLVE, Permission.OVERSIGHT, Permission.ANALYTICS, Permission.AUDIT, Permission.REPORTS, Permission.DOCUMENT_CREATE, Permission.DOCUMENT_READ, Permission.DOCUMENT_DELETE}),
    Role.AUDITOR: frozenset({Permission.CONSOLE_ACCESS, Permission.AUDIT, Permission.REPORTS}),
}


def permissions_for_roles(roles: set[Role]) -> set[Permission]:
    return set().union(*(ROLE_PERMISSIONS.get(role, frozenset()) for role in roles)) if roles else set()
