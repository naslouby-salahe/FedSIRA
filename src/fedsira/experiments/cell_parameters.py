from fedsira.datasets.common import DatasetAdapter, Role
from fedsira.domain.enums import (
    AblationVariant,
    AdmissionOpeningMode,
    BaselineIdentity,
    CoreMethodIdentity,
    OpeningMode,
)
from fedsira.domain.models import ScientificCell
from fedsira.domain.types import BooleanValue, DomainId, RequiredReproductionRowCount
from fedsira.experiments.collapse import ResolvedCore
from fedsira.experiments.definitions import MECHANISM_ABLATION_NAME, ablation_opening_mode
from fedsira.protocol.capability_contract import reproduction_evidence_is_adequate
from fedsira.protocol.proposal import supported_role_count, target_role_count
from fedsira.runtime import current_application_context

RESOLVED_FEDSIRA_CORE_METHOD = CoreMethodIdentity.RESOLVED_FEDSIRA_CORE


def opening_mode_for_cell(
    cell: ScientificCell, resolved_core: ResolvedCore | None = None
) -> AdmissionOpeningMode:
    if cell.experiment == MECHANISM_ABLATION_NAME:
        return ablation_opening_mode(AblationVariant(cell.method))
    if cell.method == RESOLVED_FEDSIRA_CORE_METHOD and resolved_core is not None:
        return resolved_core.opening_mode
    if cell.method == OpeningMode.PROPOSAL_ASSISTED:
        return AdmissionOpeningMode.PROPOSAL_ASSISTED
    return AdmissionOpeningMode.CANDIDATE_FREE


def row_requirement(
    cell: ScientificCell, resolved_core: ResolvedCore | None = None
) -> RequiredReproductionRowCount:
    config = current_application_context().scientific_config
    if cell.method == RESOLVED_FEDSIRA_CORE_METHOD and resolved_core is not None:
        return config.protocol.synthesis.committee_size if resolved_core.plurality_survives else 1
    if cell.method in (
        BaselineIdentity.ONE_INDEPENDENT_RETRAIN,
        BaselineIdentity.CLIENT_REVIEW_THEN_ONE_INDEPENDENT_RETRAIN,
    ) or (
        cell.experiment == MECHANISM_ABLATION_NAME
        and cell.method == AblationVariant.ONE_INDEPENDENT_REPRODUCTION
    ):
        return 1
    if cell.method == BaselineIdentity.THREE_ROW_COORDINATE_MEDIAN_ALTERNATIVE or (
        cell.experiment == MECHANISM_ABLATION_NAME
        and cell.method == AblationVariant.GENERIC_THREE_ROW_THRESHOLD
    ):
        return config.baselines.three_row_coordinate_median.row_count
    return config.protocol.synthesis.committee_size


def domain_is_reproduction_adequate(adapter: DatasetAdapter, domain: DomainId) -> BooleanValue:
    config = current_application_context().scientific_config
    return reproduction_evidence_is_adequate(
        target_role_count(adapter, domain, Role.REPRODUCTION),
        supported_role_count(adapter, domain, Role.POST_REFERENCE_REPLAY),
        config.capability_contract.evidence_minima,
    )
