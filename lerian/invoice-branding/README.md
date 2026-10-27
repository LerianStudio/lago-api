# Lerian invoice branding

Fork patch `lerian-invoice-branding` (see `.lerian-fork.yml`). It rebrands the
customer-facing invoice PDF that Lago renders from
`app/views/templates/invoices/v4.slim` and its `v4/` partials, for invoices
issued to Lerian Clients. Upstream Lago OSS has no per-organization template
customisation, so the template itself is patched.

The templates under `app/views/templates/invoices/` are **generated**. Do not
edit them by hand: change `build_template.py` and regenerate.

## What changes in the PDF

Every root invoice template Lago picks (`Invoices::GeneratePdfService#template`)
gets the brand: `v4.slim` (subscription and progressive billing invoices) and
the standalone `v4/one_off.slim`, `v4/charge.slim` (pay-in-advance charges),
`v4/fixed_charge.slim` and `v4/self_billed.slim`. The other `v4/` partials only
get aligned amount cells, plus grouped breakdown rows in `_subscription_details.slim`.

- Inter and IBM Plex Mono are embedded as base64 `@font-face` (no network
  fetch at render time); colours move to zinc neutral tokens, with yellow
  `#FACC15` used only as a thin rule under table heads and on the due-date chip.
- Header card with the Lerian wordmark (`billing_entity.logo` wins when the
  billing entity has one) and the document kind; the invoice number becomes the
  title.
- Status, issuing-date and due-date chips. The status label is pt/en
  (`Pendente`/`Pending`, `Pago`/`Paid`, `Falhou`/`Failed`), and voided invoices
  read `Cancelada`/`Voided`.
- Amount panel labelled `Total`. The line upstream shows under the amount (the
  due date, or `invoice.already_paid` for advance charges) moves into the
  accent chip.
- `self_billed.slim` keeps its legal self-billing statement and, like upstream,
  shows no billing entity logo (only the Lerian wordmark).
- Every table amount is rendered by `MoneyHelper.cell`, defined once in
  `app/views/helpers/money_helper.rb` (part of this patch, not generated, with
  unit specs in `spec/views/helpers/money_helper_spec.rb`). It takes a Money or
  an already formatted String plus an optional sign, and splits it into
  `<span class="money"><span class="cur">BRL</span><span class="num">1.234,56</span></span>`
  (inline-grid, 11ch number column) so currency codes and decimals line up
  across all tables. In the partials, `td` cells whose whole content is a
  `MoneyHelper.format` / `FeeDisplayHelper.format_*` call are rewritten to it.
  Living in Ruby, it is available to every renderer, including the standalone
  `v4/{one_off,charge,fixed_charge,self_billed}.slim` templates that Lago uses
  for one-off, pay-in-advance charge, fixed-charge and self-billed invoices
  and that never go through `v4.slim`.
- 5-column fee tables use `table-layout: fixed` (38/8/19/16/19 %) and
  `calc(100% - 1px)` so mono amounts never clip.
- `billing_entity.invoice_footer` is rendered as a `Dados de pagamento` /
  `Payment detail` block; the `_powered_by_logo` partial is no longer rendered.
- The brand footer is page chrome, not part of the body: see below.
- The recurring fees breakdown of `v4/_subscription_details.slim` (recurring
  `sum_agg` / `unique_count_agg` charges paid in arrears) prints one row per
  date, action and duration, with the amounts summed, in both loops (fees with
  filters and fees without group, never merging rows across fees). Upstream
  prints one row per breakdown item, i.e. one `+1` row per distinct value of a
  unique count metric, which turned a production invoice into 201 pages.
  Presentation only: the breakdown, fees and totals are unchanged, and a fee's
  rows sum to the same amount. A row reads `<count> × <item>` (`562 × Conta
  Ativa`, `-3 × Conta Ativa` for removals, `+/-N × <item>` for items added and
  removed), also for a single item: the item name is free text from the plan,
  so it is never inflected. Its date and amount cells read as ink text, not as
  the muted uppercase `.body-1` section label.

## Page footer

`app/views/templates/documents/footer.slim` is also generated. It is the
`footer.html` part that `Utils::PdfGenerator` posts to Gotenberg, a mechanism
taken from upstream PR #6489 (commit `0447828b7`, first released in v1.54.0,
cherry-picked onto this fork, see `.lerian-fork.yml`). Chromium renders it in
the bottom margin of every page, so the footer can no longer land alone on a
new page when the content ends near the page bottom, and multi-subscription
invoices carry it on every page instead of page 1 only. Until lerian.4 it was
an in-flow `.brand-footer` at the end of the body; the generator no longer
emits it.

