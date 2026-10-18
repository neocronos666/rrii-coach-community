class PersistenceError(RuntimeError):
    """Error técnico de persistencia sin detalles sensibles."""


class SettingNotFoundError(PersistenceError):
    """No existe una configuración técnica con la clave solicitada."""
