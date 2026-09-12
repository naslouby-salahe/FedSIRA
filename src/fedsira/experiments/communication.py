from fedsira.domain.models import CommunicationMessageType
from fedsira.domain.types import CommunicationMessageCount


def efficiency_message_counts() -> (
    tuple[
        tuple[CommunicationMessageType, CommunicationMessageCount],
        ...,
    ]
):
    return (
        (CommunicationMessageType.SOURCE_COMMITMENT, 1),
        (CommunicationMessageType.MODEL_DISTRIBUTION, 8),
        (CommunicationMessageType.UPDATE_SUBMISSION, 8),
        (CommunicationMessageType.CAPABILITY_CONTRACT, 1),
        (CommunicationMessageType.REVIEW_ASSIGNMENT, 3),
        (CommunicationMessageType.REVIEW_REPORT, 3),
        (CommunicationMessageType.VERIFIER_ASSIGNMENT, 5),
        (CommunicationMessageType.VERIFIER_REPORT, 5),
        (CommunicationMessageType.FINAL_GATE_ASSIGNMENT, 6),
        (CommunicationMessageType.FINAL_GATE_REPORT, 6),
        (CommunicationMessageType.DECISION, 1),
    )
