# Lerian invoice branding

Fork patch `lerian-invoice-branding` (see `.lerian-fork.yml`). It rebrands the
customer-facing invoice PDF that Lago renders from
`app/views/templates/invoices/v4.slim` and its `v4/` partials, for invoices
issued to Lerian Clients. Upstream Lago OSS has no per-organization template
customisation, so the template itself is patched.

The templates under `app/views/templates/invoices/` are **generated**. Do not
edit them by hand: change `build_template.py` and regenerate.

## What changes in the PDF

- Inter and IBM Plex Mono are embedded as base64 `@font-face` (no network
  fetch at render time); colours move to zinc neutral tokens, with yellow
  `#FACC15` used only as a thin rule under table heads and on the due-date chip.
- Header card with the Lerian wordmark (`billing_entity.logo` wins when the
  billing entity has one) and the document kind; the invoice number becomes the
  title.
- Status, issuing-date and due-date chips. The status label is pt/en
  (`Pendente`/`Pending`, `Pago`/`Paid`, `Falhou`/`Failed`), and voided invoices
  read `Cancelada`/`Voided`.
- Amount panel labelled `Total`, without the due date (it is in the chips).
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
  `Payment detail` block; the `_powered_by_logo` partial is no longer rendered;
  a quiet in-flow brand footer shows the wordmark, legal name, email and the
  document reference.

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

Not covered by that render (the partials are converted, but no invoice
exercised them): graduated, package, percentage and volume charge models,
taxes above zero, coupons, credit notes, pricing units and progressive billing.

## Assets and licences

- `fonts/inter-400-normal.woff2`: Inter, SIL Open Font License 1.1 (Google Fonts).
- `fonts/ibm-plex-mono-{400,600}-latin.woff2`: IBM Plex Mono, SIL Open Font
  License 1.1 (Google Fonts).
- `lerian-logo.png`: the Lerian wordmark, property of Lerian. Not covered by
  the repository licence.
