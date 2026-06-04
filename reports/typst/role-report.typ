#let report = json(sys.inputs.at("data", default: "../generated/role_report_sample.json"))

#let ink = rgb("#222222")
#let muted = rgb("#6b6b6b")
#let line = rgb("#d8d8d8")
#let panel = rgb("#f8f9fa")
#let accent = rgb("#00a9e0")
#let teal = rgb("#25b8b4")
#let navy = rgb("#1f2f97")
#let role-red = rgb("#d66b61")
#let amber = rgb("#f0a12a")
#let red = rgb("#25b8b4")
#let green = rgb("#d66b61")

#let val(d, key, fallback: none) = d.at(key, default: fallback)
#let score(v) = if v == none { "n/a" } else { str(v) }
#let category-color(c) = if c == "automatable" { red } else if c == "augmentable" { accent } else { green }
#let skill-label(s) = if val(s, "skill_type", fallback: "") == "ai_skill" { "AI" } else { "Role" }
#let role = val(report, "role_metadata", fallback: (:))
#let company = val(role, "organisation_name", fallback: "CPFB")
#let report-date = val(val(report, "meta", fallback: (:)), "date_label", fallback: val(val(report, "meta", fallback: (:)), "report_date", fallback: ""))
#let fte-label(value) = str(value) + if value == 1 { " FTE" } else { " FTEs" }
#let footer-block() = [
  #set text(font: "Noto Sans", size: 5.8pt, fill: rgb("#a6a6a6"))
  #align(left)[
    #grid(
      columns: (8pt, 1fr),
      gutter: 4pt,
      [#image("../assets/pulsifi-footer-logo.png", width: 7pt)],
      [
        AI Impact Assessment | #company \
        © Pulsifi. All rights reserved. Report generated on #report-date.
      ],
    )
  ]
]

#set document(title: val(val(report, "role_metadata"), "role_title", fallback: "Role") + " AI Impact Assessment")
#set page(
  paper: "a4",
  margin: (x: 18mm, y: 17mm),
  footer: context [
    #footer-block()
  ],
)
#set text(font: "Noto Sans", size: 7.6pt, fill: ink, lang: "en")
#set par(justify: false, leading: 0.55em)

#let meta = val(report, "meta", fallback: (:))
#let scores = val(report, "computed_scores", fallback: (:))
#let narratives = val(report, "narratives", fallback: (:))
#let future = val(val(report, "future_role", fallback: (:)), "task_evolution", fallback: ())
#let skills = val(report, "skills_reference", fallback: ())

#let section-label(label) = text(size: 6.3pt, fill: accent, weight: "bold", tracking: 0.06em)[#upper(label)]
#let role-header() = [
  #text(size: 11pt, weight: "bold")[#val(role, "role_title", fallback: "Role")]
  #v(1pt)
  #text(size: 6.8pt, fill: ink)[#val(role, "department", fallback: "") | #fte-label(val(role, "fte", fallback: 1))]
  #v(7mm)
]

#let divider(title, subtitle: none) = [
  #pagebreak(weak: true)
  #role-header()
  #text(size: 12pt, weight: "bold")[#title]
  #if subtitle != none [
    #v(1.5pt)
    #text(size: 6.8pt, fill: muted)[#subtitle]
  ]
  #v(3mm)
  #std.line(length: 100%, stroke: 0.5pt + line)
  #v(4mm)
]

#let score-card(label, value, band, color) = block(width: 100%, inset: 6pt, stroke: line, fill: white, radius: 2pt)[
  #text(size: 5.5pt, fill: ink)[#label]
  #v(2pt)
  #text(size: 13pt, fill: ink, weight: "bold")[#score(value)]
  #h(4pt)
  #v(2pt)
  #box(width: 100%, height: 3pt, fill: rgb("#e8f4f5"))[
    #box(width: calc.min(100%, calc.max(0%, value * 1%)), height: 3pt, fill: color)
  ]
  #v(1.5pt)
  #text(size: 5.8pt, fill: color)[#str(band)]
]

#let narrative-card(title, narrative) = block(width: 100%, inset: 0pt, stroke: none)[
  #text(size: 7.2pt, fill: accent, weight: "bold")[#title]
  #v(3pt)
  #val(narrative, "claim", fallback: "")
]

#let progress(value, color) = box(width: 100%, height: 4pt, fill: rgb("#edf2f4"))[
  #box(width: calc.min(100%, calc.max(0%, value * 1%)), height: 4pt, fill: color)
]

