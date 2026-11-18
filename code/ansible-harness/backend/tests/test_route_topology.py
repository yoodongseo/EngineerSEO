"""Route topology tests - verify public URL contracts are preserved."""

import app.main as main


def _all_routes():
    """Return list of (method, path) for every registered route."""
    routes = []
    for route in main.app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            for method in route.methods:
                if method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                    routes.append((method, route.path))
    return routes


def test_project_discovery_routes_exist():
    """Assert exact project discovery paths exist with GET method."""
    routes = _all_routes()

    assert ("GET", "/api/projects") in routes, "GET /api/projects must be registered"
    assert ("GET", "/api/projects/{project_name}/playbooks") in routes, (
        "GET /api/projects/{project_name}/playbooks must be registered"
    )
    assert ("GET", "/api/projects/{project_name}/inventories") in routes, (
        "GET /api/projects/{project_name}/inventories must be registered"
    )


def test_project_managed_inventory_routes_exist():
    """Assert exact legacy managed inventory paths exist with expected methods."""
    routes = _all_routes()

    expected_routes = [
        ("GET", "/api/projects/{project_name}/managed-inventories"),
        ("GET", "/api/projects/{project_name}/managed-inventories/{filename}"),
        ("POST", "/api/projects/{project_name}/managed-inventories"),
        ("PUT", "/api/projects/{project_name}/managed-inventories/{filename}"),
        ("DELETE", "/api/projects/{project_name}/managed-inventories/{filename}"),
        (
            "POST",
            "/api/projects/{project_name}/managed-inventories/{filename}/groups/{group_name}/hosts/{host_name}/connection-test",
        ),
        (
            "POST",
            "/api/projects/{project_name}/managed-inventories/{filename}/groups/{group_name}/connection-test",
        ),
        ("POST", "/api/projects/{project_name}/managed-inventories/{filename}/connection-test"),
    ]

    for route in expected_routes:
        assert route in routes, f"{route[0]} {route[1]} must be registered"


def test_url_path_for_resolves():
    """Assert app.url_path_for resolves handler names to exact paths."""
    assert (
        main.app.url_path_for("list_projects") == "/api/projects"
    ), "list_projects should resolve to /api/projects"

    assert (
        main.app.url_path_for("list_project_playbooks", project_name="test")
        == "/api/projects/test/playbooks"
    ), "list_project_playbooks should resolve to /api/projects/{project_name}/playbooks"

    assert (
        main.app.url_path_for("list_project_inventories", project_name="test")
        == "/api/projects/test/inventories"
    ), "list_project_inventories should resolve to /api/projects/{project_name}/inventories"

    assert (
        main.app.url_path_for("list_project_managed_inventories", project_name="test")
        == "/api/projects/test/managed-inventories"
    ), "list_project_managed_inventories should resolve to /api/projects/{project_name}/managed-inventories"

    assert (
        main.app.url_path_for("get_project_managed_inventory", project_name="test", filename="hosts.ini")
        == "/api/projects/test/managed-inventories/hosts.ini"
    ), "get_project_managed_inventory should resolve to /api/projects/{project_name}/managed-inventories/{filename}"

    assert (
        main.app.url_path_for("create_project_managed_inventory", project_name="test")
        == "/api/projects/test/managed-inventories"
    ), "create_project_managed_inventory should resolve to /api/projects/{project_name}/managed-inventories"

    assert (
        main.app.url_path_for("update_project_managed_inventory", project_name="test", filename="hosts.ini")
        == "/api/projects/test/managed-inventories/hosts.ini"
    ), "update_project_managed_inventory should resolve to /api/projects/{project_name}/managed-inventories/{filename}"

    assert (
        main.app.url_path_for("delete_project_managed_inventory", project_name="test", filename="hosts.ini")
        == "/api/projects/test/managed-inventories/hosts.ini"
    ), "delete_project_managed_inventory should resolve to /api/projects/{project_name}/managed-inventories/{filename}"

    assert (
        main.app.url_path_for(
            "trigger_managed_inventory_host_connection_test",
            project_name="test",
            filename="hosts.ini",
            group_name="web",
            host_name="host-1",
        )
        == "/api/projects/test/managed-inventories/hosts.ini/groups/web/hosts/host-1/connection-test"
    ), "trigger_managed_inventory_host_connection_test should resolve to the exact host connection test path"

    assert (
        main.app.url_path_for(
            "trigger_managed_inventory_group_connection_test",
            project_name="test",
            filename="hosts.ini",
            group_name="web",
        )
        == "/api/projects/test/managed-inventories/hosts.ini/groups/web/connection-test"
    ), "trigger_managed_inventory_group_connection_test should resolve to the exact group connection test path"

    assert (
        main.app.url_path_for(
            "trigger_managed_inventory_inventory_connection_test",
            project_name="test",
            filename="hosts.ini",
        )
        == "/api/projects/test/managed-inventories/hosts.ini/connection-test"
    ), "trigger_managed_inventory_inventory_connection_test should resolve to the exact inventory connection test path"


def test_no_duplicate_project_discovery_routes():
    """Assert project discovery routes are registered exactly once."""
    routes = _all_routes()

    def count_routes(method: str, path: str) -> int:
        return sum(1 for m, p in routes if m == method and p == path)

    assert count_routes("GET", "/api/projects") == 1, (
        "GET /api/projects must not be duplicated"
    )
    assert count_routes("GET", "/api/projects/{project_name}/playbooks") == 1, (
        "GET /api/projects/{project_name}/playbooks must not be duplicated"
    )
    assert count_routes("GET", "/api/projects/{project_name}/inventories") == 1, (
        "GET /api/projects/{project_name}/inventories must not be duplicated"
    )


def test_no_duplicate_project_managed_inventory_routes():
    """Assert legacy managed inventory routes are registered exactly once."""
    routes = _all_routes()

    def count_routes(method: str, path: str) -> int:
        return sum(1 for m, p in routes if m == method and p == path)

    expected_routes = [
        ("GET", "/api/projects/{project_name}/managed-inventories"),
        ("GET", "/api/projects/{project_name}/managed-inventories/{filename}"),
        ("POST", "/api/projects/{project_name}/managed-inventories"),
        ("PUT", "/api/projects/{project_name}/managed-inventories/{filename}"),
        ("DELETE", "/api/projects/{project_name}/managed-inventories/{filename}"),
        (
            "POST",
            "/api/projects/{project_name}/managed-inventories/{filename}/groups/{group_name}/hosts/{host_name}/connection-test",
        ),
        (
            "POST",
            "/api/projects/{project_name}/managed-inventories/{filename}/groups/{group_name}/connection-test",
        ),
        ("POST", "/api/projects/{project_name}/managed-inventories/{filename}/connection-test"),
    ]

    for method, path in expected_routes:
        assert count_routes(method, path) == 1, f"{method} {path} must not be duplicated"
