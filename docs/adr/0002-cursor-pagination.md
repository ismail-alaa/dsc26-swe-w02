# 0002. Use cursor pagination for listParcels

## Status
Accepted

## Context
Parcels can change state while couriers and merchants page through a filtered list. Offset pagination can skip or repeat items when the filtered result set changes between requests.

## Decision
Use opaque cursors that refer to the creation-order position of the last returned parcel. Only cursors issued by this application instance are accepted; unknown cursors return HTTP 400. The next cursor is null when no further matching item exists.

## Consequences
- Pagination continues after the last item returned even when earlier parcels change state.
- Clients cannot jump directly to an arbitrary page number.
- The application keeps issued cursors in memory.
