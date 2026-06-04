#let report = json(sys.inputs.at("data", default: "../generated/org_report_sample.json"))

#let black = rgb("#000000")
#let ink = rgb("#222222")
#let body-ink = rgb("#3a3a3a")
#let title-weight = 900
#let title-font = "Arial"
#let muted = rgb("#6B7280")
#let line = rgb("#d8d8d8")
#let panel = rgb("#f8f9fa")
#let pale = rgb("#eef6fb")
#let accent = rgb("#185FA5")
#let aps-purple = rgb("#534AB7")
#let navy = rgb("#1F3864")
#let role-skill-fill = rgb("#E1F5EE")
#let ai-skill-fill = rgb("#F3F4F6")
#let low-blue = rgb("#DDECF8")
#let medium-blue = rgb("#A4C9E8")
#let high-blue = rgb("#08A9D9")
#let empty-cell = rgb("#F3F4F6")
#let amber = rgb("#f0a12a")
#let ais-blue = rgb("#185FA5")

#let val(d, key, fallback: none) = d.at(key, default: fallback)
#let percent(v) = str(v) + "%"
#let score(v) = if v == none { "n/a" } else { str(v) }
#let title-case-band(v) = if v == none { "n/a" } else { upper(str(v).slice(0, 1)) + str(v).slice(1) }
#let band-short(v) = if v == "medium" { "Med" } else if v == "high" { "High" } else { "Low" }
#let rounded-score(v) = if v == none { "n/a" } else { str(calc.round(v)) }
#let table-fill(x, y) = if y == 0 { white } else if calc.even(y) { rgb("#FBFCFD") } else { white }
#let priority-color(p) = if p == "high" { high-blue } else if p == "medium" { medium-blue } else { low-blue }
#let priority-text-color(p) = if p == "high" { white } else { ink }
#let priority-accent(p) = if p == "high" { high-blue } else if p == "medium" { medium-blue } else { low-blue }
#let classification-label(item) = val(item, "classification_label", fallback: val(item, "aria_classification_label", fallback: val(item, "classification", fallback: val(item, "aria_classification", fallback: ""))))

#let meta = val(report, "meta", fallback: (:))
#let front = val(report, "front_matter", fallback: (:))
#let exec = val(report, "executive_summary", fallback: (:))
#let snapshot = val(exec, "workforce_snapshot", fallback: (:))
#let company = val(meta, "organisation_name", fallback: "Organisation")
#let cover = val(val(report, "front_matter", fallback: (:)), "cover", fallback: (:))
#let report-date = val(cover, "date_label", fallback: val(meta, "report_date", fallback: ""))
#let report-year = if str(val(meta, "report_date", fallback: "")).len() >= 4 { str(val(meta, "report_date")).slice(0, 4) } else { "2026" }
#let page-w = 190.5mm
#let page-h = 275.17mm
#let page-margin-x = 18mm
#let page-margin-y = 16mm
#let rec-page-margin-x = 15.5mm
#let rec-page-margin-y = 13.8mm
#let rec-text-width = 141mm
#let source-page-footer = context [
  #footer-block()
]
#let footer-block() = [
  #set text(font: title-font, size: 5.8pt, fill: rgb("#a6a6a6"))
  #align(left)[
    #grid(
      columns: (8pt, 1fr),
      gutter: 3pt,
      [#image("../assets/pulsifi-footer-logo.png", width: 7pt)],
      [
        AI Impact Assessment | #company \
        © Pulsifi. All rights reserved. Report generated on #report-date.
      ],
    )
  ]
]

#set document(title: val(val(report, "meta"), "organisation_name", fallback: "Organisation") + " AI Impact Assessment")
#set page(
  width: page-w,
  height: page-h,
  margin: (x: page-margin-x, y: page-margin-y),
  footer: context [
    #footer-block()
  ],
  background: rect(width: 100%, height: 100%, fill: white),
)
#set text(font: title-font, size: 8.8pt, fill: ink, lang: "en")
#set par(justify: false, leading: 0.82em)

