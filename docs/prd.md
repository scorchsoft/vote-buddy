# "VoteBuddy" tool - British Powerlifting Voting Platform – Product Requirements Document (MVP)

> **One‑liner**  
> “A single‑instance Flask web app that lets BP admins run clear, two‑stage (or combined) electronic ballots, emailing each member a unique link and publishing auditable results in line with the new Articles 107‑115.”

---

## 1  Vision & Success Criteria
| Goal | Measurable KPI | Target for first live EGM/AGM |
|------|---------------|--------------------------------|
| Run ballots that match Articles 107‑115 | 100 % of required voting flows available | ✅ |
| Member confidence | ≥ 90 % “process was clear” in post‑meeting survey | ✅ |
| Security | Passes OWASP Top 10 checks in automated scan | ✅ (no critical issues) |
| Accessibility | WCAG 2.2 AA conformance | ✅ |

---

## 2  Stakeholders & Roles
| Role | Powers | Notes |
|------|--------|-------|
| **Root Admin** | Create any meeting; manage coordinators; toggle revoting; view all data | Typically BP Head Office governance officer |
| **Meeting Coordinator** | CRUD only for meetings they own | Assigned per meeting |
| **Returning Officer (RO)** | Read‑only access plus “lock/unlock stage”, download tallies, certify result | Must be independent under Art 112c |
| **Member (token‑based)** | Vote once per stage (unless revoting enabled) | No login account in MVP |
| **User** | Login account for admins & coordinators | Flask‑Login with role‑permission mapping |

---

## 3  Scope

### In‑scope (MVP)
* Single‑tenant Flask app (Python 3.12)  
* Postgres via SQLAlchemy ORM  
* Tailwind CSS + htmx + vanilla JS (progressive enhancement)  
* Email delivery via AWS SES (fallback: SMTP)  
* CSV import **per meeting** (`member_id, name, email, proxy_for`)
* Two ballot modes:  
  * **Two‑stage:** Stage 1 amendments ⇒ Stage 2 motion  
  * **Combined:** Simultaneous amendments + motion (Art 111)  
* Optional revoting toggle (per stage)  
* Run‑off flow for clashing amendments (automatic if needed)  
* Quorum check (Art 112d) with alert banners  
* Docx export of Stage 1 summary & Stage 2 certified outcome  
* Full audit log (CSV) downloadable by RO  
* WCAG‑AA templates; keyboard + screen‑reader tested   
* OWASP Top 10 mitigations (CSRF, rate‑limit, token entropy ≥ 128 bits, etc.)   

### Out‑of‑scope (MVP)
* Multi‑tenant federation support  
* Member self‑service accounts / password auth  
* Real‑time vote visualisations  
* Full mobile app (responsive web only)  

---

## 4  User Journeys (Happy‑Path)

### 4.1  Coordinator
1. Logs in via admin panel (Flask‑Login).  
2. “Create Meeting” → fills metadata, uploads CSV.  
3. Adds motion text and one or more amendments (rich‑text Markdown).  
4. Picks ballot mode, sets opening/closing timestamps, toggles revoting.  
5. Clicks “Send invites” → system emails unique, one‑click ballot URLs.  
6. Monitors dashboard: quorum %, votes‑cast, reminder countdown.  
7. At close, system auto‑generates Stage 1 docx + optional run‑off ballot.  
8. Triggers Stage 2; at final close, downloads certified results package.

### 4.2  Member
1. Opens e‑mail and clicks a personal URL containing a UUIDv7 token hashed via SHA-256 on the server (see changelog entry 2025-06-15).  
2. Landing page shows **motion text** in full plus specific amendment being voted on – this nudges comprehension without forcing back‑and‑forth navigation.  
3. Selects *Yes* / *No* (or *Abstain*, optional toggle) → confirms.  
4. Sees “Thanks, you voted X” banner; “Change vote” appears only if revoting enabled.  
5. Receives e‑mail receipt with hash of ballot for later verification.

