"""Pure domain rules for Tawseel parcels. No web/framework dependencies."""
from dataclasses import dataclass, replace
from enum import StrEnum


class ParcelState(StrEnum):
    CREATED = "created"
    OUT_FOR_DELIVERY = "out_for_delivery"
    FAILED_ATTEMPT = "failed_attempt"
    DELIVERED = "delivered"
    RETURNED = "returned"


class EventType(StrEnum):
    DISPATCH = "dispatch"
    DELIVER = "deliver"
    FAIL = "fail"
    RETURN = "return"


MAX_ATTEMPTS = 3


@dataclass(frozen=True, slots=True)
class Parcel:
    id: str
    merchant_ref: str
    cod_amount_piastres: int
    address_text: str
    state: ParcelState = ParcelState.CREATED
    attempts: int = 0


class InvalidTransition(ValueError):
    """Raised when an event is not valid for a parcel's current state."""


def apply_event(parcel: Parcel, event: EventType) -> Parcel:
    """Return a new parcel with the event applied; never mutate the input."""
    if not isinstance(event, EventType):
        try:
            event = EventType(event)
        except (ValueError, TypeError):
            raise InvalidTransition(f"Unknown event: {event!r}") from None

    if parcel.state == ParcelState.CREATED and event == EventType.DISPATCH:
        return replace(parcel, state=ParcelState.OUT_FOR_DELIVERY, attempts=parcel.attempts + 1)
    if parcel.state == ParcelState.OUT_FOR_DELIVERY and event == EventType.DELIVER:
        return replace(parcel, state=ParcelState.DELIVERED)
    if parcel.state == ParcelState.OUT_FOR_DELIVERY and event == EventType.FAIL:
        return replace(parcel, state=ParcelState.FAILED_ATTEMPT)
    if parcel.state == ParcelState.FAILED_ATTEMPT and event == EventType.DISPATCH:
        if parcel.attempts < MAX_ATTEMPTS:
            return replace(parcel, state=ParcelState.OUT_FOR_DELIVERY, attempts=parcel.attempts + 1)
        raise InvalidTransition("Maximum delivery attempts reached")
    if parcel.state == ParcelState.FAILED_ATTEMPT and event == EventType.RETURN:
        return replace(parcel, state=ParcelState.RETURNED)
    raise InvalidTransition(f"Cannot apply {event.value!r} to parcel in state {parcel.state.value!r}")