#let section-label(label) = {
  text(size: 6.5pt, fill: accent, weight: "bold", tracking: 0.08em)[#upper(label)]
}

#let report-heading(section: "Executive Summary") = [
  #text(font: title-font, size: 7.4pt, weight: "bold", fill: black)[#section]
  #linebreak()
  #text(font: title-font, size: 6.6pt, fill: body-ink)[#company | #val(meta, "organisation_descriptor", fallback: "AI impact assessment")]
  #v(9mm)
]

#let divider(title, subtitle: none, section: "Executive Summary", show-heading: true) = [
  #pagebreak(weak: true)
  #if show-heading [
    #report-heading(section: section)
  ]
  #text(font: title-font, size: 9.2pt, weight: "bold", fill: black)[#title]
  #if subtitle != none [
    #v(1.5mm)
    #text(size: 7pt, fill: body-ink)[#subtitle]
  ]
  #v(7mm)
]

#let prose(body, size: 9.6pt, fill: body-ink) = block(width: 100%)[
  #set par(leading: 0.86em)
  #text(size: size, fill: fill)[#body]
]

#let prose-title(body, size: 12.8pt) = text(font: title-font, size: size, weight: "bold", fill: black)[#body]

#let spaced-bullets(items, size: 9.2pt, gap: 5.8pt) = block(width: 100%)[
  #set par(leading: 1.03em)
  #for (index, item) in items.enumerate() [
    #grid(
      columns: (8pt, 1fr),
      gutter: 5pt,
      [#text(size: size, fill: body-ink)[•]],
      [#text(size: size, fill: body-ink)[#item]],
    )
    #if index < items.len() - 1 [
      #v(gap)
    ]
  ]
]

#let step-badge(number) = box(
  width: 8mm,
  height: 8mm,
  fill: rgb("#0C9BF2"),
  radius: 2pt,
)[
  #align(center + horizon)[#text(size: 6.6pt, fill: white, weight: "bold")[#str(number)]]
]

#let rec-step-badge(number) = box(
  width: 6.4mm,
  height: 6.4mm,
  fill: rgb("#0C9BF2"),
  radius: 1pt,
)[
  #align(center + horizon)[#text(size: 7pt, fill: white, weight: "bold")[#str(number)]]
]

#let approach-step(number, title, body) = block(width: 100%)[
  #grid(
    columns: (11mm, 1fr),
    gutter: 7mm,
    [#step-badge(number)],
    [
      #text(font: title-font, size: 8.2pt, weight: "bold", fill: black)[#title]
      #v(2mm)
      #prose(body, size: 7.8pt, fill: black)
    ],
  )
]

#let visual-divider(title, image-path: "../assets/org-intro-hero.png") = [
  #pagebreak()
  #set page(
    width: page-w,
    height: page-h,
    margin: 0mm,
    footer: none,
    background: rect(width: 100%, height: 100%, fill: white),
  )
  #image(image-path, width: 100%, height: 137mm, fit: "cover")
  #block(width: 100%, height: 138mm, inset: (x: 23mm, y: 18mm), fill: white, above: 0pt, below: 0pt)[
    #v(49mm)
    #if title == "Recommendations & Next Steps" [
      #text(font: title-font, size: 17pt, weight: "bold", fill: body-ink)[Recommendations &]
      #linebreak()
      #text(font: title-font, size: 17pt, weight: "bold", fill: body-ink)[Next Steps]
    ] else [
      #text(font: title-font, size: 17pt, weight: "bold", fill: body-ink)[#title]
    ]
  ]
  #set page(
    width: page-w,
    height: page-h,
    margin: (x: page-margin-x, y: page-margin-y),
    footer: context [
      #footer-block()
    ],
    background: rect(width: 100%, height: 100%, fill: white),
  )
  #pagebreak()
]

