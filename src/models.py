from datetime import datetime, date, timezone
from typing import Annotated
from pydantic import StringConstraints
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import UniqueConstraint, CheckConstraint


class DepartamentBase(SQLModel):
    name: Annotated[
        str, StringConstraints(min_length=1, max_length=200, strip_whitespace=True)
    ]


class DepartmentRead(SQLModel):
    id: int
    name: str
    parent_id: int | None
    created_at: datetime
    employees: list["Employee"] | None = None
    children: list["DepartmentRead"] | None = None


class DepartamentCreate(DepartamentBase):
    parent_id: int | None = None


class DepartmentUpdate(SQLModel):
    name: (
        Annotated[
            str, StringConstraints(min_length=1, max_length=200, strip_whitespace=True)
        ]
        | None
    ) = None
    parent_id: int | None = None


class Department(DepartamentBase, table=True):
    __table_args__ = (
        UniqueConstraint("name", "parent_id"),
        CheckConstraint("id != parent_id", name="department_not_self_parent"),
    )

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    parent_id: int | None = Field(default=None, foreign_key="department.id")

    employees: list["Employee"] = Relationship(back_populates="departament")


class DepartmentDeleteParams(SQLModel):
    mode: str = Field(
        default="cascade",
        title="Mode",
        description='Mode of deletion "cascade" or "reassign"',
    )
    reassign_to_department_id: int | None = Field(
        default=None,
        title="Reassign to department ID",
        description='ID of the department to reassign employees to. Required if mode is "reassign"',
    )


class EmployeeBase(SQLModel):
    full_name: Annotated[
        str, StringConstraints(min_length=1, max_length=200, strip_whitespace=True)
    ]
    position: Annotated[
        str, StringConstraints(min_length=1, max_length=200, strip_whitespace=True)
    ]
    hired_at: date | None = None


class EmployeeCreate(EmployeeBase):
    department_id: int


class Employee(EmployeeBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    department_id: int = Field(foreign_key="department.id")
    departament: Department = Relationship(back_populates="employees")


DepartmentRead.model_rebuild()
