# app/core/exceptions.py

class AppException(Exception):
    """Base exception para todo el proyecto."""

class ConfigError(AppException):
    """Error de configuración o variables de entorno."""

class ScraperError(AppException):
    """Error en el scraping de datos."""

class PipelineError(AppException):
    """Error en procesamiento/limpieza de datos."""
