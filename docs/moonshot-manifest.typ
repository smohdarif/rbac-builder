// ==========================================================================
// LaunchDarkly Theme & Page Setup
// ==========================================================================
#let ld-navy = rgb("#191C22")
#let ld-blue = rgb("#405BFF")
#let ld-teal = rgb("#00C0E8")
#let ld-white = rgb("#FFFFFF")
#let ld-light = rgb("#F7F8FA")
#let ld-gray = rgb("#6B7280")
#let ld-dark = rgb("#374151")
#let ld-green = rgb("#3DD6F5")
#let ld-accent = rgb("#A34FDE")

#set page(
  margin: (x: 0.9in, y: 0.8in),
  footer: context [
    #line(length: 100%, stroke: 0.3pt + rgb("#E5E7EB"))
    #v(4pt)
    #text(size: 8pt, fill: ld-gray)[
      RBAC Builder ~ Moonshots XXIII
      #h(1fr)
      #counter(page).display("1 / 1", both: true)
    ]
  ],
)

#set text(font: "Helvetica Neue", size: 10pt, fill: ld-dark)
#set par(leading: 0.65em, justify: true)

// ==========================================================================
// Reusable Components
// ==========================================================================

// Accent bar + heading
#let section(title) = {
  v(14pt)
  block(width: 100%)[
    #box(width: 4pt, height: 18pt, fill: ld-blue, baseline: -2pt)
    #h(8pt)
    #text(size: 15pt, weight: "bold", fill: ld-navy)[#title]
  ]
  v(6pt)
}

// Lighter sub-section
#let subsection(title) = {
  v(8pt)
  text(size: 11pt, weight: "bold", fill: ld-blue)[#title]
  v(3pt)
}

// Callout box
#let callout(body, accent: ld-blue) = {
  v(4pt)
  block(
    width: 100%,
    inset: (left: 14pt, rest: 12pt),
    stroke: (left: 3pt + accent),
    fill: ld-light,
    radius: (right: 4pt),
  )[#text(size: 9.5pt)[#body]]
  v(4pt)
}

// Flow diagram box
#let flow-box(label, accent: ld-blue) = {
  box(
    inset: (x: 10pt, y: 6pt),
    fill: accent.lighten(85%),
    stroke: 1pt + accent,
    radius: 6pt,
  )[#text(size: 9pt, weight: "bold", fill: accent.darken(20%))[#label]]
}

// Arrow between flow boxes
#let arrow() = {
  h(4pt)
  text(size: 12pt, fill: ld-gray)[#sym.arrow.r]
  h(4pt)
}


// ==========================================================================
// PAGE 1 --- Cover / Summary
// ==========================================================================

// Header bar
#block(
  width: 100%,
  inset: (x: 16pt, y: 14pt),
  fill: ld-navy,
  radius: 8pt,
)[
  #text(size: 10pt, fill: ld-teal, weight: "bold")[MOONSHOTS XXIII]
  #v(2pt)
  #text(size: 24pt, fill: ld-white, weight: "bold")[RBAC Builder]
  #v(2pt)
  #text(size: 11pt, fill: rgb("#9CA3AF"))[Design RBAC policies visually. Deploy them instantly.]
]

#v(14pt)

// Quick facts row
#grid(
  columns: (1fr, 1fr, 1fr, 1fr),
  gutter: 10pt,
  block(inset: 10pt, fill: ld-light, radius: 6pt, width: 100%)[
    #text(size: 8pt, fill: ld-gray)[TEAM] \
    #text(size: 10pt, weight: "bold")[Arif Shaikh]
  ],
  block(inset: 10pt, fill: ld-light, radius: 6pt, width: 100%)[
    #text(size: 8pt, fill: ld-gray)[STATUS] \
    #text(size: 10pt, weight: "bold")[Work in Progress]
  ],
  block(inset: 10pt, fill: ld-light, radius: 6pt, width: 100%)[
    #text(size: 8pt, fill: ld-gray)[DEMO] \
    #text(size: 9pt, weight: "bold")[#link("https://customroles.streamlit.app")[customroles.streamlit.app]]
  ],
  block(inset: 10pt, fill: ld-light, radius: 6pt, width: 100%)[
    #text(size: 8pt, fill: ld-gray)[NEED HELP WITH] \
    #text(size: 9pt, weight: "bold")[Demo video, eng polish]
  ],
)

