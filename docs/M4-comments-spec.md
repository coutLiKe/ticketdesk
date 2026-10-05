# M4 spec: ticket comments (you implement this)

Goal: make `pytest tests/test_comments.py` pass by implementing the two routes in
[`backend/app/routers/comments.py`](../backend/app/routers/comments.py). The schemas
(`CommentCreate`, `CommentRead`), the `is_internal` column, its migration and the router
registration are already done. The tests are the source of truth. This doc explains the intent.

Work on branch `m4-comments`. Commit in small steps (for example: "list comments", then
"hide internal notes from requesters", then "create comment"), then tell me and I'll review.

## What a comment is

A message on a ticket. It has an author, a body, a timestamp and an `is_internal` flag.
**Internal notes** are for staff (technician, admin) only. Requesters must never see them
or create them.

## POST /tickets/{ticket_id}/comments

| Situation | Result |
|---|---|
| Not logged in | 401 |
| Ticket doesn't exist, or the user can't see it (requester, not their ticket) | 404 |
| Ticket is closed | 409 |
| Requester sends `is_internal: true` | 403, nothing saved |
| Invalid body (empty, blank, over 5000 chars, missing; `is_internal` not a boolean) | 422 |
| Otherwise | 201 and the new comment |

Rules:
- Anyone who can see the ticket can comment: its requester, any technician, any admin.
- The author is **always the logged-in user**. Ignore any `author_id` in the request.
- `is_internal` defaults to `false`.
- Commenting is allowed on `open`, `in_progress` and `resolved` tickets.

## GET /tickets/{ticket_id}/comments

| Situation | Result |
|---|---|
| Not logged in | 401 |
| Ticket doesn't exist, or the user can't see it | 404 |
| Otherwise | 200 and a list (possibly empty) |

Rules:
- **Staff** get every comment. **Requesters** get only comments where `is_internal` is false.
- Oldest first. Several comments can share one `created_at`, so add a tie-breaker.
- Only comments for the requested ticket.
- Reading is allowed on closed tickets.

## Questions to think through (I'll ask you about these in review)

1. Which check comes first: "does the ticket exist and may I see it?", "is it closed?" or
   "may I post an internal note?" Does the order change what a requester can learn about a
   ticket that isn't theirs?
2. Where should the "hide internal notes from requesters" rule live, so you can't forget it?
   Think about what would happen if a future endpoint also returned comments.
3. Filtering in SQL or in Python after loading? What changes for a ticket with 10,000 comments?
4. 403 or silently ignoring `is_internal: true` from a requester? Which is better, and why?
5. Does your list query cause an N+1 (one extra query per comment for the author)?

## Where to look in the existing code

- `routers/tickets.py`: `get_visible_ticket` already implements "404 if you can't see it". Reuse it.
- `deps.py`: `CurrentUser`, `DbSession`.
- `models.py`: `Comment`, `User.is_staff`.
- `tests/conftest.py`: the `make_comment` fixture builds comments directly in the DB.

## How to run

```bash
cd backend
.venv/bin/pytest tests/test_comments.py -q        # your spec
.venv/bin/pytest -q                               # everything must stay green
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

## Done means

- All tests in `tests/test_comments.py` pass, and the full suite passes.
- Ruff lint and format pass.
- You can explain every line to someone else.
- You did not edit the tests to make them pass. If you think a test is wrong, tell me why
  and we'll decide together.
