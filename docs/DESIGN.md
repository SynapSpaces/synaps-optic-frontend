# DESIGN.md — Synapspaces

The design system for every Synapspaces surface. Source of truth: the `design-system/` folder in this repo (tokens, fonts, icons, React components).

> Values were measured from the production marketing site. Two things are still open: the logo files (not supplied, so the brand name is set in type) and a confirmation that the production font is Geist.

---

## 1. Setup

```
design-system/
  styles.css            ← import this once (tokens + fonts + base + .ss-* classes)
  tokens/               colors · typography · spacing · effects · fonts
  base/elements.css     element defaults + type utility classes
  fonts/                Geist + Geist Mono variable woff2 (SIL OFL)
  assets/icons/         Lucide SVGs in use
  components/<group>/   React components: <Name>.jsx + .d.ts (props) + .prompt.md (usage)
```

```js
import 'design-system/styles.css';
import { Button } from 'design-system/components/actions/Button.jsx';
```

The components use only React and CSS variables: no CSS-in-JS and no other dependencies.

---

## 2. Principles

1. **Ink on white.** `#0d0d0d` is the only brand colour. Colour otherwise comes from four flat pastel tints, and each tint stands for a product.
2. **One typeface.** Geist everywhere. Headings are Medium 500 with tight tracking; supporting copy is small and gray. The size contrast does the work.
3. **Flat.** One shadow in the whole system (the floating product card). No gradients, blur, textures or photography.
4. **Ruled rhythm.** Every page band has a full-bleed 1px `#ededed` rule on top and 100px vertical padding.
5. **Pills for actions.** Every button and chip is fully rounded.

---

## 3. Tokens

### Colour
| Token | Value | Use |
|---|---|---|
| `--ink` / `--fg-1` | `#0d0d0d` | Headings, names, primary buttons, inverse panels |
| `--fg-2` (`--gray-600`) | `#5d5d5d` | Body copy, meta, eyebrows, footer links |
| `--fg-3` (`--gray-500`) | `#8a8a8a` | Tags, step numerals, placeholders only |
| `--gray-50` / `--surface-card` | `#f5f5f5` | Tiles, secondary pills, chips, form panel |
| `--gray-100` / `--border-subtle` | `#ededed` | Section rules, dividers inside cards |
| `--gray-200` / `--border-default` | `#e5e5e5` | FAQ and list rules, progress track |
| `--fg-inverse-2` | `#b6b6b6` | Secondary text on ink |
| `--tint-blue` / `--product-cortex` | `#d8e3f1` | Cortex |
| `--tint-sand` / `--product-plexus` | `#eee4d5` | Plexus |
| `--tint-sage` / `--product-optic` | `#e0ebda` | Optic |
| `--tint-lilac` / `--product-research` | `#e8e0f2` | Research content |

Tints are only for large flat tiles. Never use them on text, borders or gradients. There are no success/error colours yet; ask before adding them.

### Type (Geist; Geist Mono for numerals)
| Role | Spec | Class |
|---|---|---|
| Display XL (hero h1) | 500 · 60/1.1 · −0.01em | `.ss-display-xl` |
| Display LG (closing h2) | 500 · 48/1.1 · −0.015em | `.ss-display-lg` |
| H2 (section) | 500 · 36/1.1 · −0.02em | `.ss-h2` |
| Lead (two-tone statement) | 500 · 32/1.25 | `.ss-lead` + `.ss-lead-muted` span |
| Title LG (cards) | 500 · 22/1.25 · −0.02em | `.ss-title-lg` |
| Title (rows) | 500 · 18/1.35 · −0.01em | `.ss-title` |
| Subtitle (hero) | 400 · 17/1.6 | `.ss-subtitle` |
| Intro | 400 · 15/1.65 | `.ss-intro` |
| Question / card header | 500 · 16/1.4 | `.ss-question` |
| Body / strong | 400 / 500 · 14 | `.ss-body` / `.ss-body-strong` |
| Body SM (descriptions) | 400 · 13/1.6 | `.ss-body-sm` |
| Caption (card body, bullets) | 400 · 12.5/1.6 | `.ss-caption` |
| Meta / label | 400 / 500 · 12/1.4 | `.ss-meta` / `.ss-label` |
| Micro / tag | 400 · 11 / 10 | `.ss-micro` / `.ss-tag` |
| Numeral | Geist Mono 400 · 11 | `.ss-numeral` |

