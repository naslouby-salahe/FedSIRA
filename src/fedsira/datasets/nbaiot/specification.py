from fedsira.datasets.nbaiot.schema import (
    NBAIOT_CLASS_ORDER,
    NBAIOT_DOMAIN_ORDER,
    NBAIOT_PRIMARY_PREDICTOR_COUNT,
    NBAIOT_TARGET_CLASS,
)
from fedsira.datasets.specification import DatasetSpecification
from fedsira.domain.enums import DatasetId


def specification() -> DatasetSpecification:
    return DatasetSpecification(
        dataset=DatasetId.N_BAIOT,
        class_tokens=tuple(item.value for item in NBAIOT_CLASS_ORDER),
        domain_ids=tuple(item.value for item in NBAIOT_DOMAIN_ORDER),
        target_class=NBAIOT_TARGET_CLASS.value,
        benign_class="BENIGN",
        supported_class_tokens=tuple(
            item.value for item in NBAIOT_CLASS_ORDER if item is not NBAIOT_TARGET_CLASS
        ),
        expected_predictor_count=NBAIOT_PRIMARY_PREDICTOR_COUNT,
        domain_proxy_semantics="physical device proxy",
        raw_data_relative=DatasetId.N_BAIOT.value,
    )