### 4.3  Returning Officer
* Dashboard lists active stages; can **lock** a stage early if Chair instructs.  
* One‑click “Download tallies” (CSV + JSON) for offline scrutiny.

> **Why two stages?** – Robert’s Rules requires amendments first, then the motion, preserving member intent and audit clarity. 

---

## 5  Functional Requirements

### 5.1 Meetings CRUD
* Fields: `id`, `title`, `type` (AGM / EGM), `notice_date`, `opens_at_stage1`, `closes_at_stage1`, `opens_at_stage2`, `closes_at_stage2`, `ballot_mode`, `revoting_allowed`, `status`, `chair_notes_md`.

### 5.2 Member Import & Token Generation
* CSV validation (header check, duplicate e‑mail detection).  
* For each row create `Member` + `VoteToken` (UUIDv7).  
* Email template uses Django‑style placeholder tags.

### 5.3 Voting Engine
* Each `Vote` persisted with `hash(member_id + choice + secret_salt)` for tamper‑evidence.  
* Automatic lockout after submission when revoting disabled.

### 5.4 Run‑off Logic (Stage 1 only)
* Detect mutually exclusive amendments (flagged by coordinator UI).  
* Highest‑vote amendment wins; ties resolved per Art 109 (Chair tie‑break, earliest submission fallback).  
* If run‑off required in online ballot, system auto‑extends Stage 1 by configured “runoff_extension” minutes and re‑e‑mails affected members.

### 5.5 Quorum, Reminders & Cron Jobs
* Background scheduler using APScheduler (Celery + Redis optional for heavier workloads)
* Scheduler started in `create_app`; see `app/tasks.py`.
* Hourly job `stage1_reminders` checks meetings closing within `REMINDER_HOURS_BEFORE_CLOSE` and emails outstanding voters once per `REMINDER_COOLDOWN_HOURS`.
* Configurable reminder template.

### 5.6 Results Publication
* At each stage close:
  * Static HTML “Results” page (public‑share toggle).
  * Docx via `python-docx` merged template.
  * Digest e‑mail to Chair & RO.
  * Meeting status set to `Completed` after Stage 2 tallies are saved.

### 5.7 Proxy Voting Support (MVP Lite)
* CSV may include `proxy_for` (member_id).
* During vote cast, if member is proxy holder the UI shows extra banner and logs both votes.

### 5.8 Permission Management
* Admin page to create and edit individual permission records.
* Permissions are assigned to roles via the role form.

---

## 6  Non‑Functional Requirements

### 6.1 Security
* HTTPS only (HSTS pre‑load).  
* Vote tokens are UUIDv7 strings hashed with SHA-256 and a server-side salt (see changelog entry 2025-06-15). Tokens are scoped to meeting + stage and expire at stage close.
* CSRF tokens on all POST; `X-Frame-Options: DENY`.
* All user input sanitised (Bleach) to prevent XSS.
* Automated dependency scanning (GitHub Dependabot).
* Pen‑test checklist aligns with OWASP Secure Coding Guide.
* Every feature must enforce role permissions on pages and endpoints
  using `permission_required` to guard access.
* Login and voting endpoints are rate limited with Flask-Limiter.

### 6.2 Accessibility & UX
* Colour palette and logos per BP brand guide.  
* Tailwind utility classes keep contrast ≥ 4.5:1.  
* Focus order and ARIA labels tested with NVDA & VoiceOver.  
* Meets WCAG 2.2 AA.   

### 6.3 Performance & Hosting
* Containerised Docker image (gunicorn + nginx).  
* Fits in t3.small Lightsail with Postgres RDS (< 1000 concurrent voters).  
* Backups: daily DB snapshot, hourly WAL.

---

## 7  Data Model (ER snapshot)

````
Role *───* Permission
│
└─1 Role ───\* User