#v(6pt)

// The one-liner
#callout(accent: ld-blue)[
  *In one sentence:* An SA opens the builder, checks boxes in a permission matrix, and gets API-ready JSON, Terraform files, and a deployment ZIP --- no manual JSON authoring, no guessing action names, no tribal knowledge required.
]

#v(2pt)

// --------------------------------------------------------------------------
section("The Problem We're Solving")

Every enterprise customer needs custom RBAC. And every time, the SA faces the same struggle:

#v(6pt)

#grid(
  columns: (1fr, 1fr),
  gutter: 12pt,

  // Card 1
  block(inset: 12pt, fill: ld-light, radius: 6pt, width: 100%, stroke: 0.5pt + rgb("#E5E7EB"))[
    #text(weight: "bold", fill: ld-navy)[The Blank Page]
    #v(4pt)
    #text(size: 9.5pt)[
      _"Who should get what permissions?"_

      The SA opens a Google Sheet, cross-references Terraform modules, looks up action names in source code, hand-writes JSON, and hopes the scoping is right. One typo means a broken deployment. Takes *2--4 hours per customer.*
    ]
  ],

  // Card 2
  block(inset: 12pt, fill: ld-light, radius: 6pt, width: 100%, stroke: 0.5pt + rgb("#E5E7EB"))[
    #text(weight: "bold", fill: ld-navy)[No Health Visibility]
    #v(4pt)
    #text(size: 9.5pt)[
      Existing customers have orphaned roles, inactive users with elevated access, and no way to audit their posture. We can diagnose the problem (Policy Explorer) but there's no bridge to _"here's how to fix it."_
    ]
  ],
)

#v(8pt)

#block(inset: 12pt, fill: ld-light, radius: 6pt, width: 100%, stroke: 0.5pt + rgb("#E5E7EB"))[
  #text(weight: "bold", fill: ld-navy)[Keeping Up With the Product]
  #h(8pt)
  #text(size: 9.5pt)[AI Configs added new actions in 2024--2025. Most SAs don't know they exist yet. The builder includes them natively, so SAs stay ahead.]
]


// --------------------------------------------------------------------------
section("How It Works")

Here's what the SA experience looks like, start to finish:

#v(8pt)

// Flow diagram
#align(center)[
  #flow-box("Setup", accent: ld-blue)
  #arrow()
  #flow-box("Design Matrix", accent: ld-accent)
  #arrow()
  #flow-box("Review & Deploy", accent: rgb("#10B981"))
]

#v(10pt)

#grid(
  columns: (1fr, 1fr, 1fr),
  gutter: 10pt,

  block(inset: 10pt, radius: 6pt, width: 100%, stroke: (top: 3pt + ld-blue, rest: 0.5pt + rgb("#E5E7EB")))[
    #text(size: 9pt, weight: "bold", fill: ld-blue)[1. SETUP]
    #v(3pt)
    #text(size: 9pt)[
      Enter customer name, project key, teams, and environments. Choose manual or connected mode (pull from the LD API).
    ]
  ],

  block(inset: 10pt, radius: 6pt, width: 100%, stroke: (top: 3pt + ld-accent, rest: 0.5pt + rgb("#E5E7EB")))[
    #text(size: 9pt, weight: "bold", fill: ld-accent)[2. DESIGN MATRIX]
    #v(3pt)
    #text(size: 9pt)[
      Check boxes in a spreadsheet-like grid: Teams #sym.times Permissions #sym.times Environments. Project-scoped and environment-scoped actions are clearly separated.
    ]
  ],

  block(inset: 10pt, radius: 6pt, width: 100%, stroke: (top: 3pt + rgb("#10B981"), rest: 0.5pt + rgb("#E5E7EB")))[
    #text(size: 9pt, weight: "bold", fill: rgb("#10B981"))[3. DEPLOY]
    #v(3pt)
    #text(size: 9pt)[
      Download API-ready JSON, Terraform HCL, or a delivery ZIP. Or deploy directly to LaunchDarkly with one click.
    ]
  ],
)


