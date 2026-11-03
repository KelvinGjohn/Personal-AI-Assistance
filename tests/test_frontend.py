"""Day 5 - tests for the base layout, sidebar, flash messages and error pages."""

from flask import flash, redirect, url_for


def page_html(client, path="/"):
    return client.get(path).get_data(as_text=True)


def test_layout_loads_bootstrap_and_is_mobile_ready(auth_client):
    html = page_html(auth_client)
    assert "bootstrap@5.3.3/dist/css/bootstrap.min.css" in html
    assert "bootstrap.bundle.min.js" in html
    assert 'name="viewport"' in html
    assert "css/style.css" in html


def test_page_title_is_set_by_the_child_template(auth_client):
    assert "<title>Dashboard · Personal AI Assistant</title>" in page_html(auth_client)


def test_sidebar_marks_dashboard_as_current_page(auth_client):
    html = page_html(auth_client)
    assert 'aria-current="page"' in html
    assert 'href="/"' in html


def test_unbuilt_pages_are_disabled_not_broken_links(auth_client):
    html = page_html(auth_client)
    # Pages from later days are shown with their day, with no link to a missing route
    assert "Day 10" in html and "Day 13" in html
    assert 'href="/reminders' not in html
    assert 'aria-disabled="true"' in html


def test_dashboard_shows_all_summary_cards(auth_client):
    html = page_html(auth_client)
    for label in ("Pending tasks", "Upcoming reminders", "Notes", "Conversations"):
        assert label in html


def test_mobile_menu_button_targets_the_sidebar(auth_client):
    html = page_html(auth_client)
    assert 'data-bs-target="#sidebar"' in html
    assert 'id="sidebar"' in html
    assert 'aria-label="Open menu"' in html


def test_404_page_uses_the_layout(client):
    response = client.get("/does-not-exist")
    html = response.get_data(as_text=True)
    assert response.status_code == 404
    assert "find that page" in html
    assert 'id="sidebar"' in html


def test_500_page_is_friendly_and_hides_error_details(app):
    def broken():
        raise RuntimeError("secret internal detail")

    app.add_url_rule("/broken", "broken", broken)
    app.config["PROPAGATE_EXCEPTIONS"] = False  # behave like production instead of re-raising

    response = app.test_client().get("/broken")
    html = response.get_data(as_text=True)
    assert response.status_code == 500
    assert "something went wrong" in html
    assert "secret internal detail" not in html


def test_flash_messages_are_displayed(app, make_user, login):
    def flash_then_redirect():
        flash("Saved successfully", "success")
        return redirect(url_for("main.index"))

    app.add_url_rule("/flash-test", "flash_test", flash_then_redirect)

    client = app.test_client()
    make_user("tester")
    login(client, "tester")
    html = client.get("/flash-test", follow_redirects=True).get_data(as_text=True)
    assert "Saved successfully" in html
    assert "alert-success" in html