Meeting 1───\* Motion
│                │
│                └─\* Amendment
│                     │
│                     └─\* Vote
│
├──\* Member (scoped to meeting)
│        │
│        └─1 VoteToken (per stage)
│
├──\* Runoff (optional)
└──\* AmendmentConflict (optional)

````

| Table | Key Columns (trimmed) |
|-------|-----------------------|
| `meetings` | `id`, `title`, `type`, open/close timestamps, `ballot_mode`, `revoting_allowed`, `quorum`, `stage1_locked`, `stage2_locked` |
| `motions` | `id`, `meeting_id`, `title`, `text_md`, `category`, `threshold`, `ordering` |
| `motion_options` | `id`, `motion_id`, `text` |
| `amendments` | `id`, `meeting_id`, `motion_id`, `text_md`, `order`, `status`, `proposer_id`, `seconder_id` |
| `votes` | `id`, `member_id`, `amendment_id`, `motion_id`, `choice`, `hash` |
| `members`  | `id`, `meeting_id`, `name`, `email`, `proxy_for` |
| `vote_tokens` | `token`, `member_id`, `stage`, `used_at` |
| `runoffs` | `id`, `meeting_id`, `amendment_a_id`, `amendment_b_id` |
| `amendment_conflicts` | `id`, `meeting_id`, `amendment_a_id`, `amendment_b_id` |
| `users` | `id`, `email`, `password_hash`, `role_id`, `is_active`, `created_at` |

---

## 8  System Architecture

```text
Nginx
  ↳ Gunicorn (Flask)
       ↳ Blueprints
            auth/
            meetings/
            voting/
            admin/
Postgres  ─── SQLAlchemy ORM
Redis (local container) ─── Celery tasks (emails, reminders)
Local storage ─── Static files & document exports (S3 optional)
SES/SMTP  ─── Outbound mail
````

---

## 9  UI Principles & Wireframe Notes

* **Single‑column mobile‑first** (cards).
* Breadcrumbs for stage navigation; persistent “Your vote” footer on vote pages.
* Use progressive disclosure: motion summary collapsible beside each amendment.
* Confirmation pages use a GOV‑UK style pattern (big green tick).
* Error banners top‑of‑page, never toast pop‑ups (screen‑reader friendly).

---

## 10  Work Breakdown – Epics → Tickets

### EPIC 1 App Skeleton

1. Initialise Flask app, blueprints, config loader.
2. Dockerfile + GitHub Actions CI.
3. User login & session management (bcrypt, Flask‑Login).

### EPIC 2 Meetings CRUD

4. Meeting model + migration scripts.
5. Coordinator UI (Create / Edit / List).
6. CSV import & validation form.

### EPIC 3 Voting Flows

7. Token generation & email dispatcher.
8. Stage 1 ballot page + submission endpoint.
9. Quorum checker & reminders.
10. Run‑off flow engine.
11. Stage 2 motion ballot.

### EPIC 4 Reporting

12. Tallies endpoint + RO download CSV.
13. Docx generation service.
14. Public results static page.

### EPIC 5 Hardening & Accessibility

15. CSRF & security headers middleware.
16. WCAG audit fixes + keyboard tests.
17. Pen‑test script (ZAP baseline).

> **Ticket sizing rule:** anything that would exceed one ChatGPT call or 150 LoC sprawl should be split again.

---

## 11  Risks & Mitigations

| Risk                             | Impact                   | Mitigation                                                           |
| -------------------------------- | ------------------------ | -------------------------------------------------------------------- |
| High voter load causing DB locks | Lost ballots             | Use row‑level locking & short transactions; pre‑warm connection pool |
| Email deliverability             | Members don’t get tokens | DKIM + SPF, SES dedicated IP pool                                    |
| Run‑off ties unresolved          | Governance dispute       | Implement Article 109 tie‑break logic exactly; manual override UI    |

---

## 12  Future Extensions (Post‑MVP)

* Member accounts + SSO with Sport80
* Multi‑federation tenancy
* Live vote tracker for conference‑room screens
* Shamir‑secret‑split vote encryption (advanced audit)
* React or Alpine upgrade if interaction grows

---

## 13  Living Document Process

* The file `docs/prd.md` is **source‑of‑truth**.
* Each merged PR must update either:

  * `## Changelog` section (append date + summary), or
  * Tick a checklist item under its Ticket header.
