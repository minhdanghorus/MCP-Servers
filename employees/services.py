from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from pydantic import ValidationError

from .database import get_connection, initialize_schema as _initialize_schema
from .exceptions import (
    DuplicateEmailError,
    EmployeeDatabaseError,
    EmployeeError,
    EmployeeForeignKeyError,
    EmployeeNotFoundError,
    InvalidEmployeeDataError,
)
from .models import Employee, EmployeeCreate


# #region agent log
_DEBUG_LOG_PATH = Path("debug-01f101.log")


def _debug_log(*, run_id: str, hypothesis_id: str, location: str, message: str, data: Any) -> None:
    try:
        payload = {
            "sessionId": "01f101",
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(datetime.now(tz=timezone.utc).timestamp() * 1000),
        }
        _DEBUG_LOG_PATH.write_text("", encoding="utf-8") if False else None
        with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        return


def _email_domain(email: str) -> str:
    try:
        return email.split("@", 1)[1].lower()
    except Exception:
        return ""


# #endregion agent log


def initialize_employees_schema() -> None:
    """Public entry point to create the employees schema if needed."""
    try:
        _initialize_schema()
        _seed_demo_data_if_needed()
    except sqlite3.Error as exc:  # pragma: no cover - defensive
        raise EmployeeDatabaseError("Failed to initialize employees schema.") from exc