Left: the Lerian wordmark, the billing entity legal name (or name) and email.
Right: `Lerian Clients · Billing`, then the document reference
(`<document name> <number> · <issuing date>`) and the localized
`document.page_numbering` counter (`Página n de N`). Credit notes and payment
receipts render the same footer; methods only invoices have are guarded with
`respond_to?`, so a credit note shows `<number> · <issuing date>` and a
payment receipt `<number>`, both followed by the counter.

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
  not loaded yet is invisible (block period): a footer rendered on its own
  showed only the wordmark, and it only worked inside Lago because the body
  had loaded the same data fonts first. Inter lists `local("Inter")` first
  (the Gotenberg image ships Inter-Regular.ttf) with the data: url as
  fallback; the image has no IBM Plex Mono, so its data: url comes first, with
  `local()` after it, and the stack is
  `'IBM Plex Mono', 'DejaVu Sans Mono', monospace`.
- Gotenberg 8 does not apply `scale: 1.28` to the footer, so every value is
  the former in-flow design value multiplied by 1.28. Gotenberg 7.8.2 (the
  local `billing-worker-lago` pin) does scale it, so a render there is not
  representative: validate the footer on Gotenberg 8.15, the version
  production runs. It is always two lines
(`nowrap`, a long legal name is ellipsized), so its height is fixed:
1px rule + 7.68px top + 2 x 14.08px lines + 15.36px bottom = 52.2 CSS px
(0.544in). Chromium draws the footer inside the bottom page margin, measured
from the page edge, so `marginBottom` in `Utils::PdfGenerator` is 0.66in
(63.4px): the footer plus about 11px between the last body line and the rule
(the 8px design gap the in-flow footer had, x 1.28). Upstream uses 0.6in for
its one-line, 43.2px footer.

All Lago data logic (fees, taxes, coupons, credit notes, custom sections, EU
tax, progressive billing) is untouched: only markup, CSS and the presentational
`MoneyHelper.cell` change.

## Regenerate

```sh
python3 lerian/invoice-branding/build_template.py
```

Stdlib-only Python 3. The script reads `upstream.sha` from `.lerian-fork.yml`,
takes the pristine upstream `v4.slim` and `v4/*.slim` with `git show <sha>:<path>`
(the commit is an ancestor of the release line, so it is present in any
non-shallow clone; on a shallow one, fetch it first),
and overwrites `app/views/templates/invoices/v4.slim` and `v4/` in place.
Partials without amount cells are written back unchanged.

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
The script asserts that the header, amount and footer blocks it replaces still
exist upstream; if one of those assertions fails, the upstream template moved
and the generator needs to follow it.

## How it was validated

On 2026-10-26, on a local Lago v1.51.0 with the generated templates mounted
over the image's, 28 invoices shaped like production ones were rendered to PDF,
including a usage invoice with two billing-period groups and an
English-locale customer. Column alignment of currency codes and decimals was
measured with `pdftotext -bbox` across all tables.

The generator in this directory was then re-validated on the same local Lago
with the branch files mounted (templates and `money_helper.rb`): the 28
subscription invoices regenerated without errors, and a one-off invoice, a
pay-in-advance charge invoice (also with the `already paid` path) and a
self-billed render were produced in pt-BR, with every amount column sharing one
right edge (within 0.1pt). A fixed-charge invoice was not rendered (no fixed
charge data locally); its template only differs from `charge.slim` in the data
partials.

Not covered by that render (the partials are converted, but no invoice
exercised them): graduated, package, percentage and volume charge models,
taxes above zero, coupons, credit notes, pricing units and progressive billing.

On 2026-10-27, 18 invoices shaped like the production ones were rendered with
1.51.0-lerian.3. The usage invoice with two billing-period groups ended page 1
about 43pt short of room for the payment block and brand footer, which moved
alone to page 2. 1.51.0-lerian.4 removes 90px of vertical spacing from that
shape (76px from single-period invoices): header card, title, chips, block
margins (`.mb-24`, `.mt-24` between period groups, the payment block), amount
panel, table head cells, totals rows and footer. Font sizes, line heights,
column widths and horizontal padding are unchanged.

1.51.0-lerian.4 then moved the brand footer to the Gotenberg page footer
(above). Locally, the generator was run twice (the second run leaves the tree
unchanged), the invoice snapshots changed only by the removed in-flow footer,
and `spec/services/utils/pdf_generator_spec.rb` plus
`spec/views/app/views/templates/documents/footer.slim_spec.rb` cover the
footer posted to Gotenberg for an invoice, a credit note and a payment
receipt. The PDF render of the production-shaped invoices, the stress
scenarios (wrapped legal name, five-line payment detail) and a
multi-subscription invoice is done outside this repository.

## Assets and licences

- `fonts/inter-400-normal.woff2`: Inter, SIL Open Font License 1.1 (Google Fonts).
- `fonts/ibm-plex-mono-{400,600}-latin.woff2`: IBM Plex Mono, SIL Open Font
  License 1.1 (Google Fonts).
- `lerian-logo.png`: the Lerian wordmark, property of Lerian. Not covered by
  the repository licence.
