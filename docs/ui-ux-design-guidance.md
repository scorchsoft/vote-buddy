This file tells any future AI (or human) contributor exactly how to design, theme and build UI/UX that feels unmistakably "British Powerlifting", while staying lean, accessible and easy to extend.

# UI / UX & Design Guidance  
_VoteBuddy: British Powerlifting Voting Platform_

> **Purpose** – Provide a single, authoritative reference for colours, typography, layout patterns and UX conventions so every screen, e‑mail and export looks coherent, accessible and on‑brand.

---

## 1 Brand‑Core

| Token | Hex | Usage |
|-------|------|-------|
| **bp‑blue** | `#002D59` | Headers, nav‑bars, primary text links 0 |
| **bp‑red**  | `#DC0714` | Primary CTA buttons, accent highlights 1 |
| **bp‑white**| `#FFFFFF` | Backgrounds, cards |
| **bp‑grey‑50** | `#F7F7F9` | Page backdrop, table stripes |
| **bp‑grey‑700** | `#3F4854` | Body copy |
| **bp‑yellow‑a11y** | `#FFEB3B` | Success banners / highlight pills (matches screenshot) |

### Brand Font Stack
```css
font-family: "Gotham", "Arial", "Helvetica Neue", sans-serif;

Gotham Book (400), Bold (700)

Arial fallback for system compatibility. 



---

2 Tailwind Config Snippet

// tailwind.config.cjs
module.exports = {
  content: ["./templates/**/*.html", "./static/js/**/*.js"],
  theme: {
    extend: {
      colors: {
        bp: {
          blue:  "#002D59",
          red:   "#DC0714",
          yellow:"#FFEB3B",
          gray:  {
            50:  "#F7F7F9",
            700: "#3F4854",
          },
        },
      },
      fontFamily: {
        sans: ['Gotham', 'Arial', 'Helvetica Neue', 'sans-serif'],
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};


---

3 Layout & Navigation

3.1 Global Shell

┌─ Top Nav (bp‑blue, white logo)
│  ├ Home ┊ Meetings ┊ Results ┊ Help
│  └ User‑menu  ⋮  (role badge)
├─ Sticky secondary bar (stage status / quorum %)
│
└─ Main content container (≤ 1200 px, centred)

Mobile: swap to hamburger → slide‑in drawer.

3.2 Admin Dashboard

Card grid of My Meetings (status chips, % voted).

"Create Meeting" floating action button (bp‑red).

Breadcrumbs: Dashboard › 2025 AGM › Stage 1.


3.3 Voting Page (Member)

1. Progress header – stage label + closes in Xh Ym.


2. Motion overview – collapsible accordions:
Full motion text ⇢ Each amendment card (big Yes/No buttons).


3. Sticky confirmation footer – shows selection status, large "Submit vote" CTA. Appears as the final Tab stop so keyboard users can submit easily.


4. Post‑vote screen → big tick icon (bp‑red outline), next‑steps text, link to FAQs.



3.4 Run‑off Flow

List conflicting amendments in a two‑column card → radio select → submit.
Banner explaining why this extra step exists.


---

4 Component Library

Component	Key Details

Buttons	.btn-primary (bp‑red bg → white text), .btn-secondary (bp‑blue border text), 44 px min height
Cards	white bg, 1 px bp‑grey‑50 border, 16 px radius
Badges	Rounded pill, size‑sm; colours map to vote status (green, red, grey)
Stepper	Horizontal for desktop, vertical for mobile; ARIA labelled
Modal	Used ONLY for destructive actions (delete meeting)


Convention: Prefer hx-boost="true" + htmx attributes for partial reloads; avoid heavy JS.

Data tables follow a simple pattern:
* Wrap the table in `<table class="bp-table">` and keep headers in `<thead>`.
* Provide a search `<form>` with `hx-get` to the list route and `hx-trigger="keyup changed delay:300ms"`.
* Clicking a column header issues an `hx-get` with `sort` and `direction` params.
* The `<tbody id="table-body">` is replaced on each request so the page never fully reloads.



---

5 Accessibility Rules (WCAG 2.2 AA)

Colour contrast ≥ 4.5 : 1 (already met with bp‑blue / white).
Dark mode uses a dark‑blue/grey palette and is enabled automatically with an optional toggle in the header.

All interactive elements reachable via Tab order; visible focus ring (outline-offset: 2px).

ARIA role="status" on live quorum counter.

Screen‑reader‑only sr-only labels on icon‑only buttons.

Forms: associate every <input> with <label>; inline error beneath field using
`<p id="field-id-error" class="bp-error-text">...` and add
`aria-describedby="field-id-error"` on the input.



---

6 Interaction & Copy Tone

Scenario	Micro‑copy example

Vote submitted "💪 Vote recorded! You'll get an e‑mail receipt in the next few minutes."
Stage closed "This stage is now locked by the Returning Officer."
Quorum warning "Only 38 % turnout – reminders will be sent automatically in 3 h."
Disabled revote	Tooltip: "The coordinator has disabled vote changes for this stage."


Tone = confident, plain‑English, small flashes of powerlifting humour ("Let's chalk up and lift your vote!") but never sarcastic when confirming actions.


---

7 Email Templates

HTML + plain‑text versions.

Header bar: bp‑blue; BP logo 120×40 px inline‑SVG.

Big red CTA button ⇒ unique voting link.

Footer: unsubscribe link (batch mail compliance) + legal footer (company number).
Link points to `/unsubscribe/<token>` and marks the member opted out.

WCAG: 600 px width, min font 16 px, dark‑mode tested.



---

8 Export / Docs Styling

Docx exports use bp‑blue title bar, Gotham Book body, bp‑red section headers.

Table rows alternate white / bp‑grey‑50.

Include BP logo watermark bottom‑right.



---

9 File & Class Naming

Layer	Convention

Templates	meetings_list.html, ballot_stage1.html
CSS (if needed)	Utility‑first Tailwind, but custom classes prefixed bp-
JS	vote-confirm.js, import-csv.js
Docs	Keep Markdown file names kebab‑case (design-guidance.md)



---

10 Responsive Breakpoints

sm ≤ 640 px (phones) – single column, 20 px gutter

md 641‑1024 px – two‑column admin grids

lg ≥ 1025 px – max‑width 1200 px, 24 px gutter


Tailwind handles these via sm:, md:, lg: utilities.


---

11 Motion & Amendment Presentation Rules

1. Always show full motion text at top of every amendment voting page (read‑only).


2. Clearly label each amendment card: Amendment #A3, proposer & seconder names.


3. If amendment carried, show bp‑red tick on Stage 1 results table.


4. Stage 2 page displays auto‑compiled motion (carried amendments merged); read‑only blockquote style.




---

12 Visual Inspiration References

Attached screenshot (hero section) – note high‑impact bold headline, red text highlight, yellow button.

GOV.UK Design System – clarity & accessibility patterns.

IPF meet results portals – table designs for big numeric data.



---

13 Updating This Guide

1. Minor tweak? Commit directly to docs/design-guidance.md with [ci skip] in message.


2. New component? Add under "Component Library" with usage notes.


3. PR auto‑fails if heading names are changed without updating internal links in README.

14 Extended Design Patterns
- **Form layout** – wrap groups in `.bp-form` with 24 px vertical gaps. Inputs use 12 px padding and a 4 px radius.
- **Alert banners** – `.bp-alert-success`, `.bp-alert-warning` and `.bp-alert-error` classes with matching icons.
- **Pagination** – `.bp-pagination` list with arrow icons; highlight current page with bp-red.
- **Stepper states** – `.bp-stepper-current` and `.bp-stepper-complete` to show progress.
- **Progress bars** – `.bp-progress` uses ARIA roles and includes a `<span class="sr-only">% complete</span>` label.
- **Tabs** – `.bp-tab` underlines the active tab; keep touch targets ≥ 44 px.
- **Collapsible sections** – use `<details>` and `<summary>` styled with a bp-blue disclosure arrow.
- **Tooltip** – `[data-tooltip]` reveals a CSS-only bubble on hover **or focus**.
  The element should be `position: relative`; the bubble text is generated with a
  `::after` pseudo-element.
- **Utility gaps** – `.bp-gap-xs` (4 px) to `.bp-gap-lg` (24 px) standardise spacing across components.




---

Version 0.1 – 13 Jun 2025

---

### How to use this

* Designers: import colours/fonts into Figma file `BP‑Voting‑UI.fig`.  
* Developers: merge `tailwind.config.cjs`, run `npm run dev`, spot‑check contrast with the Axe browser add‑on.  
* Docs writers / future AI: reference page structures above to stay consistent.

Now we've set the bar – time to lift heavy (code)!3

---

## 15 Modern Design Enhancements (2024 Update)

### Enhanced Visual Design
- **Gradients** – Linear gradients on buttons, hero sections, and navigation for depth
- **Shadows** – Multi-level shadow system (shadow-sm through shadow-2xl) for elevation  
- **Animations** – Smooth transitions, hover effects, and micro-interactions
- **Icons** – SVG icons throughout for better scalability and consistency

### New Components
- **Hero Section** – Full-width gradient hero with animated background pattern
- **Stat Cards** – Large numeric displays with hover animations  
- **Feature Grid** – Icon-based feature cards with hover effects
- **Enhanced Dropdowns** – Smooth animated dropdowns with icons
- **Loading States** – Spinner animations and skeleton screens
- **Progress Bars** – Animated progress indicators with shimmer effect

### Typography Updates
- **Font** – Inter font family for modern, clean appearance
- **Sizes** – Larger, more readable text with better hierarchy
- **Letter Spacing** – Tighter tracking on headings for impact

### Improved Interactions
- **Hover States** – All interactive elements have smooth transitions
- **Focus States** – Yellow outline for accessibility with offset
- **Mobile Navigation** – Slide-in drawer with overlay backdrop
- **Smooth Scrolling** – Anchor links scroll smoothly to sections
- **Form Enhancements** – Floating labels and better validation states

### Dark Mode Support
- Toggle between light/dark themes with smooth transition
- Theme preference saved to localStorage
- Icon changes between sun/moon based on theme

### Performance Optimizations
- CSS custom properties for dynamic values
- Efficient animations using transform and opacity
- Lazy loading for images and heavy components

Version 1.0 – December 2024
