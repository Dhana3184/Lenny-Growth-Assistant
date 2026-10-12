# Design Notes

## Interaction principles
- Keep the main chat flow simple: ask a question, read the answer, inspect
  sources, and continue within the same session.
- Make the active model/provider visible in the interface or settings.
- Keep loading and error states clear; do not silently discard failed requests.
- Display source episode titles and links alongside generated answers.
- Separate generated artifacts from the conversation where the artifact viewer
  is available.

## Answer quality
Answers should distinguish transcript evidence from interpretation, use inline
citations, avoid fabricated quotations, and acknowledge missing evidence.
The presence of a source link alone does not prove that every claim is
supported; source excerpts should be checked.

## Artifact safety
Treat model-generated HTML as untrusted. Sanitize HTML and restrict scripts,
navigation, forms, and external resource loading. Prefer a sandboxed iframe
with restrictive permissions. Do not render raw generated HTML in the main
application DOM.

## Accessibility and resilience
Use readable contrast, keyboard-accessible controls, descriptive labels,
visible focus, and useful empty/error states. Avoid exposing stack traces,
database credentials, or provider secrets to the browser.