#let metric-card(label, value, note: none, color: accent) = box(
  width: 100%,
  height: 18mm,
  inset: (x: 5pt, y: 4.5pt),
  stroke: line,
  fill: white,
  radius: 1pt,
)[ 
  #text(size: 5.6pt, fill: body-ink)[#label]
  #v(2pt)
  #text(size: 10.5pt, weight: "bold", fill: black)[#str(value)]
  #if note != none [
    #v(1pt)
    #text(size: 5.5pt, fill: body-ink)[#note]
  ]
]

#let readiness-dimension(title, body, align-pos: center) = block(width: 100%, height: 18mm)[
  #align(align-pos + horizon)[
    #text(size: 7.2pt, weight: "bold", fill: navy)[#title]
    #v(2pt)
    #text(size: 6.5pt, fill: muted)[#body]
  ]
]

#let readiness-framework() = block(width: 100%, inset: 0pt, stroke: none, fill: white)[
  #image("../assets/ai-readiness-framework-source.png", width: 100%)
]

#let claim-card(title, body, evidence: none) = block(
  stroke: none,
  fill: white,
  inset: 0pt,
  radius: 1pt,
  width: 100%,
)[
  #text(size: 7.6pt, weight: "bold", fill: black)[#title]
  #v(4pt)
  #body
  #if evidence != none [
    #let confidence = val(evidence, "confidence", fallback: "medium")
    #let facts = val(evidence, "source_facts", fallback: ())
    #v(5pt)
    #text(size: 6.5pt, fill: muted)[Confidence: #confidence · Evidence facts: #str(facts.len())]
  ]
]

#let progress-bar(value, color: accent) = {
  let width = if value == none { 0% } else { calc.min(100%, calc.max(0%, value * 1%)) }
  box(width: 28mm, height: 5pt, fill: rgb("#d7eaf7"))[
    #box(width: width, height: 5pt, fill: color)
  ]
}

#let priority-badge(priority, label) = box(inset: (x: 4pt, y: 1.5pt), fill: priority-color(priority), radius: 1pt)[
  #text(size: 5.8pt, fill: priority-text-color(priority), weight: "bold")[#label]
]

#let narrative-paragraph(body, size: 7.6pt) = block(width: 100%)[
  #text(size: size, fill: ink)[#body]
]

#let narrative-claim(item) = val(val(item, "narrative", fallback: (:)), "claim", fallback: "")

#let plain-claim(item) = val(item, "claim", fallback: "")

#let narrative-stack(items, size: 7.6pt, gap: 4pt) = [
  #for (index, item) in items.enumerate() [
    #narrative-paragraph(val(item, "claim", fallback: ""), size: size)
    #if index < items.len() - 1 [
      #v(gap)
    ]
  ]
]

#let priority-legend() = [
  #v(3.5mm)
  #align(center)[
    #grid(
      columns: (auto, auto, auto),
      gutter: 13mm,
      [
        #box(width: 6pt, height: 6pt, fill: low-blue)
        #h(5pt)
        #text(size: 7.2pt, fill: body-ink)[Low Priority]
      ],
      [
        #box(width: 6pt, height: 6pt, fill: medium-blue)
        #h(5pt)
        #text(size: 7.2pt, fill: body-ink)[Medium Priority]
      ],
      [
        #box(width: 6pt, height: 6pt, fill: high-blue)
        #h(5pt)
        #text(size: 7.2pt, fill: body-ink)[High Priority]
      ],
    )
  ]
]

#let role-row(role) = {
  let priority = val(role, "priority", fallback: "low")
  let label = val(role, "aria_classification_label", fallback: val(role, "aria_classification", fallback: ""))
  (
  [
    #val(role, "role_title", fallback: "")
  ],
  [
    #str(val(role, "fte", fallback: 0))
  ],
  [
    #score(val(role, "ais_score")) (#val(role, "ais_band_label", fallback: band-short(val(role, "ais_band", fallback: ""))))
    #progress-bar(val(role, "ais_score"), color: ais-blue)
  ],
  [
    #score(val(role, "aps_score")) (#val(role, "aps_band_label", fallback: band-short(val(role, "aps_band", fallback: ""))))
    #progress-bar(val(role, "aps_score"), color: aps-purple)
  ],
  [
    #priority-badge(priority, label)
  ],
  )
}

