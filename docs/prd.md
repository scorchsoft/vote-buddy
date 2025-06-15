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
* CSV import **per meeting** (`member_id, name, email, vote_weight, proxy_for`)  
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
1. Opens e‑mail, clicks personal URL (JWT token bound to meeting+stage).  
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
* Fields: `id`, `title`, `type` (AGM / EGM), `opens_at_stage1`, `closes_at_stage1`, `opens_at_stage2`, `closes_at_stage2`, `ballot_mode`, `revoting_allowed`, `status`, `chair_notes_md`.

### 5.2 Member Import & Token Generation
* CSV validation (header check, duplicate e‑mail detection).  
* For each row create `Member` + `VoteToken` (UUIDv7).  
* Email template uses Django‑style placeholder tags.

### 5.3 Voting Engine
* Each `Vote` persisted with `hash(member_id + choice + secret_salt)` for tamper‑evidence.  
* Vote weighting field (for future parity with Sport80).  
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

### 5.7 Proxy Voting Support (MVP Lite)
* CSV may include `proxy_for` (member_id).  
* During vote cast, if member is proxy holder the UI shows extra banner and logs both votes.

---

## 6  Non‑Functional Requirements

### 6.1 Security
* HTTPS only (HSTS pre‑load).  
* JWT tokens scoped to meeting + stage; expire at stage close.  
* CSRF tokens on all POST; `X-Frame-Options: DENY`.
* All user input sanitised (Bleach) to prevent XSS.
* Automated dependency scanning (GitHub Dependabot).
* Pen‑test checklist aligns with OWASP Secure Coding Guide.
* Every feature must enforce role permissions on pages and endpoints
  using `permission_required` to guard access.

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
| `members`  | `id`, `meeting_id`, `name`, `email`, `proxy_for`, `weight` |
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
* 2025-06-14 – Expanded UI/UX design guidance with extended design patterns.
* 2025-06-14 – Implemented meetings list view with table layout.
* 2025-06-14 – Enhanced meetings list with htmx search and sort.
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
* 2025-06-15 – Addeed motion categories, thresholds and options with new tables
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
* 2025-06-16 – Added audit log CSV download for Returning Officers.
* 2025-06-15 – Added manual Stage 2 merge screen with final text field.
* 2025-06-15 – Voting route rejects ballots when a stage is locked.
* 2025-06-15 – Run-off and reminder emails now link to `/vote/<token>`.
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
* 2025-06-16 – Added sticky confirmation footer summarising selections on voting pages.
* 2025-06-16 – Added flash message banners and login/meeting alerts



---

## 14  Glossary

* **Stage 1** – Separate votes on each amendment.
* **Stage 2** – Vote on final motion (amended).
* **Combined ballot** – Amendments + motion on one form.
* **Revoting** – Ability for members to change choice before stage close.
* **RO** – Returning Officer (independent scrutineer).

---

*Draft v0.1 – generated 13 Jun 2025.*
