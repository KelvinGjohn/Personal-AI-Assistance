# Development Log — Day 07

| Field | Entry |
|-------|-------|
| Date | 2 November 2026 |
| Day | 7 of 29 |
| Phase | 2 — Core application development |

## Objectives
- Build registration and login forms
- Implement password hashing
- Configure Flask-Login
- Implement logout
- Protect private application routes
- Validate user inputs

## Tasks completed
- `User` model: `set_password()` / `check_password()` (Werkzeug salted scrypt hashes), `UserMixin`, `display_name`, and the `load_user` callback
- `app/forms/auth_forms.py`: `RegistrationForm` and `LoginForm` with server-side validation
- `app/routes/auth.py`: `/register`, `/login`, `/logout`
- Login accepts username or email, is not case-sensitive, and offers "Keep me logged in"
- `@login_required` on the dashboard, which now uses `current_user`. The temporary "first user" code from Day 6 and its notice were removed
- CSRF protection on every POST (`CSRFProtect`), with a friendly "form expired" page
- Safe cookie settings: HttpOnly and SameSite=Lax always; Secure in production
- Header shows the user's name and a logout menu
- Demo account: the seed script now prints a new random password each run, so no password is in the code

## Security decisions
| Decision | Why |
|----------|-----|
| Only a salted hash is stored | A database leak doesn't reveal passwords; equal passwords get different hashes |
| Same error for wrong password and unknown user | The login page can't be used to discover who has an account |
| `next` is checked by `is_safe_redirect()` | Prevents a login link from sending users to another website (open redirect) |
| Logout is POST with a CSRF token | Another website can't log a user out with a link or image |
| Database UNIQUE errors are caught on registration | Handles two people choosing the same name at the same moment |

## How the files connect
`POST /login` → `csrf.protect()` checks the token → `LoginForm` validates → the route finds the `User` → `check_password()` → `login_user()` puts the user's id in the signed session cookie. On later requests, `load_user()` turns that id back into `current_user`, and `@login_required` redirects anyone without one to `/login?next=...`.

## Files created
- `app/forms/__init__.py`, `app/forms/auth_forms.py`
- `app/routes/auth.py`
- `app/templates/auth/layout.html`, `auth/login.html`, `auth/register.html`
- `app/templates/errors/400.html`
- `app/templates/partials/form_field.html`, `head_assets.html`, `scripts.html`
- `tests/test_auth.py`
- `documentation/daily_logs/Day07.md`

## Files modified
- `app/extensions.py`: `login_manager`, `csrf`
- `app/models/user.py`: password methods, `UserMixin`, `load_user`
- `app/__init__.py`: `init_security()`, auth Blueprint, CSRF error page
- `app/routes/main.py`: `@login_required`, `current_user`
- `app/services/dashboard_service.py`: removed `get_empty_dashboard_data()`, no longer needed
- `app/templates/base.html`: account menu; shared assets moved to partials so the login pages can reuse them
- `app/templates/dashboard.html`, `app/static/css/style.css`
- `config/settings.py`: cookie settings; CSRF off in the testing config (`test_auth.py` turns it on)
- `scripts/seed_demo_data.py`: generates a password
- `tests/conftest.py`: `RealisticClient`, `login`, `auth_client`
- `tests/test_app.py`, `tests/test_frontend.py`, `tests/test_dashboard.py`: log in first, because `/` is now protected
- `PLAN.md`, `README.md`

## Database changes
- No table changes (`password_hash` has existed since Day 4).

## Technologies used
- Flask-Login, Flask-WTF / WTForms, email-validator, Werkzeug security, Jinja2 macros, Pytest, requests (for the HTTP check)

## Problems encountered and solutions
1. **Problem:** `test_each_user_sees_only_their_own_dashboard` and `test_deleted_users_session_stops_working` failed: Bob's request saw Alice.
   **Cause:** the test fixture kept one app context open, so all requests shared one `g`, where Flask-Login caches the current user. A real server creates a new context per request.
   **Solution:** `RealisticClient` runs each request in an empty context. Because a privacy failure should not be dismissed on a theory, it was also checked against a real running server with two sessions: each user saw only their own note.
2. **Problem:** links were Bootstrap blue instead of the app's teal.
   **Cause:** Bootstrap 5.3 reads `--bs-link-color-rgb`, not `--bs-link-color`.
   **Solution:** set the correct variables in `style.css`.
3. **Problem:** a new user was greeted with "Welcome back".
   **Solution:** changed to "Welcome".

## Test results
- `pytest`: **85 passed, 0 failed, 1 warning** (see "Known warning"). Day 7 adds tests for hashing and salt, every validation rule, duplicate names and emails, login by username or email, identical failure messages, safe redirects, remember-me, cookie flags, logout, protected pages, per-user dashboards, deleted users' sessions, and CSRF (missing, wrong and real tokens).
- Real server with a throwaway database, two HTTP sessions:
  - Each user saw their own note and not the other's
  - Password stored as `scrypt:` and the plain password was not in the database
  - Visitor to `/` → 302 to `/login?next=%2F`
  - POST to `/login` without a CSRF token → 400
  - Logout → 302, then `/` redirects; logging in again by email works; wrong password shows the generic message
- Browser at 1280×800: login page, registration errors under each field (password fields cleared), successful registration landing on an empty dashboard, account menu, and the real Log out button.
- Browser at 375 px: registration page measured with no overflowing elements (card at 16–359 px). Links confirmed teal.
- Note for Day 26: form inputs are about 37 px tall, below the 44 px touch-target goal.

## Known warning
- Pytest shows a `DeprecationWarning` from inside Flask-Login 0.6.3 (`datetime.utcnow()`). It is in the library, not this project, and causes no failure today. Check for a newer Flask-Login on Day 25.

## Outstanding issues
- No limit on login attempts yet (to be assessed in the Day 24 security review).
- Times are shown in UTC until Day 8.

## Git commit
- `Day 07: Add user registration and authentication`

## Next day's objectives (Day 8)
- Profile page: update name and email
- Change password (current password required)
- Preferences such as time zone, with times shown in the user's own zone

## Completion review
Day 7 is **complete**: users can register, log in and log out, private pages are protected, and each user sees only their own data, verified both by automated tests and on a real server.