#let matrix-cell(cell) = {
  let priority = val(cell, "priority", fallback: "low")
  let count = val(cell, "role_count", fallback: none)
  let is-empty = count == 0
  let color = if is-empty { empty-cell } else { priority-color(priority) }
  let text-color = if is-empty { muted } else { priority-text-color(priority) }
  box(width: 100%, height: 22mm, inset: (x: 5pt, y: 4pt), stroke: white, fill: color, radius: 2pt)[
    #text(size: 6.8pt, weight: "bold", fill: text-color)[#classification-label(cell)]
    #v(2pt)
    #text(size: 9.8pt, weight: "bold", fill: text-color)[#str(val(cell, "role_count", fallback: 0))]
    #v(1pt)
    #text(size: 5.8pt, fill: text-color)[#str(val(cell, "fte", fallback: 0)) FTE]
  ]
}

#let matrix-reference-cell(cell) = {
  let label = classification-label(cell)
  let is-pale = label == "Invest Selectively" or label == "Maintain" or label == "Monitor"
  let is-medium = label == "Adapt"
  let fill-color = if is-pale { low-blue } else if is-medium { medium-blue } else { high-blue }
  let text-color = if is-pale or is-medium { black } else { white }
  box(width: 100%, height: 30mm, inset: (x: 6pt, y: 5pt), stroke: white, fill: fill-color, radius: 4pt)[
    #text(size: 7.4pt, weight: "bold", fill: text-color)[#label]
    #linebreak()
    #text(size: 7.1pt, fill: text-color)[#val(cell, "short_definition", fallback: "")]
    #v(3pt)
    #text(size: 6.8pt, fill: text-color, style: "italic")[#val(cell, "recommended_action", fallback: "")]
  ]
}

#let axis-label(label) = align(center + horizon)[
  #text(size: 5.6pt, fill: body-ink)[#label]
]

#let aria-matrix(cells, reference: false) = {
  let render-cell = if reference { matrix-reference-cell } else { matrix-cell }
  let matrix-rows = if reference { (auto, 30mm, 30mm, 30mm) } else { (auto, 22mm, 22mm, 22mm) }
  grid(
    columns: (19mm, 1fr, 1fr, 1fr),
    rows: matrix-rows,
    gutter: if reference { 5pt } else { 3pt },
    [],
    axis-label("Low AIS (0 - 39)"),
    axis-label("Med AIS (40 - 69)"),
    axis-label("High AIS (70 - 100)"),
    axis-label("High APS\n(70 - 100)"),
    render-cell(cells.at(0)),
    render-cell(cells.at(1)),
    render-cell(cells.at(2)),
    axis-label("Med APS\n(40 - 69)"),
    render-cell(cells.at(3)),
    render-cell(cells.at(4)),
    render-cell(cells.at(5)),
    axis-label("Low APS\n(0 - 39)"),
    render-cell(cells.at(6)),
    render-cell(cells.at(7)),
    render-cell(cells.at(8)),
  )
}

#let skill-row(skill) = {
  let roles-label = str(val(skill, "required_in_roles", fallback: 0)) + " of " + str(val(skill, "total_roles", fallback: 0))
  let frequency = val(skill, "frequency_percent", fallback: 0)
  let kind = if val(skill, "skill_type", fallback: "") == "ai_skill" { "AI" } else { "Role" }
  let fill-color = if kind == "AI" { ai-skill-fill } else { role-skill-fill }
  (
    [
      #box(inset: (x: 4pt, y: 1.5pt), fill: fill-color, radius: 1pt)[#text(size: 5.8pt, weight: "bold", fill: ink)[#kind]]
    ],
    [
      #val(skill, "skill_name", fallback: "")
    ],
    [
      #roles-label
    ],
    [
      #percent(frequency)
      #v(2pt)
      #progress-bar(frequency, color: accent)
    ],
  )
}

