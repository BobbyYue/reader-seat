# Visual Evidence Protocol

Use this module whenever a document selects, generates, replaces, captions, or publishes a photo, illustration, chart, diagram, screenshot, or cover visual. Visuals can assert identity, event, product state, magnitude, chronology, or causality even when the prose does not. Manage those claims with the same rigor as written claims.

## Visual Claim Inventory

Record every candidate or used visual internally:

| Field | Required content |
| --- | --- |
| Asset | File, URL, source block, or generated asset identifier |
| Visual type | Documentary photo, screenshot, chart, diagram, source illustration, or generated concept |
| Apparent claim | What a reasonable reader may believe the visual proves or depicts |
| Origin | Original page, official account, named publisher, photographer, agency, or user-supplied source |
| Context | Person, event, location, product state, and date when material |
| Authenticity | Whether the asset is original, edited, generated, or unknown |
| Decision | `verified`, `contextualized`, `synthetic`, or `rejected` |
| Presentation | Caption, attribution, nearby synthetic label, and alt text |

Do not use a candidate until its decision is recorded. A citation records where an asset was found; it does not by itself verify what the asset depicts.

## Source Hierarchy

Use the highest available level:

1. the original visual supplied in the user's source;
2. an official source controlled by the depicted person, organization, event, or product;
3. a named photographer, agency, or reputable publisher that identifies the creator and context;
4. a secondary publisher whose caption links or attributes the asset to a traceable original source.

Search-result previews, aggregator pages, copied captions, filenames, alt text, and unlabeled social reposts are discovery clues only. If the chain stops there, reject the visual for identity- or event-bearing use.

## Mandatory Decision Flow

For every visual:

1. **State the apparent claim**: identify what the reader may infer from the image, not merely what the file is called.
2. **Classify the visual**: documentary, source illustration, screenshot, data visual, diagram, or generated concept.
3. **Trace the origin**: locate the original or best available authoritative source and record creator, date, and context when material.
4. **Verify identity and context**: check that the asset depicts the named person, event, product state, period, and location it will be used to represent.
5. **Check authenticity**: determine whether it is generated, composited, materially edited, or of unknown origin.
6. **Decide**:
   - `verified`: identity, source, and material context are supported;
   - `contextualized`: the visual is accurate for background or explanation but does not document the specific event;
   - `synthetic`: the visual is generated or conceptual and will be presented as such;
   - `rejected`: origin, identity, context, or authenticity is insufficient or misleading.
7. **Present honestly**: add attribution and context for documentary assets; add a visible nearby label for synthetic assets.
8. **Verify the rendered artifact**: confirm the label, caption, attribution, and alt text remain visible and accurate in the actual output.

No unresolved identity or authenticity question may be converted into a confident caption.

## Real-Person And Real-Event Hard Gate

A real-person portrait is an identity claim. A real-event photo is an event and context claim. Do not use either unless:

- the depicted identity is traceable to the original source, official source, or named photographer, agency, or publisher with provenance;
- the date, event, and setting are not presented in a misleading way;
- material cropping, editing, or generation status is known or disclosed;
- the caption states only what the evidence supports.

Reject the asset when any required identity, origin, authenticity, or context check remains unresolved. Do not use a third-party label, search snippet, or repeated publication as proof. Do not generate a realistic likeness of the named person as a fallback.

## Generated And Conceptual Visuals

When no verified documentary visual is available, use this fallback order:

`verified source visual -> non-person conceptual or structural visual -> no visual`

For generated or conceptual visuals:

- prefer abstract systems, objects, diagrams, or non-person scenes that support comprehension;
- do not imitate the named person, event, product interface, or physical evidence;
- place a clear label next to the visual, such as `AI 生成概念插画，不代表真实人物或事件`;
- do not rely only on a footer, hover text, metadata, or source list to disclose synthetic status;
- do not cite the generated image as evidence for a factual claim.

If a conceptual image adds no understanding, omit it.

## Captions And Attribution

- Write captions as bounded descriptions, not stronger claims than the source supports.
- Name the creator, agency, or source when available and relevant.
- Distinguish `现场照片`, `资料图`, `示意图`, `产品截图`, and `AI 生成概念图`.
- Use alt text to describe visible content and function. Do not use alt text to assert unverified identity or context.
- For external publication, consider license and attribution requirements separately from factual verification. Permission to use an image does not prove its identity, and verified identity does not automatically grant publication rights.

## Final Verification

Before delivery, confirm:

1. every used visual exists and renders in the delivered artifact;
2. every identity-, event-, product-, or data-bearing visual has a traceable source and accurate context;
3. no rejected or unresolved visual remains in the artifact or source list;
4. generated or conceptual status is visible next to the asset;
5. captions, attributions, and alt text do not overstate what the visual proves;
6. visuals do not contradict, exaggerate, or silently extend the prose;
7. charts preserve underlying values, units, scales, denominators, and uncertainty;
8. publication rights and required attribution have been considered when the output will be published.

An asset loading successfully proves only that it renders. It does not prove provenance, identity, context, or authenticity.
