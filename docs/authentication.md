# TrustID authentication architecture

Phase 3 establishes a secure authentication foundation for the protected TrustID console. The current development implementation uses an `AuthService` with a repository-shaped interface and environment-configured fictional demo users. SQLAlchemy models and an Alembic migration define the persistent `users`, `roles`, and `user_roles` schema for the next persistence integration.

## Authentication flow

The login form submits an identifier and password to `POST /api/v1/auth/login`. The backend verifies a scrypt password hash, rejects inactive accounts, creates a random session identifier, and returns only safe user information. The session identifier is sent as an HttpOnly, SameSite=Lax cookie. The browser never receives a password hash or secret token in JSON and never stores the session in localStorage or sessionStorage.

`GET /api/v1/auth/me` resolves the current cookie session and returns the authenticated user, roles, permissions, and active status. `POST /api/v1/auth/logout` revokes the server-side session and expires the cookie. Sessions currently expire according to `SESSION_COOKIE_MAX_AGE` and are held in the development service process; production deployment must move session persistence to a shared database or Redis-backed repository before horizontal scaling.

Unauthenticated API calls return `401 Authentication required.` Protected frontend destinations use the centralized `AuthProvider` and redirect unauthenticated users to `/login`. Login failures use the same generic `Invalid credentials.` response for missing, incorrect, or inactive accounts so account existence is not disclosed.

## Password security

Passwords are never stored directly. The development helper uses salted `scrypt` with a strong work factor and constant-time digest comparison. Passwords are not logged, returned by APIs, or embedded in frontend state. A minimum length of ten characters is enforced when creating a credential.

## Roles and permissions

The initial application roles are `ADMIN`, `OFFICER`, `SUPERVISOR`, and `AUDITOR`. Permissions are explicit and server-enforced. Frontend navigation filters visibility for usability, but API dependencies independently require the relevant permission and return `403` for authenticated users without access.

- **ADMIN:** full console, user management, and system configuration permissions.
- **OFFICER:** verification workflow, case work, reports, and console access.
- **SUPERVISOR:** verification oversight, cases, analytics, reports, audit visibility, and console access.
- **AUDITOR:** read-only audit and report visibility plus console access.

## Security hardening

The API adds `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy: no-referrer`. CORS remains explicit and environment-configured. The cookie is secure when `SESSION_COOKIE_SECURE=true` is set in a TLS deployment. Because cookie sessions are used, production must add CSRF protection for state-changing browser requests and a shared session store. Login rate limiting is documented as a hardening item because the current local foundation has no distributed limiter.

Authentication event logging is limited to event names and a non-sensitive user ID for successful login; passwords, tokens, and credential payloads are never logged. Future audit persistence should represent `LOGIN_SUCCESS`, `LOGIN_FAILURE`, `LOGOUT`, and `ACCOUNT_DEACTIVATED` without sensitive values.

## Demo accounts and limitations

Demo accounts are fictional and created only when `DEMO_PASSWORD` is supplied in the server environment. The password is intentionally absent from the repository and frontend. The current service is suitable for local demonstration and tests, not production deployment until persistent user/session repositories, CSRF protection, login rate limiting, password reset policy, and operational secret management are added.