#let next-step(step) = block(fill: white, inset: (top: 6pt, bottom: 6pt), width: 100%)[
  #grid(columns: (13mm, 1fr), gutter: 7mm,
    [#text(size: 11pt, weight: "bold", fill: black)[#str(val(step, "step_number", fallback: ""))]],
    [
      #text(size: 8.6pt, weight: title-weight)[#val(step, "title", fallback: "")]
      #v(4pt)
      #text(size: 7.2pt)[#val(val(step, "narrative", fallback: (:)), "claim", fallback: "")]
      #let actions = val(step, "actions", fallback: ())
      #if val(step, "step_number", fallback: 0) != 1 and actions.len() > 0 [
        #for action in actions [
          #v(4.5mm)
          #text(size: 7.2pt)[#val(action, "action", fallback: "")]
        ]
      ]
    ],
  )
]

#let static-rec-step(number, title, paragraphs) = block(fill: white, inset: (top: 6pt, bottom: 6pt), width: 100%)[
  #grid(columns: (6.4mm, 1fr), gutter: 4mm,
    [#rec-step-badge(number)],
    [
      #box(width: rec-text-width)[
        #text(font: title-font, size: 9.8pt, weight: title-weight, fill: black)[#title]
        #v(4mm)
        #for (index, paragraph) in paragraphs.enumerate() [
          #block(width: 100%)[
            #set par(leading: 0.86em)
            #text(size: 9.6pt, fill: black)[#paragraph]
          ]
          #if index < paragraphs.len() - 1 [
            #v(7.5mm)
          ]
        ]
      ]
    ],
  )
]

#let recommendations-heading() = [
  #text(font: title-font, size: 13.4pt, weight: "bold", fill: black)[Recommendations & Next Steps]
  #v(3.2mm)
  #text(size: 10.1pt, fill: body-ink)[Sequenced actions aligned to the organization’s AI readiness journey]
  #v(11.5mm)
]

#set page(
  width: page-w,
  height: page-h,
  margin: 0mm,
  footer: none,
  background: image("../assets/blue-cover-background.png", width: 100%, height: 100%, fit: "cover"),
)
#place(left + top, dx: 14mm, dy: 95mm)[
  #text(size: 6.4pt, fill: white)[AI Impact Assessment | #report-date]
  #v(4mm)
  #text(size: 13.2pt, weight: title-weight, fill: white)[#company - #report-year]
]
#pagebreak()
#set page(
  width: page-w,
  height: page-h,
  margin: (x: page-margin-x, y: page-margin-y),
  footer: context [
    #footer-block()
  ],
  background: rect(width: 100%, height: 100%, fill: white),
)

#let intro = val(front, "introduction", fallback: (:))
#let approach = val(front, "approach", fallback: (:))
#let how = val(front, "how_to_read", fallback: (:))

#place(left + top, dx: -page-margin-x, dy: -page-margin-y)[
  #image("../assets/org-intro-hero.png", width: page-w, height: 70mm, fit: "cover")
]
#v(73mm)
#prose-title[Introduction]
#v(4mm)
#prose(val(intro, "objective", fallback: ""))
#v(7mm)
#prose[The objective of the assessment is not to determine whether roles will be replaced, but to provide a structured view of:]
#v(2mm)
#spaced-bullets(val(intro, "scope_bullets", fallback: ()), size: 9.2pt)
#v(7mm)
#prose(val(intro, "intended_use", fallback: ""))

#pagebreak()
#v(3mm)
#prose-title[Approach]
#v(5mm)
#prose[
  Based on the #text(weight: "bold")[#str(val(snapshot, "roles_assessed", fallback: 0)) roles] that were analysed, the assessment follows a structured, task-based methodology comprising #text(weight: "bold")[three steps].
]
#v(10mm)
#for (index, step) in val(approach, "steps", fallback: ()).enumerate() [
  #approach-step(index + 1, val(step, "title", fallback: ""), val(step, "description", fallback: ""))
  #if index < val(approach, "steps", fallback: ()).len() - 1 [
    #v(11mm)
  ]
]

