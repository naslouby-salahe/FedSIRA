from fedsira.datasets.ciciot2023.schema import (
    BENIGN_LABEL,
    OFFICIAL_EXPECTED_PREDICTOR_COUNT,
    PSEUDO_DOMAIN_COUNT,
    TARGET_LABEL,
)
from fedsira.datasets.specification import DatasetSpecification
from fedsira.domain.enums import DatasetId


def specification() -> DatasetSpecification:
    return DatasetSpecification(
        dataset=DatasetId.CICIOT2023,
        class_tokens=(),
        domain_ids=tuple(f"PSEUDO_DOMAIN_{index}" for index in range(1, PSEUDO_DOMAIN_COUNT + 1)),
        target_class=TARGET_LABEL,
        benign_class=BENIGN_LABEL,
        supported_class_tokens=(),
        expected_predictor_count=OFFICIAL_EXPECTED_PREDICTOR_COUNT,
        domain_proxy_semantics="synthetic hash partition",
        raw_data_relative="CIC_IOT_Dataset2023/CSV",
    )
