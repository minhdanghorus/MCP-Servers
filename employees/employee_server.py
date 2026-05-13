from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any, Optional, TypeVar

from fastmcp import FastMCP
from pydantic import TypeAdapter

from . import services
from .exceptions import EmployeeDatabaseError
from .models import EmployeePerformanceRecord

mcp = FastMCP("employee-server")
_PERFORMANCE_FILE = Path(__file__).resolve().parent / "data" / "employee_performance.json"
_PERFORMANCE_ADAPTER = TypeAdapter(list[EmployeePerformanceRecord])
_TOOL_CALL_LOG_FILE = Path(__file__).resolve().parent / "tool_calls.log"

_T = TypeVar("_T")


def _log_tool_call(tool_name: str) -> None:
    print(f"[employee-server] tool called: {tool_name}", file=sys.stderr, flush=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _TOOL_CALL_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _TOOL_CALL_LOG_FILE.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{timestamp} | {tool_name}\n")


def _serialize_employee(employee: Any) -> dict[str, Any]:
    return employee.model_dump(mode="json")


def _load_employee_performance() -> list[dict[str, Any]]:
    if not _PERFORMANCE_FILE.exists():
        raise FileNotFoundError(
            f"Employee performance file not found: {_PERFORMANCE_FILE}"
        )

    try:
        raw = json.loads(_PERFORMANCE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Employee performance JSON is invalid: {_PERFORMANCE_FILE}"
        ) from exc

    records = _PERFORMANCE_ADAPTER.validate_python(raw)
    return [record.model_dump(mode="json") for record in records]


def _with_init_retry(action: Callable[[], _T]) -> _T:
    try:
        return action()
    except EmployeeDatabaseError as exc:
        if "no such table" not in str(exc).lower():
            raise
        services.initialize_employees_schema()
        return action()


@mcp.resource("employees://performance")
def employee_performance_resource() -> list[dict[str, Any]]:
    """Return all employee performance evaluations from JSON."""
    return _load_employee_performance()


@mcp.resource("employees://performance/{employee_id}")
def employee_performance_by_employee_resource(employee_id: str) -> list[dict[str, Any]]:
    """Return employee performance evaluations filtered by employee_id."""
    try:
        parsed_employee_id = int(employee_id)
    except ValueError as exc:
        raise ValueError("employee_id must be an integer.") from exc

    records = _load_employee_performance()
    return [
        record
        for record in records
        if int(record.get("employee_id", -1)) == parsed_employee_id
    ]


@mcp.tool()
def list_employee_performance() -> list[dict[str, Any]]:
    """Return all employee performance evaluations (reviews, ratings, goals).

    Use this for questions about performance reviews, ratings, strengths,
    improvements, or goals for any employee. Same data as MCP resource
    employees://performance.
    """
    _log_tool_call("list_employee_performance")
    return _load_employee_performance()


@mcp.tool()
def get_employee_performance(employee_id: int) -> list[dict[str, Any]]:
    """Return performance evaluations for one employee by employee_id.

    Use after resolving the person's id (e.g. via get_employee or list_employees).
    Same data as MCP resource employees://performance/{employee_id}.
    """
    _log_tool_call("get_employee_performance")
    records = _load_employee_performance()
    return [
        record
        for record in records
        if int(record.get("employee_id", -1)) == employee_id
    ]


@mcp.tool()
def initialize_employees_schema() -> dict[str, Any]:
    """Initialize employee schema and seed demo data when empty."""
    _log_tool_call("initialize_employees_schema")
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
    _log_tool_call("create_employee")

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
    _log_tool_call("get_employee")

    def _action() -> dict[str, Any]:
        employee = services.get_employee(employee_id)
        return _serialize_employee(employee)

    return _with_init_retry(_action)


@mcp.tool()
def get_employee_by_email(email: str) -> dict[str, Any]:
    """Get one employee by email."""
    _log_tool_call("get_employee_by_email")

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
    _log_tool_call("update_employee")

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
    _log_tool_call("delete_employee")

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
    _log_tool_call("list_employees")

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
    _log_tool_call("list_employees_by_department")

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
    _log_tool_call("list_employees_by_manager")

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
    _log_tool_call("find_employees_by_role")

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