def _get_or_create_department(cursor: sqlite3.Cursor, *, name: str) -> int:
    cursor.execute("SELECT id FROM departments WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row is not None:
        return int(row["id"])

    cursor.execute("INSERT INTO departments (name) VALUES (?)", (name,))
    department_id = cursor.lastrowid
    if department_id is None:  # pragma: no cover - defensive
        raise EmployeeDatabaseError("Failed to create department.")
    return int(department_id)


def _insert_employee(
    cursor: sqlite3.Cursor,
    *,
    name: str,
    email: str,
    status: str,
    salary: float,
    department_id: int,
    manager_id: Optional[int],
    phone: Optional[str],
    role: Optional[str],
    now: str,
) -> int:
    _debug_log(
        run_id="seed-pre",
        hypothesis_id="H1",
        location="employees/services.py:_insert_employee",
        message="Seeding insert attempt",
        data={
            "emailDomain": _email_domain(email),
            "status": status,
            "departmentId": department_id,
            "managerIdIsNull": manager_id is None,
        },
    )
    try:
        employee_in = EmployeeCreate(
            name=name,
            email=email,
            status=status,
            salary=salary,
            department_id=department_id,
            manager_id=manager_id,
            phone=phone,
            role=role,
        )
    except ValidationError as exc:
        _debug_log(
            run_id="seed-pre",
            hypothesis_id="H1",
            location="employees/services.py:_insert_employee",
            message="Seed validation failed",
            data={
                "emailDomain": _email_domain(email),
                "errorType": type(exc).__name__,
                "errors": exc.errors(include_url=False),
            },
        )
        raise InvalidEmployeeDataError("Invalid demo employee data.") from exc

    sql = """
        INSERT INTO employees (
            name, email, status, salary,
            department_id, manager_id, phone, role,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params: tuple[Any, ...] = (
        employee_in.name,
        employee_in.email,
        employee_in.status,
        employee_in.salary,
        employee_in.department_id,
        employee_in.manager_id,
        employee_in.phone,
        employee_in.role,
        now,
        now,
    )
    cursor.execute(sql, params)
    employee_id = cursor.lastrowid
    if employee_id is None:  # pragma: no cover - defensive
        raise EmployeeDatabaseError("Failed to create employee.")
    return int(employee_id)


def _seed_demo_data_if_needed() -> None:
    """Seed realistic demo data for local development.

    This is idempotent: it only runs when `employees` is empty, and then
    inserts exactly 9 employees across 2 departments.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM employees LIMIT 1")
        if cursor.fetchone() is not None:
            _debug_log(
                run_id="seed-pre",
                hypothesis_id="H3",
                location="employees/services.py:_seed_demo_data_if_needed",
                message="Seed skipped; employees table not empty",
                data={},
            )
            return

        now = _now_iso()
        _debug_log(
            run_id="seed-pre",
            hypothesis_id="H3",
            location="employees/services.py:_seed_demo_data_if_needed",
            message="Seed starting; employees table empty",
            data={"now": now},
        )

        # Department definitions
        dept_1_name = "Product Engineering"
        dept_2_name = "Operations"
        department_1_id = _get_or_create_department(cursor, name=dept_1_name)
        department_2_id = _get_or_create_department(cursor, name=dept_2_name)
        _debug_log(
            run_id="seed-pre",
            hypothesis_id="H3",
            location="employees/services.py:_seed_demo_data_if_needed",
            message="Departments ready",
            data={
                "department1Id": department_1_id,
                "department2Id": department_2_id,
            },
        )

        # Insert managers first (manager_id must be NULL for them).
        dept_1_manager_id = _insert_employee(
            cursor,
            name="Jordan Kim",
            email="jordan.kim@example.com",
            status="active",
            salary=150000.0,
            department_id=department_1_id,
            manager_id=None,
            phone="555-0101",
            role="Engineering Manager",
            now=now,
        )
        dept_2_manager_id = _insert_employee(
            cursor,
            name="Grace Brooks",
            email="grace.brooks@example.com",
            status="active",
            salary=135000.0,
            department_id=department_2_id,
            manager_id=None,
            phone="555-0201",
            role="Operations Manager",
            now=now,
        )

        # Department 1 employees: 5 total (1 manager + 4 non-managers).
        _insert_employee(
            cursor,
            name="Priya Patel",
            email="priya.patel@example.com",
            status="active",
            salary=125000.0,
            department_id=department_1_id,
            manager_id=dept_1_manager_id,
            phone="555-0102",
            role="Senior Software Engineer",
            now=now,
        )
        _insert_employee(
            cursor,
            name="Ethan Wright",
            email="ethan.wright@example.com",
            status="active",
            salary=118000.0,
            department_id=department_1_id,
            manager_id=dept_1_manager_id,
            phone="555-0103",
            role="Software Engineer",
            now=now,
        )
        _insert_employee(
            cursor,
            name="Sophia Martinez",
            email="sophia.martinez@example.com",
            status="on_leave",
            salary=95000.0,
            department_id=department_1_id,
            manager_id=dept_1_manager_id,
            phone="555-0104",
            role="QA Engineer",
            now=now,
        )
        _insert_employee(
            cursor,
            name="Liam Chen",
            email="liam.chen@example.com",
            status="inactive",
            salary=82000.0,
            department_id=department_1_id,
            manager_id=dept_1_manager_id,
            phone="555-0105",
            role="DevOps Engineer",
            now=now,
        )

        # Department 2 employees: 4 total (1 manager + 3 non-managers).
        _insert_employee(
            cursor,
            name="Noah Johnson",
            email="noah.johnson@example.com",
            status="active",
            salary=98000.0,
            department_id=department_2_id,
            manager_id=dept_2_manager_id,
            phone="555-0202",
            role="Operations Analyst",
            now=now,
        )
        _insert_employee(
            cursor,
            name="Ava Wilson",
            email="ava.wilson@example.com",
            status="active",
            salary=89000.0,
            department_id=department_2_id,
            manager_id=dept_2_manager_id,
            phone="555-0203",
            role="HR Coordinator",
            now=now,
        )
        _insert_employee(
            cursor,
            name="Benjamin Lee",
            email="benjamin.lee@example.com",
            status="terminated",
            salary=76000.0,
            department_id=department_2_id,
            manager_id=dept_2_manager_id,
            phone="555-0204",
            role="Facilities Specialist",
            now=now,
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_employee(row: sqlite3.Row) -> Employee:
    try:
        data = dict(row)
        return Employee(**data)
    except ValidationError as exc:
        raise InvalidEmployeeDataError(
            "Employee data stored in the database is invalid."
        ) from exc


def _handle_integrity_error(action: str, error: sqlite3.IntegrityError) -> None:
    message = str(error)
    if "UNIQUE constraint failed: employees.email" in message:
        raise DuplicateEmailError(
            "An employee with this email already exists."
        ) from error
    if "FOREIGN KEY constraint failed" in message:
        raise InvalidEmployeeDataError(
            "Invalid department_id or manager_id; referenced record does not exist."
        ) from error
    raise EmployeeDatabaseError(
        f"Database integrity error while attempting to {action} employee."
    ) from error


def list_departments() -> list[dict[str, Any]]:
    """Return all departments (id and name), sorted by name."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name FROM departments ORDER BY name COLLATE NOCASE"
            )
            rows = cursor.fetchall()
    except sqlite3.Error as exc:
        raise EmployeeDatabaseError("Database error while listing departments.") from exc

    return [{"id": int(r["id"]), "name": r["name"]} for r in rows]


def create_employee(
    *,
    name: str,
    email: str,
    status: str,
    salary: float,
    department_id: Optional[int] = None,
    department_name: Optional[str] = None,
    manager_id: Optional[int] = None,
    phone: Optional[str] = None,
    role: Optional[str] = None,
) -> Employee:
    """Create a new employee record.

    If ``department_id`` is set, it is used as-is. Otherwise, if ``department_name``
    is a non-empty string, the department row is looked up or created and that id
    is used. If neither is set, ``department_id`` is stored as NULL.
    """
    now = _now_iso()
    sql = """
        INSERT INTO employees (
            name, email, status, salary,
            department_id, manager_id, phone, role,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            if department_id is not None:
                resolved_department_id: Optional[int] = department_id
            elif department_name is not None and department_name.strip():
                resolved_department_id = _get_or_create_department(
                    cursor, name=department_name.strip()
                )
            else:
                resolved_department_id = None

            try:
                employee_in = EmployeeCreate(
                    name=name,
                    email=email,
                    status=status,
                    salary=salary,
                    department_id=resolved_department_id,
                    manager_id=manager_id,
                    phone=phone,
                    role=role,
                )
            except ValidationError as exc:
                raise InvalidEmployeeDataError("Invalid employee data.") from exc

            params: tuple[Any, ...] = (
                employee_in.name,
                employee_in.email,
                employee_in.status,
                employee_in.salary,
                employee_in.department_id,
                employee_in.manager_id,
                employee_in.phone,
                employee_in.role,
                now,
                now,
            )
            cursor.execute(sql, params)
            employee_id = cursor.lastrowid
            cursor.execute("SELECT * FROM employees WHERE id = ?", (employee_id,))
            row = cursor.fetchone()
    except InvalidEmployeeDataError:
        raise
    except sqlite3.IntegrityError as exc:
        _handle_integrity_error("create", exc)
    except sqlite3.Error as exc:
        raise EmployeeDatabaseError("Database error while creating employee.") from exc

    if row is None:  # pragma: no cover - defensive
        raise EmployeeDatabaseError("Failed to retrieve employee after creation.")

    return _row_to_employee(row)


def get_employee(employee_id: int) -> Employee:
    """Retrieve an employee by ID."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM employees WHERE id = ?", (employee_id,))
            row = cursor.fetchone()
    except sqlite3.Error as exc:
        raise EmployeeDatabaseError("Database error while fetching employee.") from exc

    if row is None:
        raise EmployeeNotFoundError(f"Employee with id {employee_id} not found.")

    return _row_to_employee(row)


def get_employee_by_email(email: str) -> Employee:
    """Retrieve an employee by email."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM employees WHERE email = ?", (email,))
            row = cursor.fetchone()
    except sqlite3.Error as exc:
        raise EmployeeDatabaseError(
            "Database error while fetching employee by email."
        ) from exc

    if row is None:
        raise EmployeeNotFoundError(f"Employee with email {email!r} not found.")

    return _row_to_employee(row)


_UPDATABLE_FIELDS = {
    "name",
    "email",
    "status",
    "salary",
    "department_id",
    "manager_id",
    "phone",
    "role",
}


def update_employee(employee_id: int, **fields: Any) -> Employee:
    """Partially update an existing employee and return the updated record."""
    # Only keep fields that are allowed to be updated
    update_data = {k: v for k, v in fields.items() if k in _UPDATABLE_FIELDS}

    # Load current state to run validation with merged data
    current = get_employee(employee_id)
    base_data = current.model_dump()
    # Remove fields that are not part of EmployeeCreate
    base_data.pop("id", None)
    base_data.pop("created_at", None)
    base_data.pop("updated_at", None)
    merged_data = {**base_data, **update_data}

    try:
        validated = EmployeeCreate(**merged_data)
    except ValidationError as exc:
        raise InvalidEmployeeDataError("Invalid employee data for update.") from exc

    set_clauses: List[str] = []
    params: List[Any] = []

    for field_name in update_data:
        set_clauses.append(f"{field_name} = ?")
        params.append(getattr(validated, field_name))

    # Always update updated_at
    set_clauses.append("updated_at = ?")
    params.append(_now_iso())

    if not set_clauses:
        # Nothing to update besides updated_at; still perform the timestamp bump.
        set_clauses = ["updated_at = ?"]

    sql = f"UPDATE employees SET {', '.join(set_clauses)} WHERE id = ?"
    params.append(employee_id)

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, tuple(params))
            if cursor.rowcount == 0:
                raise EmployeeNotFoundError(
                    f"Employee with id {employee_id} not found."
                )
    except EmployeeError:
        raise
    except sqlite3.IntegrityError as exc:
        _handle_integrity_error("update", exc)
    except sqlite3.Error as exc:
        raise EmployeeDatabaseError("Database error while updating employee.") from exc

    return get_employee(employee_id)


def delete_employee(employee_id: int) -> None:
    """Delete an employee by ID."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
            if cursor.rowcount == 0:
                raise EmployeeNotFoundError(
                    f"Employee with id {employee_id} not found."
                )
    except EmployeeNotFoundError:
        raise
    except sqlite3.IntegrityError as exc:
        message = str(exc)
        if "FOREIGN KEY constraint failed" in message:
            raise EmployeeForeignKeyError(
                "Cannot delete employee because other records depend on it."
            ) from exc
        raise EmployeeDatabaseError(
            "Database integrity error while deleting employee."
        ) from exc
    except sqlite3.Error as exc:
        raise EmployeeDatabaseError("Database error while deleting employee.") from exc


def list_employees(
    *,
    status: Optional[str] = None,
    department_id: Optional[int] = None,
    manager_id: Optional[int] = None,
    role: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[Employee]:
    """List employees filtered by the provided criteria."""
    conditions: List[str] = []
    params: List[Any] = []

    if status is not None:
        conditions.append("status = ?")
        params.append(status)
    if department_id is not None:
        conditions.append("department_id = ?")
        params.append(department_id)
    if manager_id is not None:
        conditions.append("manager_id = ?")
        params.append(manager_id)
    if role is not None:
        conditions.append("role = ?")
        params.append(role)

    sql = "SELECT * FROM employees"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY id ASC"

    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
        if offset is not None:
            sql += " OFFSET ?"
            params.append(offset)
    elif offset is not None:
        # OFFSET without LIMIT is supported using LIMIT -1
        sql += " LIMIT -1 OFFSET ?"
        params.append(offset)

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
    except sqlite3.Error as exc:
        raise EmployeeDatabaseError("Database error while listing employees.") from exc

    employees: list[Employee] = []
    for row in rows:
        employees.append(_row_to_employee(row))
    return employees


def list_employees_by_department(
    department_id: int,
    *,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[Employee]:
    """Convenience wrapper to list employees for a department."""
    return list_employees(
        status=status,
        department_id=department_id,
        limit=limit,
        offset=offset,
    )


def list_employees_by_manager(
    manager_id: int,
    *,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[Employee]:
    """Convenience wrapper to list employees for a manager."""
    return list_employees(
        status=status,
        manager_id=manager_id,
        limit=limit,
        offset=offset,
    )


def find_employees_by_role(
    role: str,
    *,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[Employee]:
    """Convenience wrapper to list employees by role."""
    return list_employees(
        status=status,
        role=role,
        limit=limit,
        offset=offset,
    )