Never uppercase, never letter-spaced eyebrows.

### Spacing & layout
- Content column `--container` **1040px**; nav row and hero panel `--container-wide` **1200px**; page gutter **40px**; nav height **56px**.
- Section padding **100px** (`--section-y`); hero top and mission **120px**.
- Card grid gap **20px**: 4-up 245 · 3-up 333 · 2-up 510.
- Split sections: **340px** label column + 24px gap. Two equal halves: 56px gap.
- Section header → content: **40px** (52px when there is an intro paragraph). Headers are bottom-aligned.
- Spacing scale: 4 8 12 16 20 24 28 32 40 48 64 80 100 120.

### Radii · elevation · controls
- Radius: pill 999 (buttons, chips) · 20 (hero / CTA panels) · 16 (cards, tiles, form panel) · 10 (inputs) · 8 (illustration widgets).
- Shadow: `--shadow-float: 0 20px 60px rgba(13,13,13,.11)`, only on the white floating product card.
- Heights: buttons 36 / 40 / 44 · inputs 44 · chips 27.
- Motion (inferred): 120–200ms colour/background transitions, `cubic-bezier(.2,0,0,1)`. No bounce.

---

## 4. Components

| Group | Components | Notes |
|---|---|---|
| actions | `Button`, `TextLink` | Button: `primary` (ink) · `secondary` (gray) · `inverse` (white on ink); sizes `sm` 36 / `md` 40 / `lg` 44. TextLink = "View all ›". |
| forms | `Field`, `Input`, `Select`, `Textarea` | White fields, no border, on the gray `#f5f5f5` panel. Pass `surface="page"` on white backgrounds. |
| display | `Chip`, `Tag`, `Eyebrow`, `BulletList` | Eyebrow `items={[a,b]}` joins with " · ". Bullets are 4px ink squares. |
| cards | `Tile`, `StepCard`, `ProductCard`, `PostCard` | Flat fills, 16px radius. StepCard `tone="ink"` marks the one active step. |
| lists | `Accordion`, `ListRow` | Hairline-ruled FAQ and definition rows. |
| navigation | `NavBar`, `Footer`, `Wordmark` | Wordmark is type-only until logo files arrive. |
| layout | `Section`, `SectionHeader`, `SplitLayout`, `CtaPanel` | They encode the page rhythm; use them instead of ad-hoc spacing. CtaPanel at most once per page. |
| product | `FloatingCard`, `NextMoveRow`, `ChecklistRow`, `ProgressBar` | Product UI excerpts shown on tinted panels. |
| icons | `Icon` | Lucide 2px stroke: chevron-right/down, plus, minus, rotate-cw, circle-play. |

Each component's props are in its `.d.ts`; each `.prompt.md` has a usage example. Not in the system yet: checkbox, radio, switch, tabs, dialog, toast, tooltip, avatar.

---

## 5. Content & voice

- Plain, specific, revenue-literate. Every claim names its mechanism; no hype words.
- **"We"** = Synapspaces, **"you / your team"** = the customer. Products act in the third person ("Cortex ranks…").
- **Sentence case everywhere.** No exclamation marks, no emoji.
- **" · "** separates paired metadata: "Revenue engine · For sellers and FDEs".
- Body sentences end in a period. Headlines, buttons and titles do not. Oxford comma.
- Patterns: *X, not Y* ("a ranked list, not a blank CRM") · rule of three · show the reason ("with the reason behind it").
- CTAs are verb-first, 2–3 words: Book a demo · Explore products · Request access · Get in touch.
- Product names: "Synaps Cortex / Plexus / Optic" in titles, "Cortex" in running copy.

