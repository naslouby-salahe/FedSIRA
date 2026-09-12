import pytest

from fedsira.protocol.attacks import (
    declared_source_backdoor_poison_fractions,
    validate_declared_source_backdoor_poison_fraction,
)


def test_declared_poison_sweep_comes_from_configuration() -> None:
    from fedsira.runtime import current_application_context

    declared = current_application_context().scientific_config.attacks_and_boundaries
    backdoor = declared.hidden_source_backdoor
    assert declared_source_backdoor_poison_fractions() == backdoor.poison_fraction_sweep
    assert backdoor.confirmatory_poison_fraction in declared_source_backdoor_poison_fractions()


def test_every_declared_poison_fraction_is_admissible() -> None:
    for fraction in declared_source_backdoor_poison_fractions():
        validate_declared_source_backdoor_poison_fraction(fraction)


def test_an_undeclared_poison_fraction_is_rejected() -> None:
    with pytest.raises(ValueError, match="not one of the declared robustness sweep fractions"):
        validate_declared_source_backdoor_poison_fraction(0.02)
