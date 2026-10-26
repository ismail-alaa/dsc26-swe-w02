# 0001. Keep parcel lifecycle rules in the domain module

## Status
Accepted

## Context
Parcel lifecycle rules should be testable without starting an HTTP server and should not be coupled to request handling.

## Decision
Keep `Parcel`, `ParcelState`, `EventType`, and `apply_event` in the pure Python module `app/domain.py`. The API layer calls the domain function and translates invalid transitions into HTTP 409 responses.

## Consequences
- Domain rules can be tested without FastAPI or a database.
- The API layer stays focused on HTTP and storage.
- Domain changes can be reviewed independently from transport changes.
