import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from src.models import Department, Employee


def test_cannot_create_department_with_empty_name(client: TestClient):
    response = client.post(
        "/departments/",
        json={"name": ""},
    )

    assert response.status_code == 422
    assert (
        "String should have at least 1 character" in response.json()["detail"][0]["msg"]
    )


def test_cannot_create_department_with_long_name(client: TestClient):
    response = client.post(
        "/departments/",
        json={"name": "a" * 201},
    )

    assert response.status_code == 422
    assert (
        "String should have at most 200 characters"
        in response.json()["detail"][0]["msg"]
    )


def test_cannot_create_department_with_nonexistent_parent_id(client: TestClient):
    response = client.post("/departments/", json={"name": "string", "parent_id": 0})
    assert response.status_code == 404

    response = client.post("/departments/", json={"name": "string", "parent_id": 1})
    assert response.status_code == 404


def test_cannot_create_duplicate_root_department_name(client: TestClient):
    client.post("/departments/", json={"name": "Engineering"})
    response = client.post("/departments/", json={"name": "Engineering"})

    assert response.status_code == 409


def test_cannot_create_duplicate_name_within_same_parent(client: TestClient):
    parent = client.post("/departments/", json={"name": "Engineering"}).json()
    parent_id = parent["id"]

    client.post("/departments/", json={"name": "Backend", "parent_id": parent_id})
    response = client.post(
        "/departments/", json={"name": "Backend", "parent_id": parent_id}
    )

    assert response.status_code == 409


def test_can_create_same_name_in_different_parents(client: TestClient):
    parent_a = client.post("/departments/", json={"name": "Division A"}).json()
    parent_b = client.post("/departments/", json={"name": "Division B"}).json()

    response_a = client.post(
        "/departments/", json={"name": "Backend", "parent_id": parent_a["id"]}
    )
    response_b = client.post(
        "/departments/", json={"name": "Backend", "parent_id": parent_b["id"]}
    )

    assert response_a.status_code == 200
    assert response_b.status_code == 200


def test_cannot_make_department_parent_of_itself_on_update(client: TestClient):
    department = client.post("/departments/", json={"name": "HR"})
    department_id = department.json()["id"]
    response = client.patch(
        f"/departments/{department_id}/",
        json={"parent_id": department_id},
    )

    assert response.status_code == 409
    assert "Circular dependency" in response.json()["detail"]


def test_cannot_make_circular_dependency_on_update(client: TestClient):
    response_a = client.post("/departments/", json={"name": "Department A"})
    response_b = client.post(
        "/departments/",
        json={"name": "Department B", "parent_id": response_a.json()["id"]},
    )
    response_c = client.post(
        "/departments/",
        json={"name": "Department C", "parent_id": response_b.json()["id"]},
    )

    response = client.patch(
        f"/departments/{response_a.json()['id']}/",
        json={"parent_id": response_c.json()["id"]},
    )
    assert response.status_code == 409
    assert "Circular dependency" in response.json()["detail"]



def test_cannot_reassign_to_deleted_department(client: TestClient):
    department = client.post("/departments/", json={"name": "Engineering"}).json()

    response = client.delete(
        f"/departments/{department['id']}/",
        params={"mode": "reassign", "reassign_to_department_id": department["id"]},
    )

    assert response.status_code == 400


def test_delete_cascade_removes_department_descendants_and_employees(
    client: TestClient, session: Session
):
    department_a = client.post("/departments/", json={"name": "A"}).json()
    department_b = client.post(
        "/departments/", json={"name": "B", "parent_id": department_a["id"]}
    ).json()
    department_c = client.post(
        "/departments/", json={"name": "C", "parent_id": department_b["id"]}
    ).json()

    employee_a = client.post(
        f"/departments/{department_a['id']}/employees/",
        json={
            "full_name": "John Doe",
            "position": "Engineer",
            "hired_at": "2024-01-15",
            "department_id": department_a["id"],
        },
    ).json()
    employee_b = client.post(
        f"/departments/{department_b['id']}/employees/",
        json={
            "full_name": "Jane Smith",
            "position": "Designer",
            "department_id": department_b["id"],
        },
    ).json()
    employee_c = client.post(
        f"/departments/{department_c['id']}/employees/",
        json={
            "full_name": "Bob Johnson",
            "position": "Manager",
            "department_id": department_c["id"],
        },
    ).json()

    response = client.delete(
        f"/departments/{department_a['id']}/", params={"mode": "cascade"}
    )

    assert response.status_code == 204
    session.expire_all()
    assert session.get(Employee, employee_a["id"]) is None
    assert session.get(Employee, employee_b["id"]) is None
    assert session.get(Employee, employee_c["id"]) is None
    assert session.get(Department, department_a["id"]) is None
    assert session.get(Department, department_b["id"]) is None
    assert session.get(Department, department_c["id"]) is None


