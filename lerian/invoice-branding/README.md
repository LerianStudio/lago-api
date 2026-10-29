# Lerian invoice branding

Fork patch `lerian-invoice-branding` (see `.lerian-fork.yml`). It rebrands the
customer-facing invoice PDF that Lago renders from
`app/views/templates/invoices/v4.slim` and its `v4/` partials, for invoices
issued to Lerian Clients. Upstream Lago OSS has no per-organization template
customisation, so the template itself is patched.

The templates under `app/views/templates/invoices/` and
`app/views/templates/documents/footer.slim` are **generated**. Do not edit them
by hand: change `build_template.py` and regenerate.

## Design

Since 1.51.0-lerian.5 the PDF follows the Sindarian UI design system
(`console-sdk/packages/sindarian-ui`, light theme, `globals.css`), the identity
Console and Lerian Clients use, with the structure of the Lerian reference
invoice. When the two disagree the design system wins:

- Inter only, weights 400/500/600/700, embedded as base64 woff2. No mono family:
  numbers use `font-variant-numeric: tabular-nums`.
- Sentence-case labels, no uppercase eyebrows or letter-spaced caps.
- Zinc neutrals: `#3F3F46` text, `#52525B` labels and table heads, `#6E6E77`
  muted, `#E4E4E7` borders.
- Yellow `#FEED02` in two places only: an 80×3px segment at the left end of the
  header rule, and the final total in Total (a chip with `#09090B` text,
  4px radius).
- Sindarian tables (head row with a bottom border only, no fill, 500 weight;
  hairline body rows, no zebra; numbers right-aligned) and the Sindarian status
  badge: pending → alert, paid → success, failed → destructive, voided →
  inactive.

## What the PDF looks like

Every root invoice template Lago picks (`Invoices::GeneratePdfService#template`)
gets the same composition: `v4.slim` (subscription and progressive billing
invoices) and the standalone `v4/one_off.slim`, `v4/charge.slim` (pay-in-advance
charges), `v4/fixed_charge.slim` and `v4/self_billed.slim`.

- **Header**: the Lerian wordmark (`billing_entity.logo` wins when the billing
  entity has one; `self_billed` never shows it, as upstream), then
  `document_invoice_name`, the number and the status badge. Below it, a 1px rule
  with the yellow segment.
- **Left rail**: every section has its title, without a number, in a 98px CSS
  (≈94pt) column, with the content from ≈136pt. Sections are separated by a hairline.
  - `Summary`: `Amount due` (24px, ISO code as a muted suffix; `Total` when
    the invoice is paid or voided; 18px from 1,000,000.00 up, and the column
    grows past its 40% rather than run under the due date), `Due date` with `Net N days` (or
    `Already paid` for advance charges), `Issued`. Document references follow
    as a second row of the same label-over-value cells (label 500 muted, value
    12px like the dates), 40/30/30 under the three columns and wrapping every
    three: the purchase order (`Purchase order`), then the customer's
    displayable metadata in creation order, the label as typed in Lago. A
    metadata value with the digits of the customer's legal number or tax id is
    skipped (that identity is already in Parties). Without references the row
    is not rendered. The whole section, references and rail included, sits on
    the surface of the badge's status family: pending (alert) `#FEFCE8`, failed
    (destructive) `#FEF2F2`, paid (success) `#F0FDF4`, voided (inactive)
    `#F4F4F5`. Already-paid advance charges take the paid surface (unless
    voided). The due date gets the yellow chip of the Total only while the
    payment is pending or failed.
  - `Parties`: `Bill to` then `From`, the upstream columns carried over as
    they are (for `self_billed`, the billing entity is `Bill to` and the partner
    is `From`). Identity only: name, legal number, address, email and tax id,
    exactly upstream's lines; the document references live in Summary.
  - `Charges`: one table, `Description | Qty | Unit price | (Tax rate) |
    Amount (<currency>)`. The currency is printed once, in the head; amounts are
    bare numbers. Billing periods are group rows (`Usage · <from> – <to>`,
    `Subscription · …`, `Subscription and usage · …`). Every upstream row kind
    keeps rendering, restyled. The tax rate column is left out when no tax
    applies to the invoice (every fee would read `0.0%`; Total keeps the tax
    row, named with the upstream `invoice.tax` key: `Imposto (0%)` in pt-BR,
    where upstream hardcodes `Tax`). The only section that breaks across pages.
  - `Total`: right-aligned block of the upstream totals rows, hairlines
    between them, the final total in the accent chip. Moves to the next page
    whole rather than split.
  - `Notes`: the recurring-breakdown notice (not prorated / prorated), EU tax
    statements, the usage threshold sentence, custom sections, the billing
    entity `invoice_footer` as `Payment detail` (`self_billed`: its legal
    self-billing statement), and `Please reference <number> on your payment.`
    Moves to the next page whole, so `Payment detail` never ends a page alone.
  - `Usage by day`, after Notes: see below.
