from fastapi.testclient import TestClient

from app.api import create_app
from app.domain import EventType, InvalidTransition, Parcel, ParcelState, apply_event


def client():
    return TestClient(create_app())


def payload(ref="order-1"):
    return {"merchant_ref": ref, "cod_amount_piastres": 2500, "address_text": "12 Nile St"}


def test_domain_dispatch_is_immutable_and_counts_attempt():
    original = Parcel("pcl_x", "ref", 10, "address")
    updated = apply_event(original, EventType.DISPATCH)
    assert original.state == ParcelState.CREATED and original.attempts == 0
    assert updated.state == ParcelState.OUT_FOR_DELIVERY and updated.attempts == 1


def test_domain_rejects_invalid_transition():
    parcel = Parcel("pcl_x", "ref", 10, "address")
    try:
        apply_event(parcel, EventType.DELIVER)
    except InvalidTransition:
        pass
    else:
        raise AssertionError("Expected InvalidTransition")


def test_create_get_and_location():
    c = client()
    response = c.post("/v1/parcels", json=payload())
    assert response.status_code == 201
    parcel = response.json()
    assert set(parcel) == {"id", "merchant_ref", "cod_amount_piastres", "address_text", "state", "attempts"}
    assert parcel["id"].startswith("pcl_")
    assert response.headers["location"] == f"/v1/parcels/{parcel['id']}"
    assert c.get(response.headers["location"]).json() == parcel


def test_duplicate_ref_is_problem_json_and_does_not_create_second_parcel():
    c = client()
    assert c.post("/v1/parcels", json=payload()).status_code == 201
    duplicate = c.post("/v1/parcels", json=payload())
    assert duplicate.status_code == 409
    assert duplicate.headers["content-type"].startswith("application/problem+json")
    assert c.get("/v1/parcels").json()["items"] and len(c.get("/v1/parcels").json()["items"]) == 1


def test_event_transitions_and_invalid_event():
    c = client()
    parcel = c.post("/v1/parcels", json=payload()).json()
    pid = parcel["id"]
    assert c.post(f"/v1/parcels/{pid}/events", json={"type": "dispatch"}).json()["attempts"] == 1
    assert c.post(f"/v1/parcels/{pid}/events", json={"type": "fail"}).json()["state"] == "failed_attempt"
    assert c.post(f"/v1/parcels/{pid}/events", json={"type": "return"}).json()["state"] == "returned"
    invalid = c.post(f"/v1/parcels/{pid}/events", json={"type": "dispatch"})
    assert invalid.status_code == 409
    assert invalid.headers["content-type"].startswith("application/problem+json")


def test_validation_errors_use_problem_json_with_field_locations():
    response = client().post("/v1/parcels", json={"merchant_ref": "x"})
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["status"] == 422
    assert response.json()["errors"]
    assert all("loc" in error and "msg" in error for error in response.json()["errors"])


def test_list_cursor_and_invalid_cursor():
    c = client()
    for i in range(3):
        assert c.post("/v1/parcels", json=payload(f"order-{i}")).status_code == 201
    first = c.get("/v1/parcels?limit=2").json()
    assert len(first["items"]) == 2 and first["next_cursor"]
    second = c.get("/v1/parcels", params={"limit": 2, "cursor": first["next_cursor"]}).json()
    assert len(second["items"]) == 1 and second["next_cursor"] is None
    bad = c.get("/v1/parcels?cursor=not-issued")
    assert bad.status_code == 400
    assert bad.headers["content-type"].startswith("application/problem+json")


def test_app_instances_have_separate_stores():
    c1, c2 = client(), client()
    assert c1.post("/v1/parcels", json=payload()).status_code == 201
    assert c2.get("/v1/parcels").json()["items"] == []


def test_unknown_parcel_is_problem_json():
    response = client().get("/v1/parcels/pcl_missing")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
