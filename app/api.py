"""HTTP API for Tawseel parcels."""
import secrets
from http import HTTPStatus
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain import EventType, InvalidTransition, Parcel, ParcelState, apply_event

PROBLEM = "application/problem+json"


class ParcelIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    merchant_ref: Annotated[StrictStr, Field(min_length=1, max_length=64)]
    cod_amount_piastres: Annotated[StrictInt, Field(ge=0, le=5_000_000)]
    address_text: Annotated[StrictStr, Field(min_length=1, max_length=500)]


class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: EventType


class ParcelOut(BaseModel):
    id: str
    merchant_ref: str
    cod_amount_piastres: int
    address_text: str
    state: ParcelState
    attempts: int


class ParcelPage(BaseModel):
    items: list[ParcelOut]
    next_cursor: str | None


def _out(parcel: Parcel) -> ParcelOut:
    return ParcelOut(
        id=parcel.id,
        merchant_ref=parcel.merchant_ref,
        cod_amount_piastres=parcel.cod_amount_piastres,
        address_text=parcel.address_text,
        state=parcel.state,
        attempts=parcel.attempts,
    )


def _problem(status: int, title: str, detail: str | None = None, **extra) -> JSONResponse:
    body = {"type": "about:blank", "title": title, "status": status}
    if detail:
        body["detail"] = detail
    body.update(extra)
    return JSONResponse(body, status_code=status, media_type=PROBLEM)


def _doc(description: str) -> dict:
    return {
        "description": description,
        "content": {
            PROBLEM: {
                "schema": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "title": {"type": "string"},
                        "status": {"type": "integer"},
                        "detail": {"type": "string"},
                        "errors": {"type": "array", "items": {"type": "object"}},
                    },
                    "required": ["type", "title", "status"],
                }
            }
        },
    }


def create_app() -> FastAPI:
    api = FastAPI(title="Tawseel Parcel API", version="1.0.0")
    store: dict[str, Parcel] = {}
    order: list[str] = []
    refs: set[str] = set()
    # Cursor token -> creation-order index of the last item returned.
    cursors: dict[str, int] = {}

    @api.exception_handler(RequestValidationError)
    async def on_validation(request, exc: RequestValidationError):
        errors = []
        seen: set[tuple] = set()
        for error in exc.errors():
            loc = tuple(error.get("loc", ()))
            if loc in seen:
                continue
            seen.add(loc)
            errors.append({"loc": list(loc), "msg": error.get("msg", "Invalid value")})
        return _problem(422, "Unprocessable Entity", "Request validation failed", errors=errors)

    @api.exception_handler(StarletteHTTPException)
    async def on_http(request, exc: StarletteHTTPException):
        try:
            title = HTTPStatus(exc.status_code).phrase
        except ValueError:
            title = "Error"
        return _problem(exc.status_code, title, str(exc.detail))

    @api.post(
        "/v1/parcels", operation_id="createParcel", status_code=201,
        response_model=ParcelOut,
        responses={409: _doc("Duplicate merchant_ref"), 422: _doc("Invalid body")},
    )
    def create_parcel(body: ParcelIn, response: Response):
        if body.merchant_ref in refs:
            raise HTTPException(409, "merchant_ref already exists")
        # IDs are unique within this app instance and use the required prefix.
        parcel_id = f"pcl_{secrets.token_hex(8)}"
        while parcel_id in store:
            parcel_id = f"pcl_{secrets.token_hex(8)}"
        parcel = Parcel(parcel_id, body.merchant_ref, body.cod_amount_piastres, body.address_text)
        store[parcel_id] = parcel
        order.append(parcel_id)
        refs.add(body.merchant_ref)
        response.headers["Location"] = f"/v1/parcels/{parcel_id}"
        return _out(parcel)

    @api.get(
        "/v1/parcels/{parcel_id}", operation_id="getParcel", response_model=ParcelOut,
        responses={404: _doc("Parcel not found")},
    )
    def get_parcel(parcel_id: str):
        parcel = store.get(parcel_id)
        if parcel is None:
            raise HTTPException(404, "Parcel not found")
        return _out(parcel)

    @api.get(
        "/v1/parcels", operation_id="listParcels", response_model=ParcelPage,
        responses={400: _doc("Invalid cursor"), 422: _doc("Invalid state or limit")},
    )
    def list_parcels(
        state: ParcelState | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        cursor: str | None = None,
    ):
        start = 0
        if cursor is not None:
            if cursor not in cursors:
                raise HTTPException(400, "Invalid cursor")
            start = cursors[cursor] + 1

        page: list[Parcel] = []
        last_idx = -1
        has_more = False
        for index in range(start, len(order)):
            parcel = store[order[index]]
            if state is not None and parcel.state != state:
                continue
            if len(page) == limit:
                has_more = True
                break
            page.append(parcel)
            last_idx = index

        next_cursor = None
        if has_more:
            next_cursor = secrets.token_urlsafe(18)
            cursors[next_cursor] = last_idx
        return ParcelPage(items=[_out(parcel) for parcel in page], next_cursor=next_cursor)

    @api.post(
        "/v1/parcels/{parcel_id}/events", operation_id="recordParcelEvent",
        response_model=ParcelOut,
        responses={404: _doc("Parcel not found"), 409: _doc("Invalid transition"), 422: _doc("Unknown or missing event type")},
    )
    def record_event(parcel_id: str, body: EventIn):
        parcel = store.get(parcel_id)
        if parcel is None:
            raise HTTPException(404, "Parcel not found")
        try:
            updated = apply_event(parcel, body.type)
        except InvalidTransition as exc:
            raise HTTPException(409, str(exc)) from exc
        store[parcel_id] = updated
        return _out(updated)

    return api


app = create_app()
