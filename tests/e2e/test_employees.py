import pytest
from fastapi.testclient import TestClient


def test_create_employee_nonexistent_department(client: TestClient):
    response = client.post(
        "/departments/999/employees/",
        json={
            "full_name": "John Doe",
            "position": "Engineer",
            "hired_at": "2024-01-15",
            "department_id": 999,
        },
    )

    assert response.status_code == 404
    assert "999" in response.json()["detail"]


def test_cannot_create_employee_with_no_name(client: TestClient):
    response = client.post(
        "/departments/",
        json={"name": "assembly shop"},
    )

    if response.status_code == 200:
        department_id = response.json()["id"]
        response = client.post(
            f"/departments/{department_id}/employees/",
            json={
                "full_name": "",
                "position": "Engineer",
                "hired_at": "2024-01-15",
                "department_id": department_id,
            },
        )
        assert response.status_code == 422
        assert (
            "String should have at least 1 character"
            in response.json()["detail"][0]["msg"]
        )
