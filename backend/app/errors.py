"""Domain exceptions shared by commands and the HTTP layer.

Business rules raise `BusinessError` (like the PoC). Authorization raises
`NotFound` (no existence disclosure for external roles) or `Forbidden`."""
from __future__ import annotations


class DomainError(Exception):
    """Base class for domain-level errors that map to an HTTP status."""

    status = 500


class NotFound(DomainError):
    status = 404


class Forbidden(DomainError):
    status = 403


class BusinessError(DomainError):
    """Typed business error (BR rules). ``code`` mirrors the PoC error vocabulary."""

    status = 409

    def __init__(self, code: str, detail: object = None):
        super().__init__(code)
        self.code = code
        self.detail = detail
