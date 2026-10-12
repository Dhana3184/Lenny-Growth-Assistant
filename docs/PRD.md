# Lenny Growth Assistant ? Product Requirements

## Problem
Product builders need practical growth and product insights from Lenny's
Podcast without manually searching hundreds of transcripts. General-purpose
chatbots may give unsupported answers or fail to identify the episode behind
a recommendation.

## Users
- Startup founders researching product-market fit and growth.
- Product managers seeking actionable frameworks.
- Builders who want follow-up questions grounded in podcast material.

## Goals and success measures
- Answer questions using retrieved transcript passages.
- Provide episode/source references and inline citations.
- Preserve separate conversation sessions and their histories.
- Offer a local Ollama demo and a configurable cloud model option.
- Provide useful feedback when retrieval finds insufficient evidence.

Suggested acceptance measures:
- A representative question returns an answer and source metadata.
- Follow-up questions can use their session's conversation history.
- Empty retrieval does not fabricate transcript-based claims.
- API validation and database failures return understandable errors.

## Scope
Included: transcript indexing, semantic retrieval, answer generation,
conversation persistence, API endpoints, web chat, and source display.

Planned or requiring final verification: cloud-provider execution, artifact
sanitization and preview, automated regression coverage, and deployment setup.

## Assumptions and risks
- Transcript availability and metadata quality may vary.
- Local model responses can be slow on consumer hardware.
- Similarity alone does not guarantee that a passage supports a claim.
- Cloud providers require credentials and may incur costs.
- Generated HTML must be sanitized and isolated before preview.

## Trade-offs
A local model improves demo privacy and avoids per-request API costs but may
be slower or less capable. Retrieval limits context size and latency but may
omit relevant passages. Citations improve traceability but must be checked
against the actual supporting excerpts.
