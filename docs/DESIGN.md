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
