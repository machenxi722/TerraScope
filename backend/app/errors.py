class DomainError(Exception):
    def __init__(self, status: int, code: str, message: str, field_errors=None):
        self.status = status
        self.code = code
        self.message = message
        self.field_errors = field_errors or []


def require(condition, status, code, message):
    if not condition:
        raise DomainError(status, code, message)
