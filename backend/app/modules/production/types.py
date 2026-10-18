from enum import StrEnum


class ProductionTaskType(StrEnum):
    FDM_PRINT = "fdm_print"
    SLA_PRINT = "sla_print"
    CNC = "cnc"
    LASER = "laser"
    POSTPROCESSING = "postprocessing"
    ASSEMBLY = "assembly"
    MANUAL = "manual"
    OTHER = "other"


class ProductionTaskStatus(StrEnum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    PHYSICALLY_COMPLETED = "physically_completed"
    CANCELLED = "cancelled"


class ProductionTaskPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