---

## 6. Do / Don't

**Do:** flat tiles · hairline rules · large Medium headings over small gray copy · tints that match the product · one primary button per group.

**Don't:** gradients · drop shadows on cards · borders around cards · coloured text · icons in circles · emoji · Title Case · stock photography · more than one ink panel per page.

## 7. App shell (installable web app, 2026-10-30)

The site installs to a phone's home screen as a standalone app: `static/app/manifest.webmanifest` (name Synaps Optic, short name Optic, standalone, start at /projects, icons 192/512 + maskable 512 rendered from the three-node mark, `apple-touch-icon.png` 180), the iOS home-screen metas and the manifest link in `base.html`, and a service worker at `static/app/sw.js` that the backend serves at `/sw.js` with `Service-Worker-Allowed: /`. The worker caches the design system and shell cache-first (versioned by its VERSION constant: bump it with any change to those files), serves pages and htmx partials network-first, shows `static/app/offline.html` on a failed navigation, and never touches non-GET requests, /api, /auth, /admin or the music library. Install: iPhone = Safari share sheet, Add to Home Screen; Android = Chrome's install prompt. Native wrappers (Capacitor) are the backend plan's MOB-02/03.

## 8. Platform module pages (2026-10-31)

The platform modules (`/m/<slug>`, `/m/<slug>/items/<id>`, `/m/<slug>/board`, `/approvals`, `/brief`, plus a module's own pages such as `/m/hr/people`, `/m/accounting/ledger` and `/m/dev/integrations`; backend `platform_routes.py`) share the page shapes in `templates/platform/` plus `partials/platform_runs.html`. The nav in `base.html` lists every module from the `modules_nav` global, then Approvals, then Brief.

- **Module page**: eyebrow, `ss-h2` label and blurb, and in the header the secondary buttons "Ask the wiki" (when `has_ask`), "Board" (always) and one per entry of the module's `pages` ("People directory", "Ledger", "Integrations"); the new-item card (title, body, and for `knowledge` the "Policy page" checkbox); a filter row of `nav-link` pills (All · each status · Needs you · AI done, the current one `.active`); then one flat card per item linking to the item page, with its due date as `ss-meta` "due <date>" when it has one.
- **Item page**: back link, title and chip row (status, attention, kind chips, the due date, then `ss-meta` "owner <name>" and "assignee <name>" when known); a two-column body (edit form and runs on the left, status and agents cards on the right). The edit form carries the title, the body, a "Due" date input and an "Assignee" select of the workspace's members ("Unassigned" first). The main status button moves the item to `next_status`; approving is wrapped in the inline `.confirm` two-step, never `window.confirm`. Agent forms `hx-post` and swap `#platform-runs`, which polls every 3 s while a run is queued or running; a done run offers "Use this draft".
- **Board** (`/m/<slug>/board`, `platform/board.html`, the "Board" button in the module header): back link, eyebrow, `ss-h2` "<label> board", then one column per status in the module's order, side by side in a horizontally scrolling row (`flex gap-4 overflow-x-auto`, each column `min-w-[260px]`), headed by the status chip and the count as `ss-numeral`. Each card: the title linking to the item page; the attention chip; the due date as `chip-err` "due <date>" when overdue (past and not approved or done) else `ss-meta`; the assignee's name as `ss-meta` (or "unassigned"); the source chip on a read-only item. A writable card whose next status is not `approved` ends with a ghost "→ <next status>" button, a plain form posting `status` and `back=board` so the member lands on the board again; approving stays on the item page behind its confirm. Empty column text "Nothing here."
- **People directory** (`/m/hr/people`, `platform/people.html`, the "People directory" button in the hr header): back link, eyebrow, `ss-h2` "People directory" and the blurb "One person per member of this workspace; members appear here as they join. Open a person to draft their onboarding checklist." One card row per person linking to the person's item page: the title as `ss-body-strong`, the role as a plain `chip`, `ss-meta` "since <start date>" and, right-aligned, `ss-meta` "<done>/<total> onboarding items" or "no checklist yet". Empty state "No people yet. Members appear here as they join."
- **Ledger** (`/m/accounting/ledger?month=YYYY-MM`, `platform/ledger.html`, the "Ledger" button in the accounting header): back link, eyebrow, `ss-h2` "Ledger" and the blurb "Records only: expenses, invoices and revenue imported from CSV. Nothing here is advice."; after an import a `status-info` line "Imported N entries, skipped M already in the ledger." The import card is a multipart form posting to `/api/m/accounting/ledger/import`: a textarea for pasted rows, a `.csv` file input, three radios for the amount rule (statement, checked by default · all money out · all money in) and a primary "Import" button. Then the "Months" table (month linking to `?month=`, in, out, net and the entry count as `ss-numeral`, the selected month's row on the gray fill); for the selected month a "Categories in <month>" table (category, direction chip, total, count) and an "Entries in <month>" table (date, direction chip, amount with currency, category, description, counterparty, kind); then "Recent imports", one card link per import item with `ss-meta` rows · inserted · skipped and any parse problems. The direction chip is `chip-ok` for `in`, plain for `out`. Empty state "No entries yet. Paste or upload a CSV above."
- **Checklist / due date / assignee**: any item can carry `meta.checklist` ([{text, done}]), a `due_at` date and an `assignee_user_id`. A person item (hr, `meta.kind` `person`, synced from the members table but editable here) adds a plain `chip` "person" and a "Person" card (role chip, `ss-meta` "since <start date>" and the user id, with the one-line onboarding flow) above the edit form. The "Checklist" card (a person, or any item that already has a list) shows `ss-meta` "<done>/<total> done", then one row per item: a ghost "☑" / "☐" toggle form, the text (`line-through text-fg-3` when done) and a ghost "×" remove form, each a plain post to `/api/m/<slug>/items/<id>/checklist` with a hidden `action` (toggle, remove) and `index`; an "Add an item" input with a secondary "Add" button (`action=add`); and "Use the body as the checklist", wrapped in the inline `.confirm` two-step (question "Replace the checklist with the body's lines? Ticked items that keep their text stay ticked.", confirm button "Replace", `action=from_body`). A read-only item has no Checklist card.
- **Approvals page**: the same filter row and item rows across every module, with the module label as an eyebrow in each row. Empty state "Nothing waits on you."
- **Ask page** (`/m/<slug>/ask`, `platform/ask.html`, reached from the "Ask the wiki" secondary button in the module header when `has_ask`): back link, eyebrow, `ss-h2` "Ask <label>" and the one-line blurb; a question card whose form `hx-post`s to `/api/m/<slug>/ask` and swaps `#platform-ask-runs` (`partials/platform_ask_runs.html`, polling every 3 s like the runs partial). Each answer shows its question as `ss-body-strong`, the status chip row, the answer in the same `<pre>` as a run, then a **Sources** list: one `ss-body-sm` link per cited page, "[n] title", pointing at `/m/<module>/items/<id>`. The runs partial renders the same Sources list under a done run that cites pages. Empty state "No questions yet."
- **Read-only synced items**: an item with a `source` other than `manual` (pulled from a repo or another system) carries that source as a plain `chip` in the module list; its item page (`read_only`) shows the body in a `<pre>` with the note "Synced from <source>; read-only on this site." and an "Open the source" link to `external_url` when there is one, has no edit form and no Status card, and the runs partial hides "Use this draft". The Agents card stays, so an agent can still read and summarise it.
- **Owner brief** (`/brief`, `platform/brief.html`, the "Brief" nav item after Approvals): eyebrow "Platform · brief", `ss-h2` "Owner brief", the one-line blurb and a primary "Make today's brief now" button (a plain form posting to `/api/brief`). The newest brief is a card with its title as `ss-body-strong`, the status chip, an "Open" link to its knowledge item and the body in the same `<pre>` as a run; while the body is still empty the chip row shows the `chip-info` "being written" pulse and the whole `<section>` re-fetches `/brief` every 5 s (`hx-select="section"`, `hx-swap="outerHTML"`) until the text arrives. Earlier briefs follow as a list of card links (title, `ss-meta` date). Empty state "No brief yet. The first one arrives at the scheduled hour, or press the button." A brief is a knowledge item whose `meta.kind` is `brief`: its item page adds a plain `chip` "brief" and a "Brief" card with the body in a `<pre>` above the edit form, which stays so the owner can correct the text.
- **Markdown pages** (backend slice 01-05): the backend renders a knowledge page's markdown (raw HTML off) and hands the item page `body_html`; every other module passes `""`. When it is non-empty the item page shows a "Page" card, `ss-body-strong` "Page" over `<div class="md">` with the HTML printed as is, above the edit form (which keeps the markdown source in its textarea) and after the Brief / Person / Checklist cards; on a read-only synced doc the card replaces the `<pre>` body and keeps the "Synced from <source>; read-only on this site." note and the "Open the source" link under the rendered page. The `.md` rules sit in `base.html`'s style block in the ss-* voice: h1-h6 at 22 / 18 / 16 / 14 / 13 px with a top margin, paragraphs and lists at `.75rem` below, disc and decimal markers, links underlined on hover in the link colour, inline `code` on the field fill with the 6 px radius at `12px` mono, `pre` the same wrapping field-fill block the runs use, a `blockquote` with a 2 px left rule in `fg-2`, tables full width with `ss-meta` heads and a subtle row rule (`display: block; overflow-x: auto`, so they scroll instead of the page), `hr` as the rule and `img` at `max-width: 100%`. Nothing in a page can push the layout sideways on a phone.
- **Brief mentions**: the backend lists the items the latest brief names as `mentions` ([{module, module_label, id, title, why}], why one of `approved`, `done`, `waiting`, `money`; missing or empty on older contexts). When the latest brief has its text and the list is not empty, the brief card ends with `ss-meta` "Mentioned in this brief" and one row per item: the title as an `ss-body-sm` link to `/m/<module>/items/<id>` and a chip with the why word (`chip-warn` waiting · `chip-ok` approved, done · plain `chip` money). The block is omitted while the brief is still being written.
- **Integrations** (`/m/dev/integrations`, `platform/integrations.html`, the "Integrations" button in the dev header; backend slice 02-01): back link, eyebrow, `ss-h2` "Integrations" and the blurb "Bring your own account: a personal access token this workspace uses to read its repositories. Nothing is ever written to GitHub." When the server has no `INTEGRATION_TOKEN_KEY` (`configured` false) a `status-err` line "Integrations are not configured on this server: the owner must set INTEGRATION_TOKEN_KEY." sits under the header and the connect button is disabled. The GitHub card: `ss-body-strong` "GitHub" with `chip-ok` "connected as <account>" or a plain `chip` "Not connected"; when connected, `ss-meta` "scopes <scopes>", the repositories as plain chips, `ss-meta` "<n> open pull requests · polled every <m> min · last poll <time or never>", the last error in a `status-err` box, then a secondary "Sync now" form (`/api/m/dev/integrations/github/sync`) and a ghost "Disconnect" wrapped in the inline `.confirm` two-step (question "Forget the token? The items already synced stay but stop updating.", confirm button "Disconnect", posting to `/api/m/dev/integrations/github/delete`). The connect card is a plain post to `/api/m/dev/integrations/github` with autocomplete off: a password input `token` (placeholder naming the fine-grained permissions), a `repos` textarea (owner/name, one per line or comma-separated, prefilled with the connected repositories), a primary "Connect" button that reads "Update" once connected, the `ss-meta` note that the token is stored encrypted and only read, and an `ss-body-sm` how-to for a fine-grained token (Contents and Pull requests, read-only).
- **Pull requests as items**: the dev lane syncs each pull request and repository as a read-only dev item (`source` `github`, `external_url` its GitHub page). A pull request (`meta.kind` `pr`: repo, number, author, head, base, draft, checks, state) shows in the module list as a plain `chip` "pr", the checks chip, a plain `chip` "draft pr" when it is a draft and `ss-meta` "#<number> by <author>"; its item page adds the "pr" chip to the header and a "Pull request" card first on the left (rows Repo "<repo>#<number>", Author and Branch "<head> → <base>"; then the state chip, the checks chip, a plain `chip` "draft" and a secondary "Open on GitHub" button to `external_url`, opening in a new tab). A repository (`meta.kind` `repo`: default_branch, open_prs, private) shows a plain `chip` "repo" and `ss-meta` "<n> open" in the list, and on its page the "repo" chip and a "Repository" card (Branch, "<n> open pull requests", a plain `chip` private / public and the same button). Both cards render on read-only items, above the Body / Page card.
- **Start work** (backend slice 02-02, DEV-02): when the workspace has a GitHub connection the item page hands the template `work_repos` (the connected "owner/name" repositories; empty on a read-only item) and `work` (`item.meta.work`, None until work starts). The "Work" card sits in the right column between Status and Agents. Before work starts it is a plain form posting `repo` to `/api/m/<slug>/items/<id>/start-work`: a `select select-sm` of the repositories, a primary "Start work" button and the `ss-meta` note "Creates a branch and a brief file in the repo; nothing else changes." Once `work` is set (repo, branch, base, brief_path, branch_url, compare_url, started_at) the card shows `ss-meta` "Branch", the branch name as an `ss-body-sm` link to `branch_url`, `ss-meta` "<brief_path> in <repo>, from <base>" and a secondary "Open a pull request" link to `compare_url` (both in a new tab); the form is gone, and the header chip row and the module list gain a plain `chip` "branch".
- **Posting a review** (DEV-03): on a pull request item the runs partial receives `comment_agent` (the review agent's name; None or missing elsewhere). A done run of that agent with text ends with "Post as a comment" instead of "Use this draft": a secondary button wrapped in the inline `.confirm` two-step (question "Post this review as a comment on the pull request? It goes to GitHub under your token, and the agent never approves or merges.", Cancel / primary "Post"), a plain form posting to `/api/m/<slug>/runs/<id>/comment`. Once posted (`run.output.comment_url`, `run.output.commented_by`) the run shows `ss-meta` "Posted as a comment by <name>" and an `ss-body-sm` "View on GitHub" link to the comment, opening in a new tab. Runs of other agents, unfinished runs and runs without text offer nothing.
- **Linear** (backend slice 02-03, the same integrations page): a second card after the GitHub connect form, `ss-body-strong` "Linear" with `chip-ok` "connected as <account>" or a plain `chip` "Not connected". When connected (`linear`: external_account, teams, last_sync_at, last_error) the configured teams show as plain chips, or `ss-meta` "every team the key sees" when none was named; then `ss-meta` "<n> issues mirrored · polled every <m> min · last poll <time or never>", the last error in a `status-err` box, a secondary "Sync now" form (`/api/m/dev/integrations/linear/sync`) and a ghost "Disconnect" wrapped in the inline `.confirm` two-step (question "Forget the key? The items already mirrored stay but stop updating.", confirm button "Disconnect", posting to `/api/m/dev/integrations/linear/delete`). The connect card is a plain post to `/api/m/dev/integrations/linear` with autocomplete off: a password input `token` labelled "Personal API key" (placeholder "lin_api_… (a personal API key)"), a `teams` text input labelled "Teams" (comma-separated keys, empty = every team, prefilled with the connected teams joined by ", "), a primary "Connect" button that reads "Update" once connected (disabled without `INTEGRATION_TOKEN_KEY`), the `ss-meta` note "Issues of these teams become Product items; edits and status moves on the site go back to Linear. Nothing is deleted on either side." and an `ss-body-sm` how-to (Linear → Settings → Security & access → Personal API keys).
- **Issues as items**: the Linear lane mirrors each issue as a product item that stays editable (`source` `linear`, `meta.kind` `issue`: identifier, team, state, state_type, assignee, priority, linear_error; `external_url` the issue page). The module list shows a plain `chip` "issue" then `ss-meta` "<state>" and "<assignee>" when set. The item page (`is_issue`) adds the "issue" chip to the header and a "Linear issue" card first on the left: rows Issue "<identifier>", Team and Assignee (when set); then the state chip (`chip-ok` for a completed or canceled `state_type`, `chip-warn` started, plain otherwise), `ss-meta` "priority <n>" when above 0 and a secondary "Open in Linear" button to `external_url` in a new tab; when `meta.linear_error` is set a `status-err` box reads "Linear refused the last change: <error>". The edit form and the Status card stay: edits and status moves go back to Linear. A manual editable item of any module receives `linear_teams` while Linear is connected (the configured team keys, possibly empty): a "Linear" card in the right column after Work, a plain form posting `team` to `/api/m/<slug>/items/<id>/linear` (a `select select-sm` of the keys, or an `input input-sm` "Team key, like OPT" when none was configured), a secondary "Create in Linear" button and the `ss-meta` note "Makes a Linear issue from this item; it then mirrors both ways." Issues and read-only items never show it.

Chips on these pages are the app status pills from `base.html`, never coloured text:

| Chip | Class | Meaning |
|---|---|---|
| status | `chip` (draft) · `chip-warn` (review) · `chip-ok` (approved, done) · `chip-err` (failed) | the item's or run's lifecycle state; a queued run reads "queued, N ahead" |
| attention | `chip-warn` "Needs you" · `chip-info` "AI done" | what waits on a member vs what an agent just finished |
| policy | plain `chip` "policy" | a knowledge item whose `meta.kind` is `policy`: rules every agent reads first |
| source | plain `chip` with the source name | an item synced from elsewhere and owned there (`read_only`, e.g. `repo`); a person (`members`) is synced too but editable, so it shows no source chip |
| brief | plain `chip` "brief" · `chip-info` "being written" | a knowledge item whose `meta.kind` is `brief` (the daily owner brief); the pulse chip while its body is still empty |
| person · import | plain `chip` "person" · plain `chip` "import" | an hr item whose `meta.kind` is `person` (one per member) · an accounting item whose `meta.kind` is `ledger_import` (the rows of one CSV import) |
| due | `chip-err` "due <date>" · otherwise `ss-meta` "due <date>" | a due date in the past on an item not yet approved or done (overdue) · any other due date, which is text, not a chip |
| direction | `chip-ok` "in" · plain `chip` "out" | a ledger entry's or category's money direction |
| why | `chip-ok` "approved" / "done" · `chip-warn` "waiting" · plain `chip` "money" | why the brief mentions an item: it was approved or finished, it waits on a member, or it is a money record |
| pr · repo | plain `chip` "pr" · plain `chip` "draft pr" (list) / "draft" (item page) · plain `chip` "repo" | a dev item synced from GitHub: a pull request (`meta.kind` `pr`), its draft flag, or a repository (`meta.kind` `repo`) |
| checks | `chip-ok` "checks pass" · `chip-err` "checks fail" · `chip-warn` "checks running" · nothing for `none` or missing | the combined result of a pull request's checks (`meta.checks` success / failure / pending / none) |
| pr state | `chip-warn` "open" · `chip-ok` "merged" · plain `chip` "closed" | the pull request's state on its item page; a repository's visibility is a plain `chip` "private" / "public" there |
| branch | plain `chip` "branch" | an item whose work has started on a branch (`meta.work`): shown in the module list and the item header, with the Work card holding the links |
| issue · issue state | plain `chip` "issue" · `chip-ok` (completed, canceled) · `chip-warn` (started) · plain `chip` otherwise, reading the Linear state name | a product item mirrored from Linear (`meta.kind` `issue`), shown in the module list and the item header; the state chip (`meta.state` toned by `meta.state_type`) sits on the "Linear issue" card |
