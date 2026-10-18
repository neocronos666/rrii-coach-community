class ProductionTaskNotFoundError(Exception):
    pass


class ProductionTaskOriginNotFoundError(Exception):
    pass


class InvalidProductionTaskTransitionError(Exception):
    pass


class ProductionTaskNotEditableError(Exception):
    pass


class InactiveMachineError(Exception):
    pass


class MachineBusyError(Exception):
    pass


class InvalidProductionTaskOriginError(Exception):
    pass


class ProductionTaskDependencyNotFoundError(Exception):
    pass


class ProductionTaskDependencyConflictError(Exception):
    pass


class ProductionTaskDependencyCycleError(Exception):
    pass


class UnsatisfiedProductionTaskDependenciesError(Exception):
    pass
