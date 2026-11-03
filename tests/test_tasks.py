"""Day 9 - tests for the task module."""

import re
from datetime import datetime, timedelta

import pytest

from app.models import Task, User
from app.services.task_service import TASKS_PER_PAGE, build_task_query, get_user_categories
from app.utils import utc_now


def get_tester():
    return User.query.filter_by(username="tester").first()


def add_task(db, user=None, **fields):
    fields.setdefault("title", "A task")
    task = Task(user=user or get_tester(), **fields)
    db.session.add(task)
    db.session.commit()
    return task


def post_task(client, path="/tasks/new", **overrides):
    data = {"title": "Write report", "description": "", "priority": "medium",
            "category": "", "due_date": ""}
    data.update(overrides)
    return client.post(path, data=data)


def page(client, path="/tasks"):
    return client.get(path).get_data(as_text=True)


# ---------- Login required ----------

@pytest.mark.parametrize("method, path", [
    ("get", "/tasks"),
    ("get", "/tasks/new"),
    ("post", "/tasks/new"),
    ("get", "/tasks/1/edit"),
    ("post", "/tasks/1/complete"),
    ("post", "/tasks/1/reopen"),
    ("post", "/tasks/1/delete"),
])
def test_every_task_page_requires_login(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


# ---------- Create ----------

def test_create_task_with_all_fields(auth_client):
    response = post_task(auth_client, title="  Write report ", description="Chapter 1",
                         priority="high", category="University", due_date="2099-01-15T12:30")
    assert response.status_code == 302
    task = Task.query.one()
    assert task.user_id == get_tester().id
    assert task.title == "Write report"
    assert task.description == "Chapter 1"
    assert task.priority == "high"
    assert task.category == "University"
    assert task.due_date == datetime(2099, 1, 15, 12, 30)
    assert task.is_completed is False


def test_create_task_with_only_a_title_saves_empty_fields_as_null(auth_client):
    post_task(auth_client)
    task = Task.query.one()
    assert task.description is None
    assert task.category is None
    assert task.due_date is None
    assert task.priority == "medium"


@pytest.mark.parametrize("overrides, message", [
    ({"title": ""}, "Enter a title."),
    ({"title": "    "}, "Enter a title."),
    ({"title": "x" * 201}, "200 characters or fewer"),
    ({"description": "x" * 5001}, "5000 characters or fewer"),
    ({"category": "x" * 51}, "50 characters or fewer"),
    ({"priority": "urgent"}, "Not a valid choice"),
    ({"due_date": "not-a-date"}, "Not a valid datetime"),
    ({"due_date": "0001-01-01T00:00"}, "between 2000 and 2100"),
    ({"due_date": "9999-12-31T23:59"}, "between 2000 and 2100"),
])
def test_invalid_task_is_rejected(auth_client, overrides, message):
    response = post_task(auth_client, **overrides)
    assert response.status_code == 200
    assert message in response.get_data(as_text=True)
    assert Task.query.count() == 0


def test_form_cannot_set_the_owner(auth_client, make_user):
    alice = make_user("alice")
    post_task(auth_client, user_id=alice.id)
    assert Task.query.one().user_id == get_tester().id


# ---------- Time zones ----------

def test_due_date_typed_in_user_zone_is_saved_as_utc(db, auth_client):
    get_tester().timezone = "Europe/Paris"
    db.session.commit()
    post_task(auth_client, due_date="2099-01-15T13:00")
    assert Task.query.one().due_date == datetime(2099, 1, 15, 12, 0)


def test_saving_edit_form_unchanged_keeps_the_same_due_date(db, auth_client):
    get_tester().timezone = "Asia/Tokyo"
    task = add_task(db, title="Keep", due_date=datetime(2099, 7, 1, 3, 15))
    html = page(auth_client, f"/tasks/{task.id}/edit")
    shown = re.search(r'name="due_date"[^>]*value="([^"]+)"', html).group(1)
    assert shown == "2099-07-01T12:15"

    post_task(auth_client, f"/tasks/{task.id}/edit", title="Keep", due_date=shown)
    assert db.session.get(Task, task.id).due_date == datetime(2099, 7, 1, 3, 15)


# ---------- Edit ----------

def test_edit_form_is_filled_with_saved_values(db, auth_client):
    task = add_task(db, title="Original", description="Details", priority="low", category="Home")
    html = page(auth_client, f"/tasks/{task.id}/edit")
    assert 'value="Original"' in html
    assert "Details" in html
    assert 'value="Home"' in html
    assert re.search(r'<option selected value="low">|<option value="low" selected>', html)


def test_edit_saves_changes_and_can_clear_fields(db, auth_client):
    task = add_task(db, title="Original", category="Home", due_date=datetime(2099, 1, 1))
    response = post_task(auth_client, f"/tasks/{task.id}/edit", title="Changed", priority="high")
    assert response.status_code == 302
    task = db.session.get(Task, task.id)
    assert task.title == "Changed"
    assert task.priority == "high"
    assert task.category is None
    assert task.due_date is None


def test_invalid_edit_changes_nothing(db, auth_client):
    task = add_task(db, title="Original")
    response = post_task(auth_client, f"/tasks/{task.id}/edit", title="")
    assert "Enter a title." in response.get_data(as_text=True)
    assert db.session.get(Task, task.id).title == "Original"


# ---------- Complete and reopen ----------

def test_complete_then_reopen(db, auth_client):
    task = add_task(db)
    assert auth_client.post(f"/tasks/{task.id}/complete").status_code == 302
    task = db.session.get(Task, task.id)
    assert task.is_completed is True
    assert task.completed_at is not None

    auth_client.post(f"/tasks/{task.id}/reopen")
    task = db.session.get(Task, task.id)
    assert task.is_completed is False
    assert task.completed_at is None


def test_completing_twice_keeps_the_first_finish_time(db, auth_client):
    finished = datetime(2026, 1, 1)
    task = add_task(db, is_completed=True, completed_at=finished)
    auth_client.post(f"/tasks/{task.id}/complete")
    assert db.session.get(Task, task.id).completed_at == finished


def test_complete_cannot_be_triggered_by_a_link(db, auth_client):
    task = add_task(db)
    assert auth_client.get(f"/tasks/{task.id}/complete").status_code == 405
    assert db.session.get(Task, task.id).is_completed is False


def test_complete_returns_to_the_filtered_list(db, auth_client):
    task = add_task(db)
    response = auth_client.post(f"/tasks/{task.id}/complete", data={"next": "/tasks?status=pending"})
    assert response.headers["Location"] == "/tasks?status=pending"


def test_complete_ignores_next_pointing_to_another_site(db, auth_client):
    task = add_task(db)
    response = auth_client.post(f"/tasks/{task.id}/complete", data={"next": "https://evil.example/"})
    assert response.headers["Location"] == "/tasks"


def test_completed_task_is_not_overdue_on_the_list(db, auth_client):
    add_task(db, title="Late", due_date=utc_now() - timedelta(days=1))
    add_task(db, title="Finished", due_date=utc_now() - timedelta(days=1), is_completed=True)
    assert page(auth_client).count("Overdue ·") == 1


# ---------- Delete ----------

def test_get_only_asks_and_post_deletes(db, auth_client):
    task = add_task(db, title="Remove me")
    assert 'Delete "Remove me"?' in page(auth_client, f"/tasks/{task.id}/delete")
    assert Task.query.count() == 1

    assert auth_client.post(f"/tasks/{task.id}/delete").status_code == 302
    assert Task.query.count() == 0


# ---------- One user can't reach another user's tasks ----------

@pytest.mark.parametrize("method, action", [
    ("get", "edit"),
    ("post", "edit"),
    ("post", "complete"),
    ("post", "reopen"),
    ("get", "delete"),
    ("post", "delete"),
])
def test_another_users_task_gives_404_and_stays_unchanged(db, auth_client, make_user, method, action):
    alice = make_user("alice")
    task = add_task(db, user=alice, title="Alice private task")
    response = getattr(auth_client, method)(f"/tasks/{task.id}/{action}", data={"title": "Hacked"})
    assert response.status_code == 404
    assert "Alice private task" not in response.get_data(as_text=True)

    task = db.session.get(Task, task.id)
    assert task.title == "Alice private task"
    assert task.is_completed is False


def test_list_filters_and_suggestions_show_only_own_tasks(db, auth_client, make_user):
    alice = make_user("alice")
    add_task(db, user=alice, title="Alice private task", category="AliceCategory")
    add_task(db, title="My task", category="MyCategory")
    for path in ("/tasks", "/tasks/new", "/tasks?category=AliceCategory"):
        html = page(auth_client, path)
        assert "Alice private task" not in html
        assert "AliceCategory</option>" not in html
        assert '<option value="AliceCategory"></option>' not in html


@pytest.mark.parametrize("path", ["/tasks/999/edit", "/tasks/99999999999999999999/edit"])
def test_task_id_that_does_not_exist_gives_404(auth_client, path):
    assert auth_client.get(path).status_code == 404


# ---------- Filters ----------

@pytest.fixture
def mixed_tasks(db, auth_client):
    now = utc_now()
    add_task(db, title="Late one", priority="high", category="Work", due_date=now - timedelta(days=1))
    add_task(db, title="Future one", priority="low", category="Home", due_date=now + timedelta(days=1))
    add_task(db, title="Undated one", priority="low", category="Work")
    add_task(db, title="Finished one", priority="high", category="Home", is_completed=True,
             completed_at=now, due_date=now - timedelta(days=2))
    return auth_client


def titles(html):
    return [t for t in ("Late one", "Future one", "Undated one", "Finished one") if t in html]


@pytest.mark.parametrize("query, expected", [
    ("", ["Late one", "Future one", "Undated one", "Finished one"]),
    ("?status=pending", ["Late one", "Future one", "Undated one"]),
    ("?status=overdue", ["Late one"]),
    ("?status=completed", ["Finished one"]),
    ("?priority=high", ["Late one", "Finished one"]),
    ("?category=Work", ["Late one", "Undated one"]),
    ("?status=pending&priority=low&category=Work", ["Undated one"]),
    # Unknown values are ignored instead of causing an error
    ("?status=nonsense&priority=nonsense", ["Late one", "Future one", "Undated one", "Finished one"]),
])
def test_filters(mixed_tasks, query, expected):
    assert titles(page(mixed_tasks, "/tasks" + query)) == expected


def test_filter_with_no_results_shows_a_message(mixed_tasks):
    assert "No tasks match these filters." in page(mixed_tasks, "/tasks?category=Nothing")


def test_count_wording_is_correct_for_one_and_many(mixed_tasks):
    assert "1 task matches your filters" in page(mixed_tasks, "/tasks?status=overdue")
    assert "3 tasks match your filters" in page(mixed_tasks, "/tasks?status=pending")
    assert "4 tasks" in page(mixed_tasks)


def test_order_is_unfinished_first_then_earliest_due_with_undated_last(db, auth_client):
    now = utc_now()
    add_task(db, title="c-undated")
    add_task(db, title="d-finished", is_completed=True, due_date=now - timedelta(days=9))
    add_task(db, title="b-later", due_date=now + timedelta(days=2))
    add_task(db, title="a-sooner", due_date=now + timedelta(days=1))
    tasks = build_task_query(get_tester().id).all()
    assert [t.title for t in tasks] == ["a-sooner", "b-later", "c-undated", "d-finished"]


def test_categories_are_unique_and_sorted(db, auth_client):
    for category in ("Work", "Home", "Work", None):
        add_task(db, category=category)
    assert get_user_categories(get_tester().id) == ["Home", "Work"]


# ---------- Pages ----------

def test_long_lists_are_split_into_pages_and_keep_filters(db, auth_client):
    user = get_tester()
    db.session.add_all([Task(user=user, title=f"Task {n}", priority="low")
                        for n in range(TASKS_PER_PAGE + 1)])
    db.session.commit()

    html = page(auth_client, "/tasks?priority=low")
    assert html.count('class="list-group-item app-task"') == TASKS_PER_PAGE
    assert "Page 1 of 2" in html
    assert "/tasks?page=2&amp;priority=low" in html or "/tasks?priority=low&amp;page=2" in html

    html = page(auth_client, "/tasks?priority=low&page=2")
    assert html.count('class="list-group-item app-task"') == 1


@pytest.mark.parametrize("number", ["0", "-5", "999", "99999999999999999999999", "abc"])
def test_bad_page_numbers_are_corrected(db, auth_client, number):
    add_task(db, title="Still shown")
    response = auth_client.get(f"/tasks?page={number}")
    assert response.status_code == 200
    assert "Still shown" in response.get_data(as_text=True)


# ---------- Display and safety ----------

def test_new_user_sees_the_empty_message(auth_client):
    assert "You have no tasks yet." in page(auth_client)


def test_user_text_is_shown_as_text_not_run(db, auth_client):
    bad = "<script>alert(1)</script>"
    post_task(auth_client, title=bad, description=bad, category=bad)
    for path in ("/tasks", "/"):
        assert bad not in page(auth_client, path)
    assert bad not in page(auth_client, f"/tasks/{Task.query.one().id}/edit")


def test_menu_highlights_tasks_on_every_task_page(auth_client):
    for path in ("/tasks", "/tasks/new"):
        html = page(auth_client, path)
        assert re.search(r'nav-link active"\s+href="/tasks"', html)


def test_new_task_appears_on_the_dashboard(auth_client):
    post_task(auth_client, title="Shown on dashboard", due_date="2099-01-15T12:00")
    html = page(auth_client, "/")
    assert "Shown on dashboard" in html
    assert 'href="/tasks"' in html


# ---------- CSRF ----------

@pytest.mark.parametrize("action", ["complete", "reopen", "delete", "edit"])
def test_changes_without_csrf_token_are_rejected(app, db, auth_client, action):
    task = add_task(db, title="Protected")
    app.config["WTF_CSRF_ENABLED"] = True
    assert auth_client.post(f"/tasks/{task.id}/{action}").status_code == 400
    task = db.session.get(Task, task.id)
    assert task.title == "Protected"
    assert task.is_completed is False


def test_real_forms_carry_working_csrf_tokens(app, db, auth_client):
    task = add_task(db, title="Finish me")
    app.config["WTF_CSRF_ENABLED"] = True
    html = page(auth_client)
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    assert auth_client.post(f"/tasks/{task.id}/complete", data={"csrf_token": token}).status_code == 302
    assert db.session.get(Task, task.id).is_completed is True