// ==========================================================================
// PAGE 2 --- Capabilities & Impact
// ==========================================================================
#pagebreak()

section("What the Builder Can Do")

#v(4pt)

// Capability 1
#grid(
  columns: (48pt, 1fr),
  gutter: 8pt,

  // Icon area
  align(center + horizon)[
    #block(
      width: 40pt, height: 40pt,
      fill: ld-blue.lighten(85%),
      radius: 20pt,
      inset: 0pt,
    )[#align(center + horizon)[#text(size: 18pt)[#sym.square.stroked.dotted]]]
  ],

  // Description
  block[
    #text(size: 11pt, weight: "bold", fill: ld-navy)[Visual Permission Matrix]
    #v(2pt)
    #text(size: 9.5pt)[
      Instead of writing JSON by hand, the SA checks boxes. The matrix covers flag lifecycle, segments, experiments, AI configs, observability, approval workflows --- everything. Critical vs. non-critical environments are handled automatically with tag-based scoping.
    ]
  ],
)

#v(10pt)

// Capability 2
#grid(
  columns: (48pt, 1fr),
  gutter: 8pt,

  align(center + horizon)[
    #block(
      width: 40pt, height: 40pt,
      fill: ld-accent.lighten(85%),
      radius: 20pt,
      inset: 0pt,
    )[#align(center + horizon)[#text(size: 18pt)[#sym.diamond.stroked]]]
  ],

  block[
    #text(size: 11pt, weight: "bold", fill: ld-navy)[Sage --- AI Role Designer]
    #v(2pt)
    #text(size: 9.5pt)[
      Not sure where to start? Describe the customer's teams in plain English: _"We have 4 teams, developers need targeting in test but only view in prod."_ Sage (powered by Gemini) recommends a complete permission matrix with reasoning. Review it, tweak it, apply it to the grid with one click.
    ]
  ],
)

#v(10pt)

// Capability 3
#grid(
  columns: (48pt, 1fr),
  gutter: 8pt,

  align(center + horizon)[
    #block(
      width: 40pt, height: 40pt,
      fill: rgb("#10B981").lighten(85%),
      radius: 20pt,
      inset: 0pt,
    )[#align(center + horizon)[#text(size: 18pt)[#sym.arrow.t.b.double]]]
  ],

  block[
    #text(size: 11pt, weight: "bold", fill: ld-navy)[Multi-Format Export]
    #v(2pt)
    #text(size: 9.5pt)[
      The builder outputs whatever the customer needs:
    ]
    #v(2pt)
    #text(size: 9pt)[
      #sym.checkmark *API-ready JSON* --- deploy custom roles and teams directly \
      #sym.checkmark *Terraform HCL* --- fits into infrastructure-as-code workflows \
      #sym.checkmark *Delivery ZIP* --- matches the standard SA delivery package \
      #sym.checkmark *Direct API deploy* --- push to LaunchDarkly from the UI
    ]
  ],
)

#v(10pt)

// Capability 4
#grid(
  columns: (48pt, 1fr),
  gutter: 8pt,

  align(center + horizon)[
    #block(
      width: 40pt, height: 40pt,
      fill: ld-teal.lighten(85%),
      radius: 20pt,
      inset: 0pt,
    )[#align(center + horizon)[#text(size: 18pt)[#sym.quest]]]
  ],

  block[
    #text(size: 11pt, weight: "bold", fill: ld-navy)[Policy Explorer (Companion)]
    #v(2pt)
    #text(size: 9.5pt)[
      A separate tool that connects to a customer's existing account and shows the health of their RBAC: orphaned roles, inactive users with elevated access, role utilization rates. Explorer diagnoses, Builder prescribes.
    ]
  ],
)

// --------------------------------------------------------------------------
section("Before & After")

#v(4pt)

