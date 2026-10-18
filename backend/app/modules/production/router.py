from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.db.session import get_db_session
from app.modules.machines.exceptions import MachineNotFoundError
from app.modules.production.exceptions import (
    InactiveMachineError,
    InvalidProductionTaskOriginError,
    InvalidProductionTaskTransitionError,
    MachineBusyError,
    ProductionTaskDependencyConflictError,
    ProductionTaskDependencyCycleError,
    ProductionTaskDependencyNotFoundError,
    ProductionTaskNotEditableError,
    ProductionTaskNotFoundError,
    ProductionTaskOriginNotFoundError,
    UnsatisfiedProductionTaskDependenciesError,
)
from app.modules.production.models import ProductionTask
from app.modules.production.schemas import (
    ProductionTaskCreate,
    ProductionTaskDependencyCreate,
    ProductionTaskDependencyRead,
    ProductionTaskRead,
    ProductionTaskUpdate,
)
from app.modules.production.service import ProductionTaskService
from app.modules.production.types import ProductionTaskPriority, ProductionTaskStatus

router = APIRouter(tags=["production-tasks"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
DOMAIN_HTTP_ERRORS = (
    ProductionTaskNotFoundError,
    ProductionTaskOriginNotFoundError,
    MachineNotFoundError,
    InvalidProductionTaskOriginError,
    InvalidProductionTaskTransitionError,
    ProductionTaskNotEditableError,
    InactiveMachineError,
    MachineBusyError,
    PersistenceError,
    ProductionTaskDependencyConflictError,
    ProductionTaskDependencyCycleError,
    ProductionTaskDependencyNotFoundError,
    UnsatisfiedProductionTaskDependenciesError,
)
FINISH_DESCRIPTION = " ".join(
    ("Marca la ejecución física como terminada;", "no completa calidad ni el origen.")
)


def _translate(error: Exception) -> HTTPException:
    if isinstance(
        error,
        ProductionTaskNotFoundError
        | ProductionTaskOriginNotFoundError
        | ProductionTaskDependencyNotFoundError
        | MachineNotFoundError,
    ):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(
        error,
        InvalidProductionTaskOriginError
        | InvalidProductionTaskTransitionError
        | ProductionTaskNotEditableError
        | InactiveMachineError
        | MachineBusyError
        | ProductionTaskDependencyConflictError
        | ProductionTaskDependencyCycleError
        | UnsatisfiedProductionTaskDependenciesError,
    ):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="No se pudo procesar la tarea de producción",
    )


@router.post(
    "/orders/{order_id}/production-tasks",
    response_model=ProductionTaskRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear tarea para un pedido",
    responses={
        404: {"description": "Origen o máquina inexistente"},
        409: {"description": "Origen o máquina no disponible"},
    },
)
def create_for_order(
    order_id: UUID, payload: ProductionTaskCreate, session: DatabaseSession
) -> ProductionTask:
    try:
        return ProductionTaskService(session).create_for_order(order_id, payload)
    except DOMAIN_HTTP_ERRORS as error:
        raise _translate(error) from error


@router.post(
    "/project-components/{component_id}/production-tasks",
    response_model=ProductionTaskRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear tarea para un componente de proyecto",
    responses={
        404: {"description": "Origen o máquina inexistente"},
        409: {"description": "Origen o máquina no disponible"},
    },
)
def create_for_project_component(
    component_id: UUID, payload: ProductionTaskCreate, session: DatabaseSession
) -> ProductionTask:
    try:
        return ProductionTaskService(session).create_for_project_component(
            component_id, payload
        )
    except DOMAIN_HTTP_ERRORS as error:
        raise _translate(error) from error


@router.get(
    "/production-tasks",
    response_model=list[ProductionTaskRead],
    summary="Listar tareas de producción",
    description="Ordena por prioridad, posición de cola, antigüedad e identificador.",
)
def list_tasks(
    session: DatabaseSession,
    task_status: Annotated[ProductionTaskStatus | None, Query(alias="status")] = None,
    priority: Annotated[ProductionTaskPriority | None, Query()] = None,
    machine_id: Annotated[UUID | None, Query()] = None,
    order_id: Annotated[UUID | None, Query()] = None,
    project_component_id: Annotated[UUID | None, Query()] = None,
    project_id: Annotated[UUID | None, Query()] = None,
) -> list[ProductionTask]:
    return ProductionTaskService(session).list(
        status=task_status,
        priority=priority,
        machine_id=machine_id,
        order_id=order_id,
        project_component_id=project_component_id,
        project_id=project_id,
    )


@router.get(
    "/production-tasks/{task_id}",
    response_model=ProductionTaskRead,
    summary="Consultar tarea de producción",
    responses={404: {"description": "Tarea inexistente"}},
)
def get_task(task_id: UUID, session: DatabaseSession) -> ProductionTask:
    try:
        return ProductionTaskService(session).get(task_id)
    except ProductionTaskNotFoundError as error:
        raise _translate(error) from error


@router.post(
    "/production-tasks/{task_id}/dependencies",
    response_model=ProductionTaskDependencyRead,
    status_code=status.HTTP_201_CREATED,
    summary="Agregar dependencia directa",
    responses={
        404: {"description": "Tarea o prerrequisito inexistente"},
        409: {"description": "Dependencia inválida"},
    },
)
def add_dependency(
    task_id: UUID,
    payload: ProductionTaskDependencyCreate,
    session: DatabaseSession,
) -> ProductionTaskDependencyRead:
    try:
        dependency = ProductionTaskService(session).add_dependency(
            task_id, payload.depends_on_task_id
        )
        return ProductionTaskDependencyRead.model_validate(dependency)
    except DOMAIN_HTTP_ERRORS as error:
        raise _translate(error) from error


@router.get(
    "/production-tasks/{task_id}/dependencies",
    response_model=list[ProductionTaskDependencyRead],
    summary="Listar prerrequisitos directos",
    responses={404: {"description": "Tarea inexistente"}},
)
def list_dependencies(
    task_id: UUID, session: DatabaseSession
) -> list[ProductionTaskDependencyRead]:
    try:
        dependencies = ProductionTaskService(session).get_dependencies(task_id)
        return [
            ProductionTaskDependencyRead.model_validate(value) for value in dependencies
        ]
    except DOMAIN_HTTP_ERRORS as error:
        raise _translate(error) from error


@router.delete(
    "/production-tasks/{task_id}/dependencies/{depends_on_task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar dependencia directa",
    responses={
        404: {"description": "Tarea o dependencia inexistente"},
        409: {"description": "El grafo ya no es editable"},
    },
)
def remove_dependency(
    task_id: UUID,
    depends_on_task_id: UUID,
    session: DatabaseSession,
) -> Response:
    try:
        ProductionTaskService(session).remove_dependency(task_id, depends_on_task_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except DOMAIN_HTTP_ERRORS as error:
        raise _translate(error) from error


@router.patch(
    "/production-tasks/{task_id}",
    response_model=ProductionTaskRead,
    summary="Actualizar campos editables de una tarea",
    responses={
        404: {"description": "Tarea o máquina inexistente"},
        409: {"description": "Estado o máquina no disponible"},
    },
)
def update_task(
    task_id: UUID, payload: ProductionTaskUpdate, session: DatabaseSession
) -> ProductionTask:
    try:
        return ProductionTaskService(session).update(
            task_id, payload.model_dump(exclude_unset=True)
        )
    except DOMAIN_HTTP_ERRORS as error:
        raise _translate(error) from error


def _action(
    task_id: UUID,
    action: Literal["start", "pause", "resume", "finish", "cancel"],
    session: Session,
) -> ProductionTask:
    service = ProductionTaskService(session)
    try:
        if action == "start":
            return service.start(task_id)
        if action == "pause":
            return service.pause(task_id)
        if action == "resume":
            return service.resume(task_id)
        if action == "finish":
            return service.finish(task_id)
        return service.cancel(task_id)
    except DOMAIN_HTTP_ERRORS as error:
        raise _translate(error) from error


@router.post(
    "/production-tasks/{task_id}/start",
    response_model=ProductionTaskRead,
    summary="Iniciar tarea",
)
def start_task(task_id: UUID, session: DatabaseSession) -> ProductionTask:
    return _action(task_id, "start", session)


@router.post(
    "/production-tasks/{task_id}/pause",
    response_model=ProductionTaskRead,
    summary="Pausar tarea",
)
def pause_task(task_id: UUID, session: DatabaseSession) -> ProductionTask:
    return _action(task_id, "pause", session)


@router.post(
    "/production-tasks/{task_id}/resume",
    response_model=ProductionTaskRead,
    summary="Reanudar tarea",
)
def resume_task(task_id: UUID, session: DatabaseSession) -> ProductionTask:
    return _action(task_id, "resume", session)


@router.post(
    "/production-tasks/{task_id}/finish",
    response_model=ProductionTaskRead,
    summary="Finalizar trabajo físico",
    description=FINISH_DESCRIPTION,
)
def finish_task(task_id: UUID, session: DatabaseSession) -> ProductionTask:
    return _action(task_id, "finish", session)


@router.post(
    "/production-tasks/{task_id}/cancel",
    response_model=ProductionTaskRead,
    summary="Cancelar tarea",
)
def cancel_task(task_id: UUID, session: DatabaseSession) -> ProductionTask:
    return _action(task_id, "cancel", session)
