from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from src.dependencies import get_session
from src.models import (
    DepartamentCreate,
    Department,
    DepartmentDeleteParams,
    DepartmentRead,
    DepartmentUpdate,
    Employee,
    EmployeeCreate,
)

router = APIRouter()


def department_exists(session: Session, _id: int) -> bool:
    department = session.get(Department, _id)
    if department:
        return True
    return False


def would_create_cycle(
    session: Session, department_id: int, new_parent_id: int
) -> bool:
    current_id = new_parent_id
    while current_id is not None:
        if current_id == department_id:
            return True
        parent = session.get(Department, current_id)
        current_id = parent.parent_id if parent else None
    return False


@router.post("/departments/")
async def create_department(
    session: Annotated[Session, Depends(get_session)], data: DepartamentCreate
):
    if data.parent_id and not department_exists(session, data.parent_id):
        raise HTTPException(
            status_code=404, detail=f"Parent department {data.parent_id} not found"
        )

    department = Department.model_validate(data)
    session.add(department)
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="A department with this name already exists under the same parent",
        ) from e
    session.refresh(department)
    return department


@router.post("/departments/{id}/employees/")
async def create_employee(
    session: Annotated[Session, Depends(get_session)], data: EmployeeCreate
):
    if not department_exists(session, data.department_id):
        raise HTTPException(
            status_code=404, detail=f"Department {data.department_id} not found"
        )
    employee = Employee.model_validate(data)
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


@router.get("/departments/{department_id}", response_model=DepartmentRead)
async def get_department(
    session: Annotated[Session, Depends(get_session)],
    department_id: Annotated[int, Path(title="The ID of the item to get")],
    depth: Annotated[
        int,
        Query(
            title="Depth",
            description="Maximum depth of nested units in the response",
            ge=1,
            le=5,
        ),
    ] = 1,
    include_employees: Annotated[
        bool,
        Query(
            title="Include employees", description="Include employees in the response"
        ),
    ] = True,
):

    all_employees: list[Employee] = []

    def _load_tree(department: Department, current_depth: int) -> DepartmentRead:
        if include_employees:
            all_employees.extend(
                session.exec(
                    select(Employee).where(Employee.department_id == department.id)
                ).all()
            )
        children = (
            [
                _load_tree(child, current_depth - 1)
                for child in session.exec(
                    select(Department).where(Department.parent_id == department.id)
                ).all()
            ]
            if current_depth > 1
            else None
        )
        return DepartmentRead(
            id=department.id,
            name=department.name,
            parent_id=department.parent_id,
            created_at=department.created_at,
            employees=None,
            children=children,
        )

    department = session.get(Department, department_id)

    if not department:
        raise HTTPException(
            status_code=404, detail=f"Departament with id {department_id} not found"
        )
    result = _load_tree(department, depth)
    result.employees = (
        sorted(all_employees, key=lambda e: e.full_name) if include_employees else None
    )
    return result


@router.patch("/departments/{department_id}")
async def update_department(
    session: Annotated[Session, Depends(get_session)],
    department: DepartmentUpdate,
    department_id: Annotated[int, Path(title="The ID of the item to update")],
):
    department_db = session.get(Department, department_id)
    if not department_db:
        raise HTTPException(
            status_code=404, detail=f"Department with id {department_id} not found"
        )

    if department.parent_id is not None:
        parent = session.get(Department, department.parent_id)
        if not parent:
            raise HTTPException(
                status_code=404,
                detail=f"Parent department {department.parent_id} not found",
            )

        if would_create_cycle(session, department_id, department.parent_id):
            raise HTTPException(status_code=409, detail="Circular dependency detected")

    department_data = department.model_dump(exclude_unset=True)
    department_db.sqlmodel_update(department_data)
    session.add(department_db)
    session.commit()
    session.refresh(department_db)
    return department_db


@router.delete("/departments/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    session: Annotated[Session, Depends(get_session)],
    department_id: Annotated[int, Path(title="The ID of the item to delete")],
    params: Annotated[DepartmentDeleteParams, Query()],
):

    def delete_cascade(department: Department):
        children = session.exec(
            select(Department).where(Department.parent_id == department.id)
        ).all()

        for child in children:
            delete_cascade(child)

        employees = session.exec(
            select(Employee).where(Employee.department_id == department.id)
        ).all()

        for employee in employees:
            session.delete(employee)
        session.delete(department)
        session.commit()
        return

    departament = session.get(Department, department_id)
    if not departament:
        raise HTTPException(
            status_code=404, detail=f"Departament with id {department_id} not found"
        )

    if params.mode == "cascade":
        delete_cascade(departament)
    else:
        if params.reassign_to_department_id is None:
            raise ValueError(
                "reassign_to_department_id is required when mode is 'reassign'"
            )

        if not department_exists(session, params.reassign_to_department_id):
            raise HTTPException(
                status_code=404,
                detail=f"Departament with id {params.reassign_to_department_id} not found",
            )

        if would_create_cycle(session, department_id, params.reassign_to_department_id):
            raise HTTPException(status_code=409, detail="Circular dependency detected")

        employees = session.exec(
            select(Employee).where(Employee.department_id == department_id)
        ).all()
        for employee in employees:
            employee.department_id = params.reassign_to_department_id
        children = session.exec(
            select(Department).where(Department.parent_id == department_id)
        ).all()
        for child in children:
            child.parent_id = params.reassign_to_department_id
        session.commit()

        session.delete(departament)
        session.commit()
        return
