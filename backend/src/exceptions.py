"""
Excepciones de dominio compartidas por la aplicación.

Usar estas excepciones en los servicios para mapear errores de negocio
a códigos HTTP mediante handlers centralizados en la app.
"""
class DomainError(Exception):
    """Base para errores del dominio."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """Recurso no encontrado -> 404"""


class ConflictError(DomainError):
    """Conflicto de negocio -> 409"""


class DomainValidationError(DomainError):
    """Datos de entrada inválidos o reglas de negocio violadas -> 422"""


class AuthenticationError(DomainError):
    """Credenciales inválidas o token expirado -> 401"""
