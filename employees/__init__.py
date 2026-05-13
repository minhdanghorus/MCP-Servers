from __future__ import annotations

from .exceptions import (
    DuplicateEmailError,
    EmployeeDatabaseError,
    EmployeeError,
    EmployeeForeignKeyError,
    EmployeeNotFoundError,
    InvalidEmployeeDataError,
)
from .models import Employee
from .services import (
    create_employee,
    delete_employee,
    find_employees_by_role,
    get_employee,
    get_employee_by_email,
    initialize_employees_schema,
    list_departments,
    list_employees,
    list_employees_by_department,
    list_employees_by_manager,
    update_employee,
)

__all__ = [
    "Employee",
    "EmployeeError",
    "EmployeeDatabaseError",
    "EmployeeNotFoundError",
    "DuplicateEmailError",
    "InvalidEmployeeDataError",
    "EmployeeForeignKeyError",
    "initialize_employees_schema",
    "create_employee",
    "get_employee",
    "get_employee_by_email",
    "update_employee",
    "delete_employee",
    "list_employees",
    "list_employees_by_department",
    "list_employees_by_manager",
    "find_employees_by_role",
    "list_departments",
]

