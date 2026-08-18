# Output Format And Portable Presentation

Use this short module whenever Reader's Seat produces or edits a finished
artifact. It selects the output format and provides the portable presentation
baseline for every format.

If the selected format is HTML, load and follow
[html-output.md](html-output.md) before building the artifact. For Feishu/Lark,
Word, Markdown, plain text, slides, or another explicit native format, preserve
that platform's capabilities and do not load HTML-only mechanics merely to
imitate their appearance.

## Output Format Decision

Apply this order before drafting:

1. If the user directly specifies Feishu/Lark, Word, Markdown, plain text,
   slides, HTML, or another format, use that format.
2. If the user asks to edit, append to, or replace an existing artifact, keep
   that artifact's format unless the user requests a conversion.
3. If the user asks for text directly in the conversation rather than a
   document artifact, return chat text.
4. Otherwise, create a self-contained HTML document.

Do not infer a non-HTML format merely from the source location. Summarizing a
Feishu source into a new report defaults to HTML; editing or adding content to
that Feishu document preserves Feishu. Record whether the selected format came
from an explicit request, an existing editable target, a chat-only request, or
the HTML default.

## Portable Presentation Baseline

Apply these principles to every finished artifact, including explicitly
requested non-HTML formats:

- Use a clear first-screen or opening hierarchy: title, practical takeaway,
  essential support, then detail.
- Use content-bearing headings that expose the document's reasoning path.
- Use restrained solid surfaces, functional color roles, readable typography,
  consistent spacing, and enough whitespace to separate ideas.
- Keep cards for repeated or bounded items; do not turn every section into a
  card or place cards inside cards.
- Use tables, callouts, charts, and diagrams only when they reduce reading,
  comparison, or reasoning effort.
- Keep figure titles, captions, source notes, uncertainty, and visual status
  close to the content they qualify.
- Make long terms, URLs, tables, code, and labels fit the target reading surface.
- Preserve accessible contrast and never communicate meaning through color alone.

Use [visual-decision.md](visual-decision.md) to decide whether a material visual
form is warranted. When one is retained or reviewed, load
[visual-communication.md](visual-communication.md) to govern chart integrity,
color semantics, scenario fit, and rendering. This portable baseline governs
how the chosen form is rendered in the target format.

For Feishu/Lark, use native headings, callouts, tables, drawings, and source
links. For Word, use document styles and native tables. For Markdown or plain
text, express hierarchy through concise headings, spacing, lists, and source
placement. Preserve the principles, not the HTML implementation.

Do not apply HTML-only requirements to other formats: no HTML marker, local
font directory, JavaScript runtime, CSS class, browser viewport check, or HTML
validator is required. Verify the actual target artifact using the strongest
native inspection available.

## Exit Check

Record one selected format and its source: explicit request, existing target,
chat-only request, or HTML default. Do not draft a finished artifact until this
decision is complete. Load [html-output.md](html-output.md) only for HTML.
