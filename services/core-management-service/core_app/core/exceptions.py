class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code


class AuthenticationError(AppError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class AuthorizationError(AppError):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403)


class NotFoundError(AppError):
    def __init__(self, message: str = "Not found"):
        super().__init__(message, status_code=404)


class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=409)


class KycValidationError(AppError):
    def __init__(
        self,
        errors: list[dict[str, str]],
        *,
        code: str = "KYC_VALIDATION_FAILED",
        message: str = "KYC submission is incomplete",
    ):
        self.errors = errors
        self.code = code
        super().__init__(message, status_code=400)


class AssistanceValidationError(AppError):
    def __init__(
        self,
        errors: list[dict[str, str]],
        *,
        code: str = "ASSISTANCE_VALIDATION_FAILED",
        message: str = "Assistance application is incomplete",
    ):
        self.errors = errors
        self.code = code
        super().__init__(message, status_code=400)