#let task-row(task) = (
  [#val(task, "task_name", fallback: "")],
  [
    #score(val(task, "ais_score", fallback: 0))
    #progress(val(task, "ais_score", fallback: 0), red)
  ],
  [
    #score(val(task, "aps_score", fallback: 0))
    #progress(val(task, "aps_score", fallback: 0), accent)
  ],
)

#let future-row(task) = (
  [#text(weight: "bold")[#val(task, "task_name", fallback: "")]],
  [#val(task, "how_ai_changes_this", fallback: "") #linebreak() #text(fill: muted)[Human role: #val(task, "human_role_in_future_state", fallback: "")]],
  [
    #for skill in val(task, "skills_applied", fallback: ()) [
      #text(size: 5.8pt, fill: if skill-label(skill) == "AI" { muted } else { role-red }, weight: "bold")[#skill-label(skill)]
      #h(3pt)
      #val(skill, "skill_name", fallback: "")
      #linebreak()
    ]
  ],
)

#let type-chip(kind) = box(inset: (x: 3pt, y: 1.5pt), fill: if kind == "AI" { rgb("#f2f2f2") } else { role-red.lighten(25%) }, radius: 1pt)[#text(size: 5.5pt, fill: if kind == "AI" { muted } else { white }, weight: "bold")[#kind]]

#let skill-row(skill) = (
  [#type-chip(skill-label(skill))],
  [#text(weight: "bold")[#val(skill, "skill_name", fallback: "")]],
  [#val(skill, "description", fallback: "")],
)

#let rec = val(report, "recommendations", fallback: (:))
#let brief = val(report, "consultant_brief", fallback: (:))
#let implementation = val(report, "implementation_plan", fallback: (:))
#let classification_position = upper(val(scores, "ais_band", fallback: "")) + " AIS, " + upper(val(scores, "aps_band", fallback: "")) + " APS"

#let action-row(action) = {
  let affected = val(action, "affected_tasks", fallback: ())
  (
    [
      #type-chip(upper(val(action, "priority", fallback: "medium")))
      #v(2pt)
      #text(size: 5.6pt, fill: muted)[#upper(val(action, "category", fallback: ""))]
    ],
    [#text(weight: "bold")[#val(action, "title", fallback: "")]],
    [#val(action, "description", fallback: "")],
    [
      #if affected.len() == 0 [
        #text(fill: muted)[No task mapping]
      ] else [
        #for task in affected.slice(0, calc.min(2, affected.len())) [
          #text(size: 5.8pt)[#task]
          #linebreak()
        ]
        #if affected.len() > 2 [
          #text(size: 5.8pt, fill: muted)[+#str(affected.len() - 2) more]
        ]
      ]
    ],
  )
}

#let priority-chip(priority) = {
  let normalized = lower(str(priority))
  let fill-color = if normalized == "high" { role-red } else if normalized == "medium" { amber } else { accent.lighten(20%) }
  box(inset: (x: 4pt, y: 1.7pt), fill: fill-color, radius: 1pt)[
    #text(size: 5.6pt, fill: white, weight: "bold")[#upper(str(priority))]
  ]
}

#let task-link-list(action) = {
  let affected = val(action, "affected_tasks", fallback: ())
  if affected.len() == 0 [
    #text(size: 6pt, fill: muted)[No task mapping]
  ] else [
    #for task in affected.slice(0, calc.min(3, affected.len())) [
      #text(size: 6pt, fill: muted)[#task]
      #linebreak()
    ]
    #if affected.len() > 3 [
      #text(size: 6pt, fill: muted)[+#str(affected.len() - 3) more]
    ]
  ]
}

#let action-card(action) = block(width: 100%, inset: 7pt, stroke: line, fill: white, radius: 2pt)[
  #grid(
    columns: (0.58fr, 2.55fr),
    gutter: 8pt,
    [
      #priority-chip(val(action, "priority", fallback: "medium"))
      #v(3pt)
      #text(size: 5.8pt, fill: muted)[#upper(val(action, "category", fallback: ""))]
    ],
    [
      #text(size: 8pt, weight: "bold")[#val(action, "title", fallback: "")]
      #v(3pt)
      #val(action, "description", fallback: "")
      #v(5pt)
      #text(size: 6pt, fill: accent, weight: "bold")[Task links]
      #v(1.5pt)
      #task-link-list(action)
    ],
  )
]