#pagebreak()
#v(2mm)
#prose-title[How to Read this Report]
#v(5mm)
#prose[The report should be read as a progression from #text(weight: "bold")[impact identification] to #text(weight: "bold")[action prioritisation].]
#v(5mm)
#prose[The Automation Impact Score (AIS) and Augmentation Potential Score (APS) are categorised into three ranges:]
#v(1.8mm)
#spaced-bullets((
  [#text(weight: "bold")[Low (0-39):] Limited exposure to automation or augmentation; work remains largely human-driven],
  [#text(weight: "bold")[Medium (40-69):] Partial exposure; meaningful opportunities for workflow redesign and efficiency gains],
  [#text(weight: "bold")[High (70-100):] Significant exposure; structural changes to the role are likely],
), size: 9.2pt)
#v(5mm)
#prose[The classification against the ARIA framework provides a simplified view of these dynamics, indicating whether a role should be automated, redesigned, invested in, or augmented (refer to the diagram below for a representation of the ARIA framework).]
#v(6mm)
#aria-matrix(val(how, "aria_cell_definitions", fallback: ()), reference: true)
#priority-legend()
#v(5mm)
#text(fill: muted)[#val(how, "closing_sentence", fallback: "")]

#visual-divider("Executive Summary & Findings")

#divider("Workforce Snapshot", subtitle: "Key workforce AI impact indicators across the organisation")

#grid(
  columns: (1fr, 1fr, 1fr, 1fr),
  gutter: 8pt,
  metric-card("Roles Assessed", val(snapshot, "roles_assessed", fallback: 0), color: navy),
  metric-card("Total FTE", val(snapshot, "total_fte", fallback: 0), color: navy),
  metric-card("High Automation Impact", val(snapshot, "high_automation_roles_count", fallback: 0), note: str(val(snapshot, "high_automation_fte", fallback: 0)) + " FTE", color: ais-blue),
  metric-card("High Augmentation Potential", val(snapshot, "high_augmentation_roles_count", fallback: 0), note: str(val(snapshot, "high_augmentation_fte", fallback: 0)) + " FTE", color: aps-purple),
)

#let cells = val(val(exec, "aria_matrix", fallback: (:)), "cells", fallback: ())
#v(7mm)
#aria-matrix(cells)
#priority-legend()

#v(6mm)
#claim-card("Bottom Line", [
  #narrative-paragraph(val(exec, "bottom_line", fallback: ""), size: 7pt)
])

#let cohorts = val(exec, "cohort_findings", fallback: (:))
#pagebreak()
#report-heading()
#narrative-paragraph(narrative-claim(val(cohorts, "high_automation", fallback: (:))), size: 7.3pt)
#v(7mm)
#narrative-paragraph(narrative-claim(val(cohorts, "high_augmentation", fallback: (:))), size: 7.3pt)
#v(7mm)
#narrative-paragraph(plain-claim(val(cohorts, "synthesis", fallback: (:))), size: 7.3pt)

#divider("Implications on Workforce Redesign", subtitle: "Understanding what each cell demands and where the real risks lie")

