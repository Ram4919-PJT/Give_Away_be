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


class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=409)