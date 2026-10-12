# Testing and Demo Checklist

## API and persistence
- [ ] `GET /health` reports healthy status and database connectivity.
- [ ] Create a session and verify its ID is returned.
- [ ] Send a question with that session ID.
- [ ] Confirm user and assistant messages persist in PostgreSQL.
- [ ] Confirm a separate session does not inherit the first session's history.
- [ ] Verify invalid requests return structured validation errors.
- [ ] Verify missing model, database outage, and empty retrieval are handled.

## Retrieval and answer quality
- [ ] Index transcripts from a clean checkout.
- [ ] Ask a known question and inspect the retrieved excerpts.
- [ ] Check that inline citation IDs correspond to returned sources.
- [ ] Ask an unrelated question and confirm unsupported claims are avoided.
- [ ] Confirm duplicate episodes do not dominate the source list.

## Providers
- [ ] Run the demo with local Ollama and the configured chat model.
- [ ] Test cloud generation with a valid provider key in a private environment.
- [ ] Test missing cloud credentials and document the fallback behavior.
- [ ] Never include real credentials in logs, screenshots, or Git.

## Frontend
- [ ] Start the API and frontend using the documented commands.
- [ ] Submit a question and view the answer and sources.
- [ ] Test follow-up questions and session creation.
- [ ] Check loading, error, and empty states.
- [ ] If artifact preview is implemented, verify HTML isolation and sanitization.

## Submission
- [ ] Review README setup instructions on a fresh terminal.
- [ ] Ensure `.env`, virtual environments, `node_modules`, and generated indexes
  are excluded from Git.
- [ ] Add reproducible automated tests and record their actual results.
- [ ] Record a 2?3 minute demo, including local Ollama and a design trade-off.