#aria-matrix(cells)
#priority-legend()
#v(6mm)
#text(size: 7pt, fill: body-ink)[Based on the distribution of roles highlighted on the ARIA matrix above, the following table highlights the potential opportunities, operational and transformation implications for the next 12 months. It outlines priority actions leadership can take to strengthen readiness, capture value from AI-driven transformation, and proactively address areas of vulnerability before they become operational challenges.]
#let implications = val(exec, "workforce_redesign_implications", fallback: ())
#if implications.len() > 0 [
  #v(7mm)
  #table(
    columns: (0.85fr, 1.45fr, 1.45fr, 1.45fr),
    inset: (x: 4pt, y: 5pt),
    stroke: (x, y) => if y == 0 { (bottom: 0.6pt + line) } else { none },
    fill: table-fill,
    table.header([ARIA Cell], [Potential], [Blind Spots], [Next Steps]),
    ..implications.map(i => (
      [
        #priority-badge(val(i, "priority", fallback: "low"), val(i, "aria_cell_label", fallback: val(i, "aria_cell", fallback: "")))
        #v(2pt)
        #text(size: 6pt, fill: muted)[#str(val(i, "role_count", fallback: 0)) roles / #str(val(i, "fte", fallback: 0)) FTE]
      ],
      [#text(size: 5.9pt)[#val(val(i, "potential", fallback: (:)), "claim", fallback: "")]],
      [#text(size: 5.9pt)[#val(val(i, "blind_spots", fallback: (:)), "claim", fallback: "")]],
      [
        #for action in val(i, "next_steps", fallback: ()) [
          #text(size: 5.7pt)[• #val(action, "action", fallback: "")]
          #linebreak()
        ]
      ]
    )).flatten()
  )
]

#divider("Organisation-Wide Skill Priorities", subtitle: "The most frequently required emerging skills across all roles")

#let skills = val(exec, "skill_priorities", fallback: ())
#let top-skills = skills.slice(0, calc.min(5, skills.len()))
#let skill-narrative = val(exec, "skill_priorities_narrative", fallback: ())
#table(
  columns: (0.45fr, 1.75fr, 1fr, 1.1fr),
  inset: (x: 4pt, y: 5pt),
  stroke: (x, y) => if y == 0 { (bottom: 0.6pt + line) } else { none },
  fill: table-fill,
  table.header([Type], [Skill], [Required in Roles], [Frequency (%)]),
  ..top-skills.map(skill-row).flatten()
)

#v(7mm)
#if skill-narrative.len() > 0 [
  #narrative-stack(skill-narrative, size: 7pt, gap: 5mm)
] else [
  #for skill in top-skills [
    #text(size: 11pt, weight: "bold")[#val(skill, "skill_name", fallback: "")]
    #v(1.5pt)
    #narrative-paragraph(val(val(skill, "narrative", fallback: (:)), "claim", fallback: ""))
    #v(5pt)
  ]
]

#divider("Top 5 Roles with Highest Exposure", subtitle: "Roles with the highest AIS and APS scores, for immediate prioritisation")

#let top = val(exec, "top_exposure_roles", fallback: (:))
#let ais-roles = val(top, "highest_ais_roles", fallback: ())
#let aps-roles = val(top, "highest_aps_roles", fallback: ())
#table(
  columns: (1.2fr, 1fr, 1.2fr, 1fr),
  inset: (x: 4pt, y: 6pt),
  stroke: (x, y) => if y == 0 { (bottom: 0.6pt + line) } else { none },
  fill: table-fill,
  table.header([Highest AIS Roles], [AIS], [Highest APS Roles], [APS]),
  ..range(5).map(i => (
    [#val(ais-roles.at(i, default: (:)), "role_title", fallback: "")],
    [
      #progress-bar(val(ais-roles.at(i, default: (:)), "ais_score", fallback: 0), color: ais-blue)
      #h(2pt)
      #rounded-score(val(ais-roles.at(i, default: (:)), "ais_score", fallback: none))
    ],
    [#val(aps-roles.at(i, default: (:)), "role_title", fallback: "")],
    [
      #progress-bar(val(aps-roles.at(i, default: (:)), "aps_score", fallback: 0), color: aps-purple)
      #h(2pt)
      #rounded-score(val(aps-roles.at(i, default: (:)), "aps_score", fallback: none))
    ],
  )).flatten()
)
#v(5mm)
#text(size: 7pt)[#val(val(top, "comparison_narrative", fallback: (:)), "claim", fallback: "")]

#divider("Role Level Breakdown", subtitle: "Overview of all roles alongside their respective AIS, APS and ARIA classification")

#let rows = val(exec, "role_level_breakdown", fallback: ())
#table(
  columns: (1.5fr, 0.45fr, 0.9fr, 0.9fr, 1fr),
  inset: (x: 4pt, y: 5.5pt),
  stroke: (x, y) => if y == 0 { (bottom: 0.6pt + line) } else { none },
  fill: table-fill,
  table.header([Role], [FTE], [AIS], [APS], [Classification]),
  ..rows.map(role-row).flatten()
)
#priority-legend()

