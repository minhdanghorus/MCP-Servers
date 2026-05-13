from __future__ import annotations


class EmployeeError(Exception):
    """Base exception for all employee-related errors."""


class EmployeeDatabaseError(EmployeeError):
    """Raised when a database operation related to employees fails."""


class EmployeeNotFoundError(EmployeeError):
    """Raised when an employee record cannot be found."""


class DuplicateEmailError(EmployeeError):
    """Raised when attempting to create or update an employee with a duplicate email."""


class InvalidEmployeeDataError(EmployeeError):
    """Raised when provided employee data fails validation."""


class EmployeeForeignKeyError(EmployeeDatabaseError):
    """Raised when a foreign key constraint involving employees is violated."""

