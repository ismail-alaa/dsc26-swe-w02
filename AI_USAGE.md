## Tools
Claude and ChatGPT were used to draft and review the domain rules, API handlers, tests, and architecture decision records. I am responsible for running the tests and checking the final behavior before submission.

## What AI got wrong
The first AI-generated draft left this section and both reflection answers as placeholders, so it was not ready to submit. I replaced the placeholders with specific notes and answers. I also ran the included tests locally; all 9 tests passed in this environment.

## In my own words
**Why does listParcels need a cursor rather than an offset?**
A cursor lets the next request continue after the last parcel returned. If parcels change state between requests, the filtered list can shift, so an offset may skip or repeat parcels.

**Which of your four operations would break the courier app if you renamed one field, and who would have to approve that change?**
Renaming a request or response field in any operation could break the courier app because it depends on the API contract. The API owner and the teams responsible for the courier client and other API consumers should agree on a compatible change before it is released.
