"""
Standard API Response Format

All endpoints return a consistent response format with:
- status: success/error/warning
- data: response payload (null if error)
- message: human-readable message
- error_code: machine-readable error code (null if success)
"""

from pydantic import BaseModel
from typing import Optional, Any, Generic, TypeVar

T = TypeVar('T')


class APIError(BaseModel):
    """Standard error response"""
    status: str = "error"
    data: Optional[Any] = None
    message: str
    error_code: str


class APISuccess(BaseModel):
    """Standard success response"""
    status: str = "success"
    data: Any
    message: Optional[str] = None
    error_code: Optional[str] = None


class APIResponse(BaseModel):
    """Generic API response"""
    status: str  # success, error, warning
    data: Optional[Any] = None
    message: Optional[str] = None
    error_code: Optional[str] = None


# Error codes for common scenarios
class ErrorCode:
    """Standard error codes for frontend handling"""
    # Authentication
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    EMAIL_ALREADY_EXISTS = "EMAIL_ALREADY_EXISTS"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    UNAUTHORIZED = "UNAUTHORIZED"
    
    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_EMAIL = "INVALID_EMAIL"
    INVALID_PASSWORD = "INVALID_PASSWORD"
    INVALID_ROLE = "INVALID_ROLE"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    
    # Resources
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"
    
    # Access Control
    FORBIDDEN = "FORBIDDEN"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    
    # Business Logic
    APPOINTMENT_CONFLICT = "APPOINTMENT_CONFLICT"
    INVALID_STATUS_TRANSITION = "INVALID_STATUS_TRANSITION"
    ALREADY_PAID = "ALREADY_PAID"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    
    # Server
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


def success_response(data: Any, message: str = "Success", status: str = "success") -> dict:
    """Create a standard success response"""
    return {
        "status": status,
        "data": data,
        "message": message,
        "error_code": None
    }


def error_response(message: str, error_code: str, status: str = "error") -> dict:
    """Create a standard error response"""
    return {
        "status": status,
        "data": None,
        "message": message,
        "error_code": error_code
    }
