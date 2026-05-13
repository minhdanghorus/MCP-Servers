from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional, TypeVar

from fastmcp import FastMCP

from employees import services
from employees.exceptions import EmployeeDatabaseError

mcp = FastMCP("employee-server")

_T = TypeVar("_T")


def _serialize_employee(employee: Any) -> dict[str, Any]:
    return employee.model_dump(mode="json")


def _with_init_retry(action: Callable[[], _T]) -> _T:
    try:
        return action()
    except EmployeeDatabaseError as exc:
        if "no such table" not in str(exc).lower():
            raise
        services.initialize_employees_schema()
        return action()


@mcp.tool()
def initialize_employees_schema() -> dict[str, Any]:
    """Initialize employee schema and seed demo data when empty."""
    services.initialize_employees_schema()
    return {"ok": True, "message": "Employee schema initialized."}


@mcp.tool()
def create_employee(
    *,
    name: str,
    email: str,
    status: str,
    salary: float,
    department_id: Optional[int] = None,
    manager_id: Optional[int] = None,
    phone: Optional[str] = None,
    role: Optional[str] = None,
) -> dict[str, Any]:
    """Create an employee and return the created record."""

    def _action() -> dict[str, Any]:
        employee = services.create_employee(
            name=name,
            email=email,
            status=status,
            salary=salary,
            department_id=department_id,
            manager_id=manager_id,
            phone=phone,
            role=role,
        )
        return _serialize_employee(employee)

    return _with_init_retry(_action)


@mcp.tool()
def get_employee(employee_id: int) -> dict[str, Any]:
    """Get one employee by id."""

    def _action() -> dict[str, Any]:
        employee = services.get_employee(employee_id)
        return _serialize_employee(employee)

    return _with_init_retry(_action)


@mcp.tool()
def get_employee_by_email(email: str) -> dict[str, Any]:
    """Get one employee by email."""

    def _action() -> dict[str, Any]:
        employee = services.get_employee_by_email(email)
        return _serialize_employee(employee)

    return _with_init_retry(_action)


@mcp.tool()
def update_employee(
    employee_id: int,
    *,
    name: Optional[str] = None,
    email: Optional[str] = None,
    status: Optional[str] = None,
    salary: Optional[float] = None,
    department_id: Optional[int] = None,
    manager_id: Optional[int] = None,
    phone: Optional[str] = None,
    role: Optional[str] = None,
) -> dict[str, Any]:
    """Update an employee and return the updated record."""

    def _action() -> dict[str, Any]:
        fields = {
            "name": name,
            "email": email,
            "status": status,
            "salary": salary,
            "department_id": department_id,
            "manager_id": manager_id,
            "phone": phone,
            "role": role,
        }
        filtered_fields = {k: v for k, v in fields.items() if v is not None}
        employee = services.update_employee(employee_id, **filtered_fields)
        return _serialize_employee(employee)

    return _with_init_retry(_action)


@mcp.tool()
def delete_employee(employee_id: int) -> dict[str, Any]:
    """Delete an employee by id."""

    def _action() -> dict[str, Any]:
        services.delete_employee(employee_id)
        return {"ok": True, "deleted_employee_id": employee_id}

    return _with_init_retry(_action)


@mcp.tool()
def list_employees(
    *,
    status: Optional[str] = None,
    department_id: Optional[int] = None,
    manager_id: Optional[int] = None,
    role: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[dict[str, Any]]:
    """List employees with optional filters."""

    def _action() -> list[dict[str, Any]]:
        employees = services.list_employees(
            status=status,
            department_id=department_id,
            manager_id=manager_id,
            role=role,
            limit=limit,
            offset=offset,
        )
        return [_serialize_employee(employee) for employee in employees]

    return _with_init_retry(_action)


@mcp.tool()
def list_employees_by_department(
    department_id: int,
    *,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[dict[str, Any]]:
    """List employees by department."""

    def _action() -> list[dict[str, Any]]:
        employees = services.list_employees_by_department(
            department_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return [_serialize_employee(employee) for employee in employees]

    return _with_init_retry(_action)


@mcp.tool()
def list_employees_by_manager(
    manager_id: int,
    *,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[dict[str, Any]]:
    """List employees by manager."""

    def _action() -> list[dict[str, Any]]:
        employees = services.list_employees_by_manager(
            manager_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        return [_serialize_employee(employee) for employee in employees]

    return _with_init_retry(_action)


@mcp.tool()
def find_employees_by_role(
    role: str,
    *,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[dict[str, Any]]:
    """List employees by role."""

    def _action() -> list[dict[str, Any]]:
        employees = services.find_employees_by_role(
            role,
            status=status,
            limit=limit,
            offset=offset,
        )
        return [_serialize_employee(employee) for employee in employees]

    return _with_init_retry(_action)


def _initialize_on_startup() -> None:
    services.initialize_employees_schema()


def main() -> None:
    _initialize_on_startup()
    mcp.run()


if __name__ == "__main__":
    main()
