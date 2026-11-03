"""Day 7 - tests for registration, login, logout, protected pages and CSRF."""

import re

import pytest

from app.models import Note, User
from app.utils import is_safe_redirect
from tests.conftest import TEST_PASSWORD


def register(client, **overrides):
    data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "a-good-password",
        "confirm_password": "a-good-password",
    }
    data.update(overrides)
    return client.post("/register", data=data)


# ---------- Registration ----------

def test_register_creates_user_and_logs_them_in(client):
    response = register(client)
    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    assert User.query.filter_by(username="newuser").count() == 1
    assert client.get("/").status_code == 200  # already logged in


def test_password_is_stored_only_as_a_hash(client):
    register(client)
    user = User.query.filter_by(username="newuser").first()
    assert user.password_hash != "a-good-password"
    assert "a-good-password" not in user.password_hash
    assert user.password_hash.startswith("scrypt:")
    assert user.check_password("a-good-password")
    assert not user.check_password("wrong-password")


def test_same_password_gives_different_hashes_because_of_salt():
    first, second = User(), User()
    first.set_password(TEST_PASSWORD)
    second.set_password(TEST_PASSWORD)
    assert first.password_hash != second.password_hash


@pytest.mark.parametrize("overrides, message", [
    ({"username": ""}, "Enter a username."),
    ({"username": "ab"}, "Use 3 to 30 letters"),
    ({"username": "bad name!"}, "Use 3 to 30 letters"),
    ({"email": ""}, "Enter your email address."),
    ({"email": "not-an-email"}, "Enter a valid email address."),
    ({"password": "short", "confirm_password": "short"}, "8 to 128 characters"),
    ({"confirm_password": "different-password"}, "don&#39;t match"),
])
def test_register_rejects_invalid_input(client, overrides, message):
    response = register(client, **overrides)
    assert response.status_code == 200  # the form is shown again
    assert message in response.get_data(as_text=True)
    assert User.query.count() == 0


def test_register_rejects_duplicate_username_ignoring_case(client, make_user):
    make_user("alice")
    response = register(client, username="ALICE")
    assert "already taken" in response.get_data(as_text=True)
    assert User.query.count() == 1


def test_register_rejects_duplicate_email_ignoring_case(client, make_user):
    make_user("alice", "alice@example.com")
    response = register(client, email="ALICE@example.com")
    assert "already exists" in response.get_data(as_text=True)
    assert User.query.count() == 1


def test_email_is_saved_in_lower_case(client):
    register(client, email="  MixedCase@Example.COM ")
    assert User.query.first().email == "mixedcase@example.com"


def test_failed_form_never_shows_the_password_again(client):
    html = register(client, email="bad", password="my-secret-pass",
                    confirm_password="my-secret-pass").get_data(as_text=True)
    assert "my-secret-pass" not in html


# ---------- Login ----------

@pytest.mark.parametrize("identifier", ["alice", "ALICE", "alice@example.com", "Alice@Example.com"])
def test_login_works_with_username_or_email(client, make_user, login, identifier):
    make_user("alice")
    response = login(client, identifier)
    assert response.status_code == 302
    assert response.headers["Location"] == "/"


def test_wrong_password_and_unknown_user_get_the_same_message(client, make_user, login):
    make_user("alice")
    wrong_password = login(client, "alice", "wrong-password")
    unknown_user = login(client, "nobody")
    message = "Incorrect username, email or password."
    assert message in wrong_password.get_data(as_text=True)
    assert message in unknown_user.get_data(as_text=True)
    assert client.get("/").status_code == 302  # still not logged in


def test_login_requires_both_fields(client):
    html = client.post("/login", data={}).get_data(as_text=True)
    assert "Enter your username or email." in html
    assert "Enter your password." in html


def test_login_returns_to_the_page_originally_requested(client, make_user):
    make_user("alice")
    response = client.post("/login?next=/health",
                           data={"identifier": "alice", "password": TEST_PASSWORD})
    assert response.headers["Location"] == "/health"


def test_login_ignores_next_pointing_to_another_site(client, make_user):
    make_user("alice")
    response = client.post("/login?next=https://evil.example/",
                           data={"identifier": "alice", "password": TEST_PASSWORD})
    assert response.headers["Location"] == "/"


