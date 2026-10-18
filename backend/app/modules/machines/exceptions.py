class MachineNotFoundError(RuntimeError):
    """No existe la máquina solicitada."""


class CommunityMachineLimitError(RuntimeError):
    """La operación superaría el límite de máquinas activas."""
