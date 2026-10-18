import pytest

from app.modules.recipes.action_templates import (
    ActionTemplateError,
    render_action,
    template_parts,
)


@pytest.mark.parametrize(
    "template",
    [
        "{unknown}",
        "{}",
        "{0}",
        "{piece.name}",
        "{piece[0]}",
        "{piece!r}",
        "{piece:>10}",
        "{piece:{quantity}}",
        "{piece",
        "piece}",
    ],
)
def test_templates_reject_unknown_fields_and_scripting(template: str) -> None:
    with pytest.raises(ActionTemplateError):
        template_parts(template)


def test_sentences_are_complete_and_can_reorder_context() -> None:
    values = {
        "piece": "brazo derecho",
        "product": "Hulk",
        "design": "Gaucho",
        "quantity": "2,5",
    }
    assert (
        render_action("Lijar {piece} de {product}", values)
        == "Lijar brazo derecho de Hulk"
    )
    assert (
        render_action("{product}: sand {piece}", values) == "Hulk: sand brazo derecho"
    )
    assert (
        render_action("Preparar {quantity} de {design}", values)
        == "Preparar 2,5 de Gaucho"
    )


def test_escaped_braces_and_context_are_not_reinterpreted() -> None:
    assert (
        render_action("{{Referencia}}: {piece}; {piece}", {"piece": "{product}"})
        == "{Referencia}: {product}; {product}"
    )
    assert render_action("Dejar secar", {}) == "Dejar secar"


def test_missing_context_does_not_generate_incomplete_instruction() -> None:
    with pytest.raises(ActionTemplateError, match="piece, product"):
        render_action("Lijar {piece} de {product}", {})
