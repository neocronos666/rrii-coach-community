from collections.abc import Mapping
from string import Formatter

PLACEHOLDERS = frozenset({"piece", "design", "product", "quantity"})


class ActionTemplateError(ValueError):
    pass


def template_parts(template: str) -> list[tuple[str, str | None]]:
    """Sólo texto y placeholders nominales; sin acceso a atributos ni formatos."""
    try:
        parsed = list(Formatter().parse(template))
    except ValueError as error:
        raise ActionTemplateError("La plantilla tiene llaves desbalanceadas") from error
    result: list[tuple[str, str | None]] = []
    for literal, field, spec, conversion in parsed:
        if field is not None and (field not in PLACEHOLDERS or spec or conversion):
            raise ActionTemplateError(
                "Sólo se admiten {piece}, {design}, {product} y {quantity}, "
                "sin formatos"
            )
        result.append((literal, field))
    return result


def render_action(template: str, values: Mapping[str, str]) -> str:
    parts = template_parts(template)
    missing = sorted(
        {field for _, field in parts if field is not None and field not in values}
    )
    if missing:
        raise ActionTemplateError("Falta contexto para: " + ", ".join(missing))
    # Las sustituciones se insertan una vez como texto, nunca se reinterpretan.
    return "".join(
        literal + (values[field] if field is not None else "")
        for literal, field in parts
    )
