class AppException(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "Internal server error"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.message
        super().__init__(self.message)


class NotFoundError(AppException):
    status_code = 404
    error_code = "NOT_FOUND"
    message = "Resource not found"


class ValidationError(AppException):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    message = "Validation error"


class AuthenticationError(AppException):
    status_code = 401
    error_code = "AUTHENTICATION_ERROR"
    message = "Authentication failed"


class PermissionError(AppException):
    status_code = 403
    error_code = "PERMISSION_ERROR"
    message = "Permission denied"


class ExternalServiceError(AppException):
    status_code = 502
    error_code = "EXTERNAL_SERVICE_ERROR"
    message = "External service error"