* CI pipeline fails if TODO count is zero but related branch not labelled `feature/complete`.

---

## Changelog
* 2025-06-13 – Simplified architecture: S3 optional; Redis containerised for local use.
* 2025-06-13 – Added Docker setup and initial database migrations with `.env.example`.
* 2025-06-13 – Added login redirection logic preserving the `next` parameter.
* 2025-06-13 – Added global X-Frame-Options header.
* 2025-06-13 – Created Flask blueprint skeleton and config structure.
* 2025-06-13 – Implemented login and session management with Flask-Login.
* 2025-06-13 – Styled login form with bp-btn-primary and labelled inputs.
* 2025-06-13 – Added CSRF protection via Flask-WTF
* 2025-06-13 – Introduced role-permission system and user management page.
* 2025-06-14 – Added meeting cards on admin dashboard with floating “Create Meeting” button.
* 2025-06-14 – Added Tailwind build setup for CSS and updated README.
* 2025-06-14 – Added secondary button, table, badge and card styles.
* 2025-06-14 – Added dotenv loading with SQLite fallback when `DATABASE_URL` is unset.
* 2025-06-14 – Added focus-visible outlines for buttons and links.
* 2025-06-15 – Implemented dark mode with optional theme toggle.
* 2025-06-14 – Expanded UI/UX design guidance with extended design patterns.
* 2025-06-14 – Implemented meetings list view with table layout.
* 2025-06-14 – Enhanced meetings list with htmx search and sort.
* 2025-06-20 – Added comment count badges and modal viewer on ballots; improved thank-you screen.
* 2025-06-14 – Added meeting create/edit form with CSRF protection.
* 2025-06-14 – Added member CSV import with token generation.
* 2025-06-14 – Implemented admin user create/edit flow with forms and routes.
* 2025-06-14 – Secured meeting management routes with new 'manage_meetings' permission.
* 2025-06-15 – Implemented email service sending voting links after member import.
* 2025-06-14 – Added contributor note about enforcing permissions on all new features.
* 2025-06-15 – Added basic voting routes with token verification and hashed vote storage.
* 2025-06-15 – Implemented stage-based voting flow with motion display and amendment handling.
* 2025-06-15 – Added motion categories, thresholds and options with new tables.
* 2025-06-15 – Added RO dashboard with quorum tracking, stage locking and CSV tallies download.
* 2025-06-15 – Enforced ballot open/close windows before accepting votes.
* 2025-06-15 – Added Stage 2 token generation, results summary page and DOCX export.
* 2025-06-15 – Added motion categories, thresholds and options with new tables.
* 2025-06-15 – Implemented run-off detection and automatic Stage-1 extension.
* 2025-06-15 – Added final results DOCX export compiling carried amendments and motion outcomes.
* 2025-06-15 – Fixed create meeting button link on meetings list page.
* 2025-06-15 – Amendments now record proposer and seconder with a 21‑day deadline and three‑per‑member cap.
* 2025-06-15 – Integrated run-off emails and tokens when closing Stage 1.
* 2025-06-15 – Added APScheduler reminders with configurable timing.
* 2025-06-15 – Proxy votes now store an additional record for the represented member and display a proxy banner.
* 2025-06-15 – Implemented public results visibility toggle and results page.
* 2025-06-15 – Corrected email invite links to use `/vote/<token>`.
* 2025-06-15 – Stage 2 ballot now shows compiled motion text with carried amendments.
* 2025-06-15 – Added audit log CSV download for Returning Officers.
* 2025-06-15 – Added manual Stage 2 merge screen with final text field.
* 2025-06-15 – Voting route rejects ballots when a stage is locked.
* 2025-06-15 – Run-off and reminder emails now link to `/vote/<token>`.
* 2025-06-17 – Stage 1 closing now voids the vote when quorum is not met.
* 2025-06-16 – Run-off invite emails now use `/vote/runoff/<token>` links.
* 2025-06-15 – Added `aria-describedby` error hints on admin and meeting forms.
* 2025-06-15 – Dashboard shows countdown to next reminder using badge design.
* 2025-06-15 – Added quorum percentage banner with countdown on dashboards.
* 2025-06-15 – Added branded 403 and 404 error pages.
* 2025-06-15 – Run-off service resolves tied amendment votes using chair/board decisions or amendment order.
* 2025-06-15 – Implemented run-off ballot route and template
* 2025-06-15 – Added Content-Security-Policy header restricting scripts/styles to self and the htmx CDN.
* 2025-06-15 – Introduced email opt-out via unsubscribe tokens and footer links.
* 2025-06-15 – Introduced role management pages secured by 'manage_users'.
* 2025-06-15 – Added help page explaining voting stages and token links.
* 2025-06-15 – Added OWASP ZAP baseline scan script for penetration testing.
* 2025-06-15 – Emailed vote receipt with ballot hash after members vote.
* 2025-06-15 – Vote tokens stored as SHA-256 hashes with server-side salt.
* 2025-06-15 – Sanitised help page HTML using Bleach to strip script tags.
* 2025-06-15 – Fixed floating “Create Meeting” button on admin dashboard link
* 2025-06-15 – DOCX exports styled with bp-blue header, bp-red headings, Gotham font and optional logo watermark.
* 2025-06-15 – Added sticky confirmation footer summarising selections on voting pages.
* 2025-06-15 – Added flash message banners and login/meeting alerts
* 2025-06-16 – Added Stage 2 closing route with motion status tally and public outcomes
* 2025-06-16 – Introduced root-admin-only settings for site title, logo and from-email.
* 2025-06-16 – Added site footer credit linking to Scorchsoft.
* 2025-06-16 – MeetingForm enforces minimum stage durations (7d/5d/1d gaps)
* 2025-06-16 – Added amendment conflict management UI with database links for combined amendments
* 2025-06-16 – Added iCalendar downloads for Stage 1 and Stage 2 windows
* 2025-06-16 – Added unit test covering multiple-choice motion voting and receipts
* 2025-06-16 – Added coordinator resend token route and email flow
* 2025-06-16 – Added Stage 2 motion tallies CSV download for Returning Officers
* 2025-06-16 – Added motion form options for clerical fixes and Articles/Bylaws placement
* 2025-06-16 – Added amendment edit/delete routes and template.
* 2025-06-16 – Added tallies JSON endpoint for Returning Officers
* 2025-06-16 – Added amendment objection workflow with admin reinstatement
* 2025-06-16 – Added board seconding option for amendments
* 2025-06-16 – Added meeting notice date with 14‑day opening validation.
* 2025-06-16 – Amendments capture seconded method and timestamp; exports include these fields.
* 2025-06-16 – Stage 1 closing now schedules Stage 2 close after the new open when no close was set.
* 2025-06-16 – Added `node_modules/` to `.gitignore` to ignore Node packages.
* 2025-06-16 – Documented Python package installation in README.
* 2025-06-16 – Added rate limiting to login and vote routes using Flask-Limiter.
* 2025-06-16 – Added skip link for keyboard users and assigned id="main" to content container.
* 2025-06-16 – Navigation drawer closes via Escape key for keyboard users.
* 2025-06-16 – Increased default rate limit to 1000 per day.
* 2025-06-18 – Added bp-pagination component and meeting list pagination.
* 2025-06-18 – Added SVG icons for the theme toggle and updated navigation script.
* 2025-06-18 – Vote invite emails now include calendar (.ics) attachments.
* 2025-06-19 – Added vote receipt verification page with lookup form.
* 2025-06-19 – Added public vote charts with JSON tallies endpoint.
* 2025-06-19 – Implemented tooltip styles for `[data-tooltip]` elements and dark mode.
* 2025-06-19 – Added discussion comments for motions and amendments with admin moderation.
* 2025-06-20 – Added CLI command `generate-fake-data` to seed demo meetings and members.
* 2025-06-20 – Meeting form auto-populates dates from AGM date with timing notes.
* 2025-06-20 – Added tooltip explaining quorum progress banner.
* 2025-06-20 – Documented `generate-fake-data` CLI usage and cautions in README.
* 2025-06-20 – Added admin preview route for voting screens.
* 2025-06-20 – Fixed motion view page when amendment seconder is null.
* 2025-06-20 – Motion creation form hides options unless "Multiple Choice" is selected and shows note about auto-added abstain.
* 2025-06-20 – Added "Site Settings" to the user dropdown and linked the RO Dashboard in navigation.
* 2025-06-20 – Updated navigation test for role badge markup.
* 2025-06-20 – Added manual email sending page with test mode and DB logging.
* 2025-06-20 – Added clearer member import button with downloadable sample CSV.
* 2025-06-21 – Added permission management pages secured by 'manage_users'.
* 2025-06-21 – Added amendment reject and merge controls on motion view page.
* 2025-06-20 – Added moderator control to toggle member commenting rights.
* 2025-06-21 – Removed unused `VoteForm` class and cleaned up voting routes.
* 2025-06-21 – Tie-break decisions from settings now apply automatically when Stage 1 closes.
* 2025-06-22 – Added Markdown preview for clerical and move text settings.
* 2025-06-22 – Added public meetings pages with resend link modal and contact URL setting.
* 2025-06-23 – Documented local PostgreSQL setup in README.
* 2025-06-23 – Rate limited public resend link form to prevent abuse.
* 2025-06-24 – Automatic quorum failure emails sent when Stage 1 closes below quorum.
* 2025-06-24 – Stage calendar downloads redirect with a flash when timestamps are missing.
* 2025-06-24 – Removed member vote weighting feature.
* 2025-06-23 – Added revoting banner and change-vote link on confirmation page when enabled.
* 2025-06-24 – Added run-off closing helper and route clearing tokens.
* 2025-06-20 – Stage 1 is skipped when no amendments exist by the deadline; Stage 2 tokens are generated.
* 2025-06-25 – Receipt checker warns when a hash matches multiple votes and footer now links to it.
* 2025-06-21 – Run-off ballots now respect a dedicated time window and can be closed early by the RO.
* 2025-06-26 – Combined ballot stepper now shows "Combined Ballot" label.
* 2025-06-26 – Objection form uses member autocomplete with `/meetings/<id>/member-search`.
* 2025-06-26 – Final results email dispatched with summary and DOCX attachment.
* 2025-06-27 – Amendments store merge/rejection reason displayed on motion view.
* 2025-06-26 – Added stage extension form and reason display on results page.
* 2025-06-30 – Run-off tie breaks recorded with chair/board/order option and service respects setting.
* 2025-06-28 – Objection submissions now require email confirmation via token link.
* 2025-07-01 – Public meeting page lists stage times with calendar downloads.



---

## 14  Glossary

* **Stage 1** – Separate votes on each amendment.
* **Stage 2** – Vote on final motion (amended).
* **Combined ballot** – Amendments + motion on one form.
* **Revoting** – Ability for members to change choice before stage close.
* **RO** – Returning Officer (independent scrutineer).
* **Token** – Unique UUIDv7 value included in email links; stored hashed with SHA-256 and a secret salt (see changelog entry 2025-06-15).

---

*Draft v0.1 – generated 13 Jun 2025.*