#grid(
  columns: (1fr, 32pt, 1fr),
  gutter: 0pt,

  // Before
  block(inset: 12pt, fill: rgb("#FEF2F2"), radius: 6pt, width: 100%, stroke: 0.5pt + rgb("#FECACA"))[
    #text(size: 10pt, weight: "bold", fill: rgb("#991B1B"))[Before]
    #v(4pt)
    #text(size: 9pt)[
      - Open Google Sheet, start from scratch \
      - Cross-reference Terraform modules \
      - Look up action names in source code \
      - Hand-write JSON policy statements \
      - Hope the scoping is correct \
      - *2--4 hours per customer*
    ]
  ],

  // Arrow
  align(center + horizon)[
    #text(size: 16pt, fill: ld-gray)[#sym.arrow.r]
  ],

  // After
  block(inset: 12pt, fill: rgb("#F0FDF4"), radius: 6pt, width: 100%, stroke: 0.5pt + rgb("#BBF7D0"))[
    #text(size: 10pt, weight: "bold", fill: rgb("#166534"))[After]
    #v(4pt)
    #text(size: 9pt)[
      - Open RBAC Builder \
      - Check boxes in a visual matrix \
      - Or ask Sage for a recommendation \
      - Download JSON, Terraform, or ZIP \
      - Deploy directly from the UI \
      - *15 minutes per customer*
    ]
  ],
)


// --------------------------------------------------------------------------
section("The Journey So Far")

#v(4pt)

// Architecture flow
#align(center)[
  #flow-box("Data Models", accent: ld-gray)
  #arrow()
  #flow-box("Storage", accent: ld-gray)
  #arrow()
  #flow-box("Payload Builder", accent: ld-blue)
  #arrow()
  #flow-box("Validator", accent: ld-blue)
]
#v(4pt)
#align(center)[
  #flow-box("UI (Streamlit)", accent: ld-accent)
  #arrow()
  #flow-box("API Client", accent: ld-accent)
  #arrow()
  #flow-box("Deployer", accent: rgb("#10B981"))
  #arrow()
  #flow-box("Terraform Gen", accent: rgb("#10B981"))
]
#v(4pt)
#align(center)[
  #flow-box("Sage (AI Advisor)", accent: ld-accent)
  #arrow()
  #flow-box("Package Gen", accent: rgb("#10B981"))
  #arrow()
  #flow-box("Session Tracker", accent: ld-gray)
]

#v(8pt)

*28 phases designed, 16+ implemented.* Fully tested with unit tests, documented with architecture guides, and deployed on Streamlit Cloud.

// --------------------------------------------------------------------------
section("Impact")

#v(4pt)

#grid(
  columns: (1fr, 1fr),
  gutter: 10pt,

  block(inset: 12pt, fill: ld-light, radius: 6pt, width: 100%)[
    #text(size: 20pt, weight: "bold", fill: ld-blue)[8x faster]
    #v(2pt)
    #text(size: 9pt, fill: ld-gray)[Hours to minutes per customer RBAC delivery]
  ],

  block(inset: 12pt, fill: ld-light, radius: 6pt, width: 100%)[
    #text(size: 20pt, weight: "bold", fill: ld-blue)[Zero guesswork]
    #v(2pt)
    #text(size: 9pt, fill: ld-gray)[Correct scoping, least-privilege, validated before deploy]
  ],

  block(inset: 12pt, fill: ld-light, radius: 6pt, width: 100%)[
    #text(size: 20pt, weight: "bold", fill: ld-blue)[Always current]
    #v(2pt)
    #text(size: 9pt, fill: ld-gray)[AI Configs, observability, context kinds built in]
  ],

  block(inset: 12pt, fill: ld-light, radius: 6pt, width: 100%)[
    #text(size: 20pt, weight: "bold", fill: ld-blue)[Any SA can deliver]
    #v(2pt)
    #text(size: 9pt, fill: ld-gray)[No more tribal knowledge --- the tool knows the actions]
  ],
)

#v(14pt)

#callout(accent: ld-teal)[
  *Want to help?* Looking for folks interested in SA tooling, AI-assisted workflows, or LaunchDarkly RBAC. Engineering help for API polish and a killer demo video would be amazing. Reach out to *\@Arif Shaikh*.
]