def test_delete_reassign_moves_employees_to_target_and_promotes_children(
    client: TestClient, session: Session
):
    target = client.post("/departments/", json={"name": "Target"}).json()
    department_a = client.post("/departments/", json={"name": "A"}).json()
    department_b = client.post(
        "/departments/", json={"name": "B", "parent_id": department_a["id"]}
    ).json()

    client.post(
        f"/departments/{department_a['id']}/employees/",
        json={
            "full_name": "John Doe",
            "position": "Engineer",
            "hired_at": "2024-01-15",
            "department_id": department_a["id"],
        },
    )
    client.post(
        f"/departments/{department_b['id']}/employees/",
        json={
            "full_name": "Jane Smith",
            "position": "Designer",
            "department_id": department_b["id"],
        },
    )

    response = client.delete(
        f"/departments/{department_a['id']}/",
        params={"mode": "reassign", "reassign_to_department_id": target["id"]},
    )

    assert response.status_code == 204
    session.expire_all()
    assert (
        session.exec(
            select(Employee).where(Employee.department_id == department_a["id"])
        ).one_or_none()
        is None
    )

    assert (
        session.exec(
            select(Employee).where(Employee.department_id == department_b["id"])
        ).one_or_none()
        is not None
    )
    assert (
        session.exec(
            select(Employee).where(Employee.department_id == target["id"])
        ).one_or_none()
        is not None
    )

    department_b_db = session.get(Department, department_b["id"])
    assert department_b_db.parent_id is None  # type: ignore


def test_get_nonexistent_department_returns_404(client: TestClient):
    response = client.get("/departments/999/")
    assert response.status_code == 404


def test_get_department_default_depth_doesnt_show_children(client: TestClient):
    a = client.post("/departments/", json={"name": "A"}).json()
    client.post("/departments/", json={"name": "B", "parent_id": a["id"]}).json()

    data = client.get(f"/departments/{a['id']}/").json()

    assert data["name"] == "A"
    assert "children" not in data


def test_get_department_depth_2_returns_children(client: TestClient):
    a = client.post("/departments/", json={"name": "A"}).json()
    b = client.post("/departments/", json={"name": "B", "parent_id": a["id"]}).json()

    data = client.get(f"/departments/{a['id']}/", params={"depth": 2}).json()

    assert data["children"][0]["name"] == "B"


def test_get_department_employees_are_flattened(client: TestClient):
    a = client.post("/departments/", json={"name": "A"}).json()
    b = client.post("/departments/", json={"name": "B", "parent_id": a["id"]}).json()
    client.post(
        f"/departments/{a['id']}/employees/",
        json={"full_name": "Zara Smith", "position": "CEO", "department_id": a["id"]},
    )
    client.post(
        f"/departments/{b['id']}/employees/",
        json={"full_name": "Alice Johnson", "position": "Engineer", "department_id": b["id"]},
    )

    data = client.get(f"/departments/{a['id']}/", params={"depth": 2}).json()

    names = [e["full_name"] for e in data["employees"]]
    assert names == ["Alice Johnson", "Zara Smith"]
    assert "employees" not in data["children"][0]


def test_get_department_exclude_employees(client: TestClient):
    a = client.post("/departments/", json={"name": "A"}).json()
    client.post(
        f"/departments/{a['id']}/employees/",
        json={"full_name": "Alice", "position": "CEO", "department_id": a["id"]},
    )

    data = client.get(
        f"/departments/{a['id']}/", params={"include_employees": False}
    ).json()

    assert "employees" not in data
