from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


ALLOWED_EMPLOYEE_STATUSES: set[str] = {
    "active",
    "inactive",
    "terminated",
    "on_leave",
}


class EmployeeBase(BaseModel):
    name: str
    email: EmailStr
    status: str
    salary: float
    department_id: Optional[int] = None
    manager_id: Optional[int] = None
    phone: Optional[str] = None
    role: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name must not be empty.")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in ALLOWED_EMPLOYEE_STATUSES:
            allowed = ", ".join(sorted(ALLOWED_EMPLOYEE_STATUSES))
            raise ValueError(f"Status must be one of: {allowed}.")
        return value

    @field_validator("salary")
    @classmethod
    def validate_salary(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Salary must be non-negative.")
        return value


class Employee(EmployeeBase):
    id: int
    created_at: datetime
    updated_at: datetime


class EmployeeCreate(EmployeeBase):
    """Model used for validating data when creating or updating employees."""