- **Multi-subscription invoices**: page 1 has the subscriptions summary in
  Charges and Total; then one page per subscription (rail `Details`), with its charges, its
  total and, if any, its usage-by-day table in flow.
- Labels come from `lerian.invoice.*` keys in `config/locales/<locale>/document.yml`
  (en and pt-BR translated; the other locales carry the English copy so nothing
  raises `translation missing`).

### Sections from one render: the markers

The fee partials render the charges table, the totals and the recurring
breakdown in one go, while the layout puts them in different rail sections. The
partials therefore emit HTML comment markers between those blocks
(`<!--lerian:sub-->`, `total`, `appendix`, `presentation`, `notice` /
`notice-end`). The root renders the partial once into a String and splits it at
the markers. Nothing is rendered twice, and every block keeps its place in the
upstream data flow.

### Amounts: `MoneyHelper.cell`

`MoneyHelper.cell` (`app/views/helpers/money_helper.rb`, hand-maintained, specs in
`spec/views/helpers/money_helper_spec.rb`) takes a Money or an already formatted
String and renders the bare number, because the column head carries the currency.
A fiat currency (ISO code or symbol) is dropped. Any other unit, i.e. a pricing
unit short name (`12.00 CREDITS`), stays as a suffix. With `code: true` the ISO
code stays as a suffix (amount due, total chip). The number is exactly what
`MoneyHelper.format` produced: same function, same rounding. In the partials,
`td` cells whose whole content is a `MoneyHelper.format` / `FeeDisplayHelper.format_*`
call are rewritten to it.

### Usage by day (appendix)

The recurring fees breakdown of `v4/_subscription_details.slim` (recurring
`sum_agg` / `unique_count_agg` charges paid in arrears) becomes an appendix
section after Notes: it starts on the same page when it fits and moves whole to
the next page otherwise (on a multi-subscription invoice it stays in flow on each
subscription page). Upstream prints one row per breakdown item, i.e. one `+1` row per
distinct value of a unique count metric, which turned a production invoice into
201 pages. The appendix prints one row per date, action and duration, with the
amounts summed, never merging rows across fees. The rows are split in two halves
side by side, with columns `Date | Days active | <item>`. The item is the fee's
`item_name`, free text from the plan, never inflected. A `Total` row prints the
fee units. A usage fee that has such an appendix shows `Daily detail in
Usage by day` under its name in Charges. Presentation only: the breakdown,
fees and totals are unchanged. Charge filter presentation breakdowns keep
their own page, as upstream.

## Page footer

`app/views/templates/documents/footer.slim` is also generated. It is the
`footer.html` part that `Utils::PdfGenerator` posts to Gotenberg, a mechanism
taken from upstream PR #6489 (commit `0447828b7`, first released in v1.54.0,
cherry-picked onto this fork, see `.lerian-fork.yml`). Chromium renders it in
the bottom margin of every page of invoices, credit notes and payment receipts.

On the left the wordmark and, next to it, the legal name above the email (the
email falls back to `lerian.studio`), a two-line block centred on the wordmark; on the right `<number> · <localized document.page_numbering>`
(`Page n of N`, `Página n de N`). Credit notes and payment receipts have
`number` and `billing_entity` too, so they render the same footer. A single
`<legal name> · <email>` line next to the wordmark never read as centred on it
(the wordmark's ink sits on the image's bottom edge), hence the stacked block.

Chromium constraints the footer follows:

- It is an isolated document, so every style is in its own `<style>` with an
  explicit size, line height and colour on each text node (an unstyled footer
  renders at zero size), and the wordmark is base64.
- Chromium injects its own stylesheet into header and footer templates, with
  rules for `.left`, `.center`, `.right`, `.date`, `.title`, `.url`,
  `.pageNumber` and `.totalPages`. Our layout classes must avoid those names:
  with `.left`, Chromium's padding pushed the wordmark and legal name 24pt to
  the right of the hairline. The left column is `.brand`; only the counter
  spans keep `.pageNumber` / `.totalPages`, which Chromium fills.
- Every `@font-face` has `font-display: swap`. Without it, text whose font is
  not loaded yet is invisible (block period). Inter lists `local()` first
  (the Gotenberg image ships the Inter family), with the data: url as
  fallback; weights 400 and 500 only.