#v(8mm)
#role-header()
#grid(
  columns: (1fr, 1fr, 1fr),
  gutter: 8pt,
  score-card("Automation Impact Score (AIS)", val(scores, "ais_composite", fallback: 0), val(scores, "ais_band", fallback: ""), teal),
  score-card("Augmentation Impact Score (APS)", val(scores, "aps_composite", fallback: 0), val(scores, "aps_band", fallback: ""), navy),
  block(width: 100%, inset: 6pt, stroke: line, fill: panel, radius: 2pt)[
    #text(size: 5.5pt, fill: ink)[ARIA Classification]
    #v(4pt)
    #text(size: 13pt, weight: "bold")[#val(scores, "aria_classification", fallback: "")]
    #v(4pt)
    #text(size: 5.8pt, fill: ink)[#classification_position]
  ],
)

#v(10mm)
#text(size: 10pt, weight: "bold")[Insights]
#v(1pt)
#text(size: 6.8pt, fill: muted)[Key message and insights distilled from this role's analysis]
#v(4mm)
#std.line(length: 100%, stroke: 0.5pt + line)
#v(5mm)
#grid(
  columns: (1fr, 1fr),
  gutter: 8pt,
  narrative-card("Automation exposure", val(narratives, "automation_exposure", fallback: (:))),
  narrative-card("Augmentation potential", val(narratives, "augmentation_potential", fallback: (:))),
)
#v(5pt)
#block(width: 100%, inset: 9pt, stroke: line, fill: panel, radius: 4pt)[
  #text(size: 7pt, weight: "bold")[Classification | #val(scores, "aria_classification", fallback: "")]
  #v(4pt)
  #val(val(narratives, "classification_explanation", fallback: (:)), "claim", fallback: "")
]
#v(5pt)

#if val(brief, "opening_talk_track", fallback: "") != "" [
  #text(size: 13pt, weight: "bold")[Opening talk track]
  #v(2mm)
  #val(brief, "opening_talk_track", fallback: "")
  #v(6mm)
]
#divider("Task Decomposition", subtitle: "Each task is scored on AIS and APS for consultant discussion.")

#table(
  columns: (1.8fr, 1fr, 1fr),
  inset: 5pt,
  stroke: line,
  table.header([Task], [AIS], [APS]),
  ..val(report, "tasks", fallback: ()).map(task-row).flatten()
)

#divider("Future Role & Skill Requirements", subtitle: "How each task evolves with AI, and which skills become important.")

#table(
  columns: (1fr, 1.7fr, 1.2fr),
  inset: 4pt,
  stroke: line,
  table.header([Task], [How AI changes this], [Skills applied]),
  ..future.map(future-row).flatten()
)

#divider("Skills Reference", subtitle: "All skills referenced above with classification and description.")

#table(
  columns: (0.45fr, 1fr, 2.2fr),
  inset: 4pt,
  stroke: line,
  table.header([Type], [Skill], [Description]),
  ..skills.map(skill-row).flatten()
)

#divider("Recommendations", subtitle: "Suggestions to move beyond the analysis.")

#text(size: 8pt, weight: "bold")[For the Organisation]
#v(2mm)
#val(val(rec, "for_organisation", fallback: (:)), "recommendation", fallback: "")
#v(8mm)
#text(size: 8pt, weight: "bold")[For Employees In Role]
#v(2mm)
#val(val(rec, "for_employees_in_role", fallback: (:)), "recommendation", fallback: "")
#v(7mm)
#if val(implementation, "strategy_summary", fallback: "") != "" [
  #text(size: 9pt, weight: "bold")[Implementation Plan]
  #v(2mm)
  #val(implementation, "strategy_summary", fallback: "")
  #v(4mm)
  #grid(
    columns: (1fr, 1fr),
    gutter: 8pt,
    block(width: 100%, inset: 6pt, stroke: line, fill: panel, radius: 2pt)[
      #text(size: 6pt, weight: "bold", fill: accent)[Estimated productivity gain]
      #v(3pt)
      #text(size: 7pt)[#val(implementation, "estimated_productivity_gain", fallback: "")]
    ],
    block(width: 100%, inset: 6pt, stroke: line, fill: panel, radius: 2pt)[
      #text(size: 6pt, weight: "bold", fill: accent)[Transition risk]
      #v(3pt)
      #text(size: 7pt)[#val(implementation, "transition_risk", fallback: "")]
    ],
  )
  #v(4mm)
  #for action in val(implementation, "actions", fallback: ()) [
    #action-card(action)
    #v(3pt)
  ]
  #v(7mm)
]
#text(size: 13pt, weight: "bold")[Consultant prompts]
#v(2mm)
#list(..val(brief, "client_questions", fallback: ()))
#v(5mm)
#text(size: 10pt, weight: "bold")[Watchouts]
#list(..val(brief, "watchouts", fallback: ()))