#visual-divider("Recommendations & Next Steps")

#set page(
  width: page-w,
  height: page-h,
  margin: (x: rec-page-margin-x, y: rec-page-margin-y),
  footer: context [
    #footer-block()
  ],
  background: rect(width: 100%, height: 100%, fill: white),
)

#recommendations-heading()

#static-rec-step(1, "Assess employee-level readiness", (
  [Conduct an organisation-wide employee readiness assessment to evaluate the extent to which the workforce possesses the behavioural traits and adaptive capabilities required to transition into evolving role requirements. The AI Readiness dimensions applied within this assessment are shaped by leading research and recognised perspectives on AI literacy, workforce transformation, and the future of work, providing a structured basis for evaluating organisational readiness¹. Employees’ readiness is measured across the following dimension below, and the insights generated will directly inform Step 3 by enabling targeted reskilling prioritisation, workforce redeployment planning, and capability investment decisions.],
))
#v(7mm)
#readiness-framework()

#recommendations-heading()
#static-rec-step(2, "Redesign Flagged Roles", (
  [Commission a structured role redesign exercise for all 5 Transition roles: Accounts Payable Clerk, Invoice Processing Officer, Payroll Administrator, Junior GL Accountant, and HR Administrator. For each, determine whether the role can be rescoped to shift task composition toward higher-APS activities, or whether the 37 FTEs should be planned for managed redeployment into Adapt or Optimize roles.],
  [This is a design decision, not a training decision. Assess all 37 FTEs for redeployment readiness within 60 days. Begin automation of statutory calculations, invoice processing, and payroll runs — these are the highest-confidence starting points.],
))
#v(8mm)
#static-rec-step(3, "Invest in Targeted Upskilling", (
  [Build the programme around the four universal AI skills in order of breadth. Start with Critical Output Review and AI-Assisted Decision Making (required across 85% and 62% of roles respectively), and the skills that most directly change how daily work gets done. A workforce that can evaluate what AI produces, know when to trust it, and know when to challenge it is fundamentally more resilient regardless of function.],
  [Add AI Output Interpretation and Communication for roles that present findings and analysis to clients, and Exception Management for roles where automation handles the routine flow and the human must step in when the system cannot resolve an edge case. The return is measurable.],
  [Upskilling is best paired with role redesign. Run this step after Step 1 and 2 to ensure job architectures have been updated and when you have a clearer understanding of the employees in the role the best way they can be upskilled.],
))

#pagebreak()
#recommendations-heading()
#static-rec-step(4, "Reassess and Recalibrate", (
  [Re-run the ARIA assessment at 12 months to measure movement across the matrix. Roles should be shifting directionally: Transition roles should be reducing in headcount through redeployment, Adapt roles should be moving toward Optimize as AI capability builds, and Optimize roles should be extending toward Expand as augmentation tooling matures. Roles that have not moved indicate either insufficient upskilling investment or structural task composition issues that redesign has not resolved.],
  [Establish the reassessment as a standing annual process. The ARIA classification is a snapshot, not a permanent state, and the distribution will shift as AI capability evolves across the industry.],
))

#pagebreak()
#set page(
  width: page-w,
  height: page-h,
  margin: 0mm,
  footer: none,
  background: image("../assets/blue-cover-background.png", width: 100%, height: 100%, fit: "cover"),
)
#block(width: 100%, height: 100%)[]