@pytest.mark.parametrize("target, expected", [
    ("/", True),
    ("/tasks?page=2", True),
    ("https://evil.example", False),
    ("//evil.example", False),
    ("/\\evil.example", False),
    ("javascript:alert(1)", False),
    ("", False),
    (None, False),
])
def test_is_safe_redirect(target, expected):
    assert is_safe_redirect(target) is expected


def test_remember_me_sets_a_lasting_cookie_only_when_ticked(app, make_user, login):
    make_user("alice")
    with_remember = app.test_client()
    without_remember = app.test_client()
    login(with_remember, "alice", remember="y")
    assert with_remember.get_cookie("remember_token") is not None
    login(without_remember, "alice")
    assert without_remember.get_cookie("remember_token") is None


def test_session_cookie_is_protected(client, make_user, login):
    make_user("alice")
    cookie = client.post("/login", data={"identifier": "alice", "password": TEST_PASSWORD}) \
        .headers.get("Set-Cookie", "")
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


# ---------- Logout and protected pages ----------

def test_dashboard_redirects_visitors_to_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


def test_logged_in_user_is_redirected_away_from_login_and_register(auth_client):
    assert auth_client.get("/login").headers["Location"] == "/"
    assert auth_client.get("/register").headers["Location"] == "/"


def test_logout_ends_the_session(auth_client):
    assert auth_client.get("/").status_code == 200
    assert auth_client.post("/logout").headers["Location"] == "/login"
    assert auth_client.get("/").status_code == 302


def test_logout_cannot_be_triggered_by_a_get_request(auth_client):
    assert auth_client.get("/logout").status_code == 405
    assert auth_client.get("/").status_code == 200  # still logged in


def test_each_user_sees_only_their_own_dashboard(app, db, make_user, login):
    alice, bob = make_user("alice"), make_user("bob")
    db.session.add_all([Note(user=alice, title="Alice private note"),
                        Note(user=bob, title="Bob private note")])
    db.session.commit()

    alice_client, bob_client = app.test_client(), app.test_client()
    login(alice_client, "alice")
    login(bob_client, "bob")

    alice_page = alice_client.get("/").get_data(as_text=True)
    bob_page = bob_client.get("/").get_data(as_text=True)
    assert "Alice private note" in alice_page and "Bob private note" not in alice_page
    assert "Bob private note" in bob_page and "Alice private note" not in bob_page


def test_deleted_users_session_stops_working(auth_client, db):
    db.session.delete(User.query.filter_by(username="tester").first())
    db.session.commit()
    assert auth_client.get("/").status_code == 302


def test_header_shows_user_name_and_logout(auth_client):
    html = auth_client.get("/").get_data(as_text=True)
    assert "tester" in html
    assert "Log out" in html
    assert 'name="csrf_token"' in html


# ---------- CSRF protection (switched on for these tests) ----------

@pytest.fixture
def csrf_client(app):
    app.config["WTF_CSRF_ENABLED"] = True
    return app.test_client()


def get_token(client, path):
    html = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)


def test_post_without_csrf_token_is_rejected(csrf_client, make_user):
    make_user("alice")
    response = csrf_client.post("/login", data={"identifier": "alice", "password": TEST_PASSWORD})
    assert response.status_code == 400
    assert "form has expired" in response.get_data(as_text=True)


def test_post_with_wrong_csrf_token_is_rejected(csrf_client):
    response = csrf_client.post("/register", data={
        "csrf_token": "made-up-token", "username": "attacker", "email": "a@example.com",
        "password": "a-good-password", "confirm_password": "a-good-password",
    })
    assert response.status_code == 400
    assert User.query.count() == 0


def test_login_and_logout_work_with_real_csrf_tokens(csrf_client, make_user):
    make_user("alice")
    response = csrf_client.post("/login", data={
        "csrf_token": get_token(csrf_client, "/login"),
        "identifier": "alice", "password": TEST_PASSWORD,
    })
    assert response.status_code == 302
    assert csrf_client.get("/").status_code == 200

    logout_token = get_token(csrf_client, "/")
    assert csrf_client.post("/logout").status_code == 400  # no token: still logged in
    assert csrf_client.get("/").status_code == 200
    assert csrf_client.post("/logout", data={"csrf_token": logout_token}).status_code == 302
    assert csrf_client.get("/").status_code == 302
