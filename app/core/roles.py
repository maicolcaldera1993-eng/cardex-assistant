"""Who is talking: operator or customer.

Streaming diarization gives anonymous labels ("A", "B") that are shaky for the
first turns and "PENDING" on very short ones. Rule: the first speaker with a
final turn is the operator (they answered the phone). PENDING turns inherit the
previous speaker. The operator can swap the roles with one click. In microphone
demo mode there is a single speaker, who is the customer.
"""
from __future__ import annotations

OPERATOR, CUSTOMER = "operator", "customer"


class RoleTracker:
    def __init__(self, single_speaker_role: str | None = None):
        self.single = single_speaker_role          # CUSTOMER in mic demo mode
        self.operator_label: str | None = None
        self.last_label: str | None = None
        self.swapped = False

    def role_for(self, speaker_label: str | None) -> tuple[str, str | None]:
        """Returns (role, resolved_label)."""
        if self.single:
            return self.single, speaker_label
        label = speaker_label
        if label in (None, "", "PENDING", "UNKNOWN"):
            label = self.last_label
        if label is None:
            return OPERATOR if not self.swapped else CUSTOMER, None
        if self.operator_label is None:
            self.operator_label = label
        self.last_label = label
        is_op = (label == self.operator_label) != self.swapped
        return (OPERATOR if is_op else CUSTOMER), label

    def swap(self) -> None:
        self.swapped = not self.swapped