- Gotenberg 8 does not apply `scale: 1.28` to the footer, so every value is the
  body design value multiplied by 1.28 (9px text → 11.52px). Gotenberg 7.8.2
  (the compose default) does scale it, so a render there is not
  representative: validate the footer on Gotenberg 8.15, the version
  production runs. Every line is `nowrap` (a long legal name is ellipsized),
  so its height is fixed: 1px rule + 10.24px top + 2 × 14.08px lines + 12.8px
  bottom = 52.2 CSS px (0.54in). Chromium draws the footer inside the bottom
  page margin, anchored at the page edge, so `marginBottom` in
  `Utils::PdfGenerator` is 0.66in (63.36px): the footer plus about 11px between
  the last body line and the rule (as lerian.4, whose footer was two lines too;
  upstream uses 0.6in).

The body uses Gotenberg's `scale: 1.28` and the 0.42in side and top margins as
before; 12px of body padding puts the content edge at 42pt, as in the reference.

## Regenerate

```sh
python3 lerian/invoice-branding/build_template.py
```

Stdlib-only Python 3. The script reads `upstream.sha` from `.lerian-fork.yml`,
takes the pristine upstream `v4.slim` and `v4/*.slim` with `git show <sha>:<path>`
(the commit is an ancestor of the release line, so it is present in any
non-shallow clone; on a shallow one, fetch it first), and overwrites
`app/views/templates/invoices/v4.slim` and `v4/` in place.

- Root templates: the upstream stylesheet is replaced, and the body is composed
  from the upstream body's fragments. The parties columns, the fee partial
  dispatch (`== render` becomes a capture), the notes partials and the footer
  text are carried over. The script asserts every fragment it relies on, and
  that nothing of the upstream body is left unaccounted for.
- Partials: upstream with presentational edits only (amount cells, column heads,
  period group rows, section markers, the appendix block, the daily-detail line,
  the custom sections spacing). Partials without such edits are written back
  unchanged.

The page footer comes from upstream #6489. `FOOTER_SHA` in the script is the
upstream commit (`0447828b7`), the identity of the patch; that object is not
reachable from any fork ref, so the script resolves the file at run time:

1. the fork's cherry-pick of it, found by its `git cherry-pick -x` line
   (`git log --all --grep="cherry picked from commit <FOOTER_SHA>"`, first
   match), whose sha changes on every rebase;
2. otherwise `FOOTER_SHA` itself, present once the fork is on an upstream
   release that contains #6489;
3. otherwise it exits non-zero and asks for
   `git fetch https://github.com/getlago/lago-api.git 0447828b740d70a4417f9e15fae04e42f07f6f3e`.

Once the fork moves to an upstream release that contains #6489 (>= v1.54.0),
point `FOOTER_SHA` at `upstream.sha` and drop the cherry-pick.

On every upstream bump: update `upstream.sha`, run the script, review the diff,
run `bundle exec rspec spec/views/app/views/templates/invoices`, update the
snapshots only after reading their diff, and re-validate a real render (below).
If one of the script's assertions fails, the upstream template moved and the
generator needs to follow it.

## How it was validated

1.51.0-lerian.5, on 2026-10-28: a local Lago v1.51.0 with Gotenberg 8.15
rendered the generated templates, helpers, `pdf_generator.rb` and locales of
the branch. Eight invoices shaped like production ones were rendered: the
two-period usage invoice with a recurring unique-count breakdown, a BYOC
invoice, a one-off, a zero-amount paid invoice, a BRL 4.49 invoice, two
multi-subscription invoices (2 and 7 subscriptions, one of them voided) and a
pt-BR single-subscription invoice. The same invoices were rendered with the
lerian.4 templates as the baseline. For every invoice, the money values that
`pdftotext -layout` extracts from the PDF are the same multiset as in the
lerian.4 PDF. `pdffonts` lists Inter only, and the page counter appears once on
every page. The two-period usage invoice keeps every section up to Notes on page 1
(3 pages → 2).

Not covered by those renders (no local data): graduated, package, percentage
and volume charge models, taxes above zero (the tax rate column), coupons,
fixed charges, pay-in-advance charge and self-billed roots, a failed payment
badge, the in-flow appendix of a multi-subscription invoice, and credit notes
and payment receipts with the new footer. rspec was not run (no runner in this
environment): the invoice view snapshots must be regenerated.

## Assets and licences

- `fonts/inter-{400,500,600,700}-latin.woff2`: Inter (fontsource 5.1.0, latin
  subset), SIL Open Font License 1.1.
- `lerian-logo.png`: the Lerian wordmark, property of Lerian. Not covered by
  the repository licence.
