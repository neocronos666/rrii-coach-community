from enum import StrEnum


class RecipeStepKind(StrEnum):
    OPERATION = "operation"
    PRINT = "print"
    SERVICE = "service"
    WAIT = "wait"
