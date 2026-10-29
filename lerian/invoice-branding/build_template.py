#!/usr/bin/env python3
"""Build the Lerian-branded Lago invoice templates from upstream v4.slim.

Visual language: the Sindarian UI design system (console-sdk/packages/sindarian-ui, light theme): Inter only,
zinc neutrals, sentence-case labels, yellow #FEED02 as the single accent, hairline separators, Sindarian table
and status badge conventions. Structure: a left rail with the section title (Summary, Parties, Charges, Total,
Notes, Usage by day); unlike the Lerian reference invoice, the sections are not numbered.

Input: the pristine upstream templates, read with `git show <sha>:<path>` where <sha> is `upstream.sha` in
.lerian-fork.yml, so the patch is always rebuilt from upstream and never from an already branded copy.
Output, overwritten in place:
- app/views/templates/invoices/v4.slim and the standalone roots v4/{one_off,charge,fixed_charge,self_billed}.slim:
  a new stylesheet and body composed here, fed by the fragments of the upstream body (parties columns, totals,
  the fee partial dispatch, footer text), each asserted to exist upstream;
- the other v4/ partials: upstream with presentational edits only (bare amounts via MoneyHelper.cell, column
  heads, billing periods as group rows, section markers, the usage-by-day appendix in _subscription_details);
- app/views/templates/documents/footer.slim, the page footer Gotenberg repeats on every page, built from the
  upstream #6489 file (FOOTER_SHA, read from its cherry-pick).
Run from anywhere inside the repo: python3 lerian/invoice-branding/build_template.py
"""
import base64, pathlib, re, subprocess

HERE = pathlib.Path(__file__).resolve().parent
REPO = pathlib.Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=HERE, check=True,
                                   capture_output=True, text=True).stdout.strip())
TEMPLATES = "app/views/templates/invoices"

# upstream.sha from the fork manifest (stdlib only, so no YAML parser: match the `sha:` key under `upstream:`)
manifest = (REPO / ".lerian-fork.yml").read_text(encoding="utf-8")
m = re.search(r"^upstream:\n(?:[ \t]+.*\n)*?[ \t]+sha:[ \t]*([0-9a-f]{40})[ \t]*$", manifest, re.M)
assert m, "upstream.sha not found in .lerian-fork.yml"
UPSTREAM_SHA = m.group(1)


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, check=True, capture_output=True).stdout


def upstream(path):
    return git("show", f"{UPSTREAM_SHA}:{path}").decode("utf-8")


def replace_once(src, old, new, what):
    assert src.count(old) == 1, f"{what}: expected exactly one match upstream, found {src.count(old)}"
    return src.replace(old, new)


def indent(text, by):
    pad = " " * by
    return "".join(pad + ln if ln.strip() else ln for ln in text.splitlines(keepends=True))


def b64(path):
    return base64.b64encode((HERE / path).read_bytes()).decode()


logo = b64("lerian-logo.png")
INTER = {w: b64(f"fonts/inter-{w}-latin.woff2") for w in (400, 500, 600, 700)}

# Section markers. The data partials emit them as HTML comments (`/! lerian:<name>`) between the blocks the
# layout puts in different rail sections; the root templates render a partial once into a String and split it
# at the markers, so every block keeps its upstream place in the data flow and nothing is rendered twice.
SUB, TOTAL, APPENDIX, PRESENTATION, NOTICE, NOTICE_END = (
    f"<!--lerian:{n}-->" for n in ("sub", "total", "appendix", "presentation", "notice", "notice-end"))

# 1. Stylesheet shared by every root template. Sindarian UI light tokens (globals.css), copied as hex. Body
# sizes stay in the family prod renders (10px/16px CSS at Gotenberg scale 1.28): labels 9px, body 10px,
# titles 12-13px, the amount due 24px. Numbers use Inter with tabular figures (no mono family in the DS).
FONT_FACES = "".join(f"""      @font-face {{
        font-family: 'Inter';
        font-style: normal;
        font-weight: {w};
        font-display: swap;
        src: url(data:font/woff2;base64,{data}) format('woff2');
      }}
""" for w, data in INTER.items())

CSS = FONT_FACES + """
      :root {
        --fg: #3F3F46;
        --label: #52525B;
        --muted: #6E6E77;
        --border: #E4E4E7;
        --surface: #F4F4F5;
        --accent: #FEED02;
        --on-accent: #09090B;
        --rail: 98px;
      }
      * { box-sizing: border-box; }
      html { font-family: Inter, sans-serif; color: var(--fg); print-color-adjust: exact; -webkit-print-color-adjust: exact; }
      /* 12px sides: with the 0.42in Gotenberg margins the content edge lands at 42pt, as in the reference */
      body { margin: 0; padding: 0 12px; font-size: 10px; line-height: 16px; font-variant-numeric: tabular-nums; }
      h1, h2, p { margin: 0; padding: 0; }
      table { border-collapse: collapse; }
      tr { break-inside: avoid; }

      .body-1 { color: var(--fg); font-weight: 500; font-size: 10px; line-height: 16px; }
      .body-2 { color: var(--fg); font-weight: 400; font-size: 10px; line-height: 16px; }
      .body-3 { color: var(--muted); font-weight: 400; font-size: 9px; line-height: 14px; }
      h2, .title-2 { color: var(--fg); font-weight: 600; font-size: 12px; line-height: 18px; }
      .mb-4 { margin-bottom: 4px; }
      .mb-24 { margin-bottom: 12px; }
      .mt-24 { margin-top: 0; }
      .overflow-auto { overflow: visible; }
      .label { color: var(--label); font-weight: 500; font-size: 9px; line-height: 14px; }

      /* header: wordmark, document kind and number, status badge; hairline with the brand segment */
      .doc-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 0 0 8px; }
      .doc-head img { display: block; height: 20px; max-width: 180px; object-fit: contain; object-position: left center; }
      .doc-id { display: flex; align-items: center; gap: 8px; white-space: nowrap; }
      .doc-kind { color: var(--label); font-weight: 500; font-size: 10px; line-height: 16px; }
      .doc-number { color: var(--fg); font-weight: 600; font-size: 13px; line-height: 18px; }
      .badge { display: inline-flex; align-items: center; border: 1px solid transparent; border-radius: 9999px; padding: 1px 8px; font-weight: 500; font-size: 9px; line-height: 14px; white-space: nowrap; }
      .badge-alert { background: #FEFCE8; color: #854D0E; border-color: rgba(234, 179, 8, 0.5); }
      .badge-success { background: #F0FDF4; color: #166534; border-color: rgba(22, 163, 74, 0.5); }
      .badge-destructive { background: #DC2626; color: #FFFFFF; border-color: #DC2626; }
      .badge-inactive { background: #E4E4E7; color: #3F3F46; border-color: rgba(82, 82, 91, 0.4); }
      .head-rule { position: relative; height: 1px; background: var(--border); }
      .head-rule::before { content: ""; position: absolute; left: 0; top: -1px; width: 80px; height: 3px; background: var(--accent); }

      /* sections: rail (title only, no number) on the left, content column on the right, hairline between them */
      .sec { position: relative; padding: 9px 0 9px var(--rail); border-top: 1px solid var(--border); }
      .sec-first { border-top: 0; padding-top: 12px; }
      .rail { position: absolute; left: 0; top: 9px; width: calc(var(--rail) - 12px); }
      .sec-first .rail { top: 12px; }
      .rail-title { color: var(--label); font-weight: 500; font-size: 10px; line-height: 14px; }
      .sec-page { break-before: page; border-top: 0; padding-top: 0; }
      .sec-page .rail { top: 0; }

      /* Summary */
      .summary { display: flex; }
      /* the amount column grows past 40% instead of running under the due date; the other two give way */
      .sum-col { flex: 0 1 30%; min-width: 0; padding-right: 12px; }
      .sum-col.sum-amount { flex: 0 0 auto; min-width: 40%; }
      .sum-value { color: var(--fg); font-weight: 500; font-size: 12px; line-height: 30px; white-space: nowrap; }
      .sum-sub { color: var(--muted); font-size: 9px; line-height: 12px; }
      .sum-amount .money { white-space: nowrap; }
      .sum-amount .money .num { color: var(--fg); font-weight: 600; font-size: 24px; line-height: 30px; letter-spacing: -0.025em; }
      .sum-amount .money .cur { color: var(--muted); font-weight: 400; font-size: 12px; line-height: 30px; margin-left: 4px; }
      /* a million and up (9+ digits): 18px, so the amount and its code still fit the 40% column */
      .sum-amount.sum-long .money .num { font-size: 18px; }
      /* pending or failed payment: the whole row (rail included) on the status surface, the due date in the accent chip */
      .sec-summary.sec-alert { background: #FEFCE8; }
      .sec-summary.sec-destructive { background: #FEF2F2; }
      .sum-value .chip { line-height: 18px; margin-left: -6px; }

      /* Parties */
      .parties { display: flex; }
      .party { flex: 0 0 40%; min-width: 0; padding-right: 12px; word-wrap: break-word; }
      .party + .party { flex-basis: 60%; }
      .party .label { margin-bottom: 2px; }
      .party .party-name { color: var(--fg); font-weight: 500; font-size: 10px; line-height: 16px; }
      .party .body-2 { color: var(--muted); font-size: 9px; line-height: 13px; }
      /* purchase order and customer metadata under the customer name, set like the address lines: label as typed
         in Lago in 500, a space, the value; one flowing line per entry (an aligned table squeezed the values) */
      .info-row { color: var(--muted); font-size: 9px; line-height: 13px; overflow-wrap: anywhere; }
      .info-key { font-weight: 500; }
      /* the value moves to the next line whole; it breaks only when wider than the column */
      .info-key + span { display: inline-block; max-width: 100%; }

      /* Charges: Sindarian table. Head row with a bottom border only, no fill, 500, sentence case; body rows
         separated by hairlines, no zebra; numbers right-aligned and tabular. The currency code is printed once
         in the amount head; MoneyHelper.cell renders bare numbers. */
      .sec-charges h2.title-2 { margin-bottom: 4px; }
      .invoice-resume { overflow: visible; }
      .invoice-resume-table { width: 100%; }
      .invoice-resume-table td { padding: 5px 0 5px 10px; text-align: right; vertical-align: top; word-wrap: break-word; }
      .invoice-resume-table td:first-child { padding-left: 0; text-align: left; }
      .invoice-resume-table td:not(:first-child) { white-space: nowrap; }
      .invoice-resume-table td:nth-child(2):nth-last-child(4) { width: 52px; }
      .invoice-resume-table td:nth-child(3):nth-last-child(3) { width: 84px; }
      .invoice-resume-table td:nth-child(4):nth-last-child(2) { width: 52px; }
      .invoice-resume-table td:nth-child(5):last-child { width: 96px; }
      .invoice-resume-table td:nth-child(2):nth-last-child(3) { width: 52px; }
      .invoice-resume-table td:nth-child(3):nth-last-child(2) { width: 84px; }
      .invoice-resume-table td:nth-child(4):last-child { width: 96px; }
      .invoice-resume-table td:nth-child(2):last-child { width: 120px; }
      /* no tax applied on the invoice: every fee reads 0.0%, so the tax rate column is left out (the Total section keeps the tax row) */
      .no-tax .invoice-resume-table td:nth-child(4):nth-last-child(2) { display: none; }
      .invoice-resume-table tr.first_child td, .invoice-resume-table tr:first-child td { color: var(--label); font-weight: 500; font-size: 9px; line-height: 14px; padding-top: 0; padding-bottom: 6px; border-bottom: 1px solid var(--border); }
      .invoice-resume-table tr.period-row td { padding: 7px 0 0; text-align: left; white-space: normal; }
      .invoice-resume-table tr.period-row:first-child td { border-bottom: 0; color: inherit; font-weight: 400; }
      .period-kind { color: var(--label); font-weight: 500; font-size: 9px; line-height: 14px; margin-right: 6px; }
      .period-dates { color: var(--muted); font-size: 9px; line-height: 14px; }
      .invoice-resume-table tr.fee { border-top: 1px solid var(--border); }
      .invoice-resume-table tr.first_child + tr.fee, .invoice-resume-table tr.period-row + tr.fee,
      .invoice-resume-table tr:first-child + tr.fee { border-top: 0; }
      .invoice-resume-table tr.period-row { border-top: 1px solid var(--border); }
      .invoice-resume-table tr.first_child + tr.period-row, .invoice-resume-table tr.period-row:first-child { border-top: 0; }
      .invoice-resume-table tr.first_child + tr.period-row td { padding-top: 6px; }
      .invoice-resume-table tr.period-row:first-child td { padding-top: 12px; }
      .invoice-resume-table tr.fee td { padding-top: 6px; }
      .invoice-resume-table tr:has(+ tr.fee) td, .invoice-resume-table tr:has(+ tr.period-row) td, .invoice-resume-table tr:last-child td { padding-bottom: 6px; }
      .invoice-resume-table td.body-1, .invoice-resume-table td .body-1 { font-weight: 400; }
      .invoice-resume-table tr.charge-name td { padding-bottom: 0; }
      .invoice-resume-table tr.details td { color: var(--muted); font-size: 9px; line-height: 14px; padding-top: 2px; padding-bottom: 2px; }
      .invoice-resume-table tr.details td:first-child { padding-left: 10px; }
      .invoice-resume-table tr.details.subtotal td { color: var(--fg); }
      .money { white-space: nowrap; }
      .money .cur { margin-left: 4px; color: var(--muted); }

      /* Total: right-aligned block, hairlines between rows, the final total in the accent chip */
      .invoice-resume .total-table, .total-table { width: 290px; margin-left: auto; }
      .total-table td { padding: 4px 0; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }
      .total-table td:first-child:empty { display: none; }
      .total-table td:last-child { text-align: right; white-space: nowrap; padding-left: 12px; }
      .total-table td.body-2:not(:last-child) { color: var(--label); }
      .total-table tr:last-child td { border-bottom: 0; padding-top: 7px; color: var(--fg); font-weight: 600; font-size: 12px; line-height: 18px; }
      .total-table tr:last-child .money .cur { font-size: 10px; }
      .sec-total .total-table tr:last-child .money, .chip { display: inline-block; background: var(--accent); color: var(--on-accent); border-radius: 4px; padding: 1px 6px; }
      .sec-total .total-table tr:last-child .money .cur { color: var(--on-accent); }

      /* Notes */
      /* Total and Notes move to the next page whole: a break inside them left `Payment detail` alone at the
         bottom of a page, its content on the next (Charges, the long one, still breaks between rows) */
      .sec-total, .sec-notes { break-inside: avoid; }
      .notes > * + * { margin-top: 6px; }
      .notes p, .notes .body-3, .notes .notice { color: var(--muted); font-size: 10px; line-height: 16px; margin-bottom: 0; }
      .notes .label { margin-bottom: 2px; }
      .notes .payment-detail { color: var(--fg); }
      .notes .ref { color: var(--fg); font-weight: 500; }
      .invoice-custom-sections { margin-bottom: 0; }

      /* A Usage by day: the grouped recurring breakdown rows, in two columns */
      .sec-appendix { break-before: page; border-top: 0; padding-top: 0; }
      .sec-appendix .rail { top: 0; }
      .sec-appendix.sec-inline { break-before: auto; border-top: 1px solid var(--border); padding-top: 9px; }
      .sec-appendix.sec-inline .rail { top: 9px; }
      .appendix-block + .appendix-block { margin-top: 18px; }
      .appendix-title { color: var(--fg); font-weight: 500; font-size: 10px; line-height: 16px; }
      .appendix-intro { color: var(--muted); font-size: 10px; line-height: 16px; margin-bottom: 8px; }
      .appendix-cols { display: flex; gap: 20px; align-items: flex-start; }
      .appendix-table { flex: 1 1 0; min-width: 0; }
      .appendix-table td { padding: 5px 0 5px 8px; border-bottom: 1px solid var(--border); text-align: right; white-space: nowrap; }
      .appendix-table td:first-child { padding-left: 0; text-align: left; }
      .appendix-table td:nth-child(2) { color: var(--muted); }
      .appendix-table tr.first_child td { color: var(--label); font-weight: 500; font-size: 9px; line-height: 14px; padding-top: 0; }
      .appendix-table tr.total-row td { background: rgba(228, 228, 231, 0.5); border-bottom: 0; color: var(--fg); font-weight: 600; }
      .appendix-table tr.total-row td:first-child { padding-left: 6px; }
      .appendix-table tr.total-row td:last-child { padding-right: 6px; }
      .sec-appendix .notice { color: var(--muted); font-size: 10px; line-height: 16px; margin-top: 10px; }

      /* upstream blocks kept as they are, restyled: presentation breakdowns (own page), detail titles */
      .invoice-details-title { break-before: auto; }
      .breakdown-details { overflow: visible; }
      .breakdown-details-table { width: 100%; }
      .breakdown-details-table tr td { padding: 5px 0; border-bottom: 1px solid var(--border); }
      .breakdown-details-table tr td:last-child { text-align: right; white-space: nowrap; }
      .presentation-breakdowns-page { break-before: page; }
      .presentation-breakdowns .breakdown-details-table tr.first_child td { color: var(--label); font-weight: 500; font-size: 9px; line-height: 14px; }
      .presentation-breakdowns .breakdown-details-table tr.presentation-group td { color: var(--muted); border-bottom: 0; padding-top: 0; }
      .presentation-breakdowns .breakdown-details-table tr.presentation-group td:first-child { padding-left: 10px; }
      .presentation-breakdowns .breakdown-details-table tr.fee td { border-bottom: 0; }
      .presentation-breakdowns .breakdown-details-table tr.section-end td { border-bottom: 1px solid var(--border); padding-bottom: 6px; }
      .alert { color: var(--muted); font-size: 10px; line-height: 16px; }
"""

# 2. Root body. The upstream body is cut into the fragments it is made of; every fragment is asserted, and the
# data-bearing ones (parties columns, fee partial dispatch, notes partials) are carried over as they are.
ROOT_HEAD_END = "    css:\n"
WRAPPER = "    .wrapper\n"
HEADER = {
    "default": """      .mb-24
        h1.invoice-title = document_invoice_name
        - if billing_entity.logo.present?
          img.header-logo src="data:#{billing_entity.logo.content_type};base64,#{billing_entity.base64_logo}"

""",
    # self_billed has no billing entity logo upstream (the document is issued on behalf of the customer)
    "self_billed": """      .mb-24
        h1.invoice-title = document_invoice_name

""",
}
INFO_FRAGMENTS = [
    "            - if purchase_order_number.present?\n",
    "              td.body-2 = purchase_order_number\n",
    "              td.body-2 = I18n.t('invoice.payment_term_days', net_payment_term:)\n",
    "              - customer.metadata.displayable.order(created_at: :asc).each do |metadata|\n",
]
INFO_START = "      .mb-24.overflow-auto\n        .invoice-information-column\n"
PARTIES_START = "      .mb-24.overflow-auto\n        .billing-information-column\n"
AMOUNT_START = "      .mb-24\n        h2.title-2"


def cut(src, start, end, what):
    """Cut the block from `start` (included) up to `end` (excluded); both must occur exactly once."""
    assert src.count(start) == 1 and src.count(end) == 1, f"{what}: block boundaries moved"
    i, j = src.index(start), src.index(end)
    assert i < j, f"{what}: block boundaries out of order"
    return src[:i] + src[j:], src[i:j]


amount_re = re.compile(r"^      \.mb-24\n        h2\.title-2\.mb-4 = (.+)\n        \.body-1 = (.+)\n\n", re.M)
dispatch_re = re.compile(r"^      \.invoice-resume\.mb-24\.overflow-auto\n((?: {8}[^\n]*\n)+)\n", re.M)
footer_text_re = re.compile(r"^      p\.body-3\.mb-24 = LineBreakHelper\.break_lines\((.+)\)\n", re.M)
DUE = "I18n.t('invoice.due_date', date: I18n.l(payment_due_date, format: :default))"
DUE_EXPRS = {DUE: "false", f"advance_charges? ? I18n.t('invoice.already_paid') : {DUE}": "advance_charges?"}
TOTAL_EXPRS = {"MoneyHelper.format(total_amount)",
               "total_amount.format(format: I18n.t('money.format'), decimal_mark: I18n.t('money.decimal_mark'), thousands_separator: I18n.t('money.thousands_separator'))"}
# blocks between the fee dispatch and the footer text, moved into the Notes section (or after it)
EU_TAX = "      == SlimHelper.render('templates/invoices/v4/_eu_tax_management', self)\n"
THRESHOLD = """      - applied_usage_threshold = progressive_billing_last_applied_usage_threshold
      - if applied_usage_threshold
        p.body-3.mb-24
          = I18n.t('invoice.reached_usage_threshold', usage_amount: MoneyHelper.format(applied_usage_threshold.lifetime_usage_amount), threshold_amount: MoneyHelper.format(applied_usage_threshold.passed_threshold_amount))
"""
CUSTOM = """      - if applied_invoice_custom_sections.present?
        == SlimHelper.render('templates/invoices/v4/_custom_sections', self)
"""
PRESENTATION_ROOT = "      == SlimHelper.render('templates/invoices/v4/_presentation_breakdowns', self, fees: fees.includes(:presentation_breakdowns, :charge, :charge_filter))\n"
POWERED = "      == SlimHelper.render('templates/invoices/v4/_powered_by_logo', self)\n"
MULTI = """      - if subscriptions.length > 1
        == SlimHelper.render('templates/invoices/v4/_subscription_details', self, disable_presentation_breakdowns: false)
"""

LOGO_IMG = {
    "default": """          - if billing_entity.logo.present?
            img src="data:#{billing_entity.logo.content_type};base64,#{billing_entity.base64_logo}"
          - else
            img src="data:image/png;base64,LOGO_B64" alt="Lerian"
""",
    "self_billed": """          img src="data:image/png;base64,LOGO_B64" alt="Lerian"
""",
}


def rail(key):
    return f"""        .rail
          .rail-title = I18n.t('lerian.invoice.sections.{key}')
"""


CUSTOMER_NAME = "            .party-name = customer.display_name\n"
CUSTOMER_INFO = """            - lerian_metadata = customer.metadata.displayable.order(created_at: :asc).to_a
            - lerian_info_digits = lerian_metadata.map { |m| m.value.to_s.gsub(/\\D/, '') }.reject(&:empty?)
            - if purchase_order_number.present? || lerian_metadata.any?
              .info-rows
                - if purchase_order_number.present?
                  .info-row
                    span.info-key => I18n.t('lerian.invoice.summary.purchase_order')
                    span = purchase_order_number
                - lerian_metadata.each do |metadata|
                  .info-row
                    span.info-key => metadata.key
                    span = metadata.value
"""


def party_column(block):
    """One upstream .billing-information-column: label to .label, the first value line to .party-name."""
    lines = [ln for ln in block.splitlines(keepends=True) if not ln.strip().startswith("/")]
    body = "".join(lines)
    body = replace_once(body, "          .body-1 = I18n.t(", "          .label = I18n.t(", "parties: column label")
    first = re.search(r"^          \.body-2\b", body, re.M)
    assert first, "parties: column without a value line"
    body = body[:first.start()] + "          .party-name" + body[first.start() + len("          .body-2"):]
    return "          .party\n" + indent(body, 2)


def compose(src, name):
    """Replace the stylesheet and the body of a root invoice template with the Lerian composition."""
    kind = "self_billed" if name == "self_billed" else "default"
    head_at = src.index(ROOT_HEAD_END)
    wrap_at = src.index(WRAPPER)
    assert src.count(WRAPPER) == 1 and head_at < wrap_at, f"{name}: css/wrapper layout moved"
    body = src[wrap_at + len(WRAPPER):]

    body = replace_once(body, HEADER[kind], "", f"{name}: header")

    # self_billed has a comment line between the parties wrapper and its first column
    body = body.replace("      .mb-24.overflow-auto\n        // Issuer (partner) information\n", PARTIES_START.split("\n")[0] + "\n", 1)
    body, info = cut(body, INFO_START, PARTIES_START, f"{name}: invoice information")
    for frag in INFO_FRAGMENTS:
        assert info.count(frag) == 1, f"{name}: invoice information fragment moved: {frag.strip()}"

    body, parties = cut(body, PARTIES_START, AMOUNT_START, f"{name}: billing information")
    columns = parties[len("      .mb-24.overflow-auto\n"):].split("        .billing-information-column\n")[1:]
    assert len(columns) == 2, f"{name}: expected two billing information columns"
    bill_to = [c for c in columns if "I18n.t('invoice.bill_to')" in c]
    assert len(bill_to) == 1, f"{name}: expected one bill_to column"
    ordered = bill_to + [c for c in columns if c is not bill_to[0]]
    parties_slim = "".join(party_column(c.rstrip("\n") + "\n") for c in ordered)
    # the purchase order number and the customer's displayable metadata sit right under the customer name, before
    # the address, as the reference puts its CNPJ (in Bill to; in self_billed the customer is the partner, From)
    parties_slim = replace_once(parties_slim, CUSTOMER_NAME, CUSTOMER_NAME + CUSTOMER_INFO, f"{name}: customer name")
    # an identifier already printed as a labelled metadata line (same digits) is not printed again bare
    for attr in ("legal_number", "tax_identification_number"):
        line = f"            - if customer.{attr}.present?\n"
        parties_slim = replace_once(parties_slim, line,
            f"            - if customer.{attr}.present? && !lerian_info_digits.include?(customer.{attr}.gsub(/\\D/, ''))\n",
            f"{name}: customer {attr}")

    amounts = amount_re.findall(body)
    assert len(amounts) == 1, f"{name}: expected one amount block upstream, found {len(amounts)}"
    total_expr, due_expr = amounts[0]
    assert total_expr in TOTAL_EXPRS, f"{name}: amount due expression moved: {total_expr}"
    assert due_expr in DUE_EXPRS, f"{name}: due date expression moved: {due_expr}"
    already_paid = DUE_EXPRS[due_expr]
    body = amount_re.sub("", body)

    dispatch = dispatch_re.findall(body)
    assert len(dispatch) == 1, f"{name}: expected one fee dispatch block"
    renders = dispatch[0].count("== SlimHelper.render(")
    assert renders >= 1, f"{name}: fee dispatch renders nothing"
    # capture the partials into one String: `== render` becomes an append, the if/elsif structure stays
    capture = re.sub(r"^(\s*)== SlimHelper\.render\(", r"\1- lerian_html << SlimHelper.render(", dispatch[0], flags=re.M)
    capture = re.sub(r"^  ", "", capture, flags=re.M)  # from the .invoice-resume child level to the .wrapper child level
    body = dispatch_re.sub("", body)

    footer_text = footer_text_re.findall(body)
    assert len(footer_text) == 1, f"{name}: expected one footer text paragraph"
    footer_expr = footer_text[0]
    assert footer_expr in ("billing_entity.invoice_footer", 'I18n.t("invoice.self_billed.footer")'), f"{name}: footer text moved"
    body = footer_text_re.sub("", body)

    notes_extra = ""
    for frag, what in ((EU_TAX, "eu tax"), (THRESHOLD, "usage threshold"), (CUSTOM, "custom sections")):
        if frag in body:
            body = replace_once(body, frag, "", f"{name}: {what}")
            notes_extra += indent(frag, 4)
    assert "_eu_tax_management" in notes_extra and "_custom_sections" in notes_extra, f"{name}: notes partials moved"
    after_notes = ""
    if PRESENTATION_ROOT in body:
        body = replace_once(body, PRESENTATION_ROOT, "", f"{name}: presentation breakdowns")
        after_notes = PRESENTATION_ROOT
    multi = MULTI in body
    if multi:
        body = replace_once(body, MULTI, "", f"{name}: multi-subscription details")
    if POWERED in body:
        body = replace_once(body, POWERED, "", f"{name}: powered by")
    assert not body.strip(), f"{name}: unexpected upstream body left over:\n{body}"

    payment_label = "" if kind == "self_billed" else "              .label = I18n.t('lerian.invoice.notes.payment_detail')\n"
    out = src[:head_at] + "    css:\n" + CSS + WRAPPER
    out += f"""      - lerian_status = status.to_s == 'voided' ? 'voided' : payment_status.to_s
      - lerian_badge = {{ 'voided' => 'inactive', 'succeeded' => 'success', 'failed' => 'destructive' }}.fetch(lerian_status, 'alert')
      - lerian_already_paid = {already_paid}
      - lerian_band = lerian_badge if !lerian_already_paid && %w[alert destructive].include?(lerian_badge)
      .doc-head
        .brand-mark
{LOGO_IMG[kind]}        .doc-id
          span.doc-kind = document_invoice_name
          span.doc-number = number
          span.badge class="badge-#{{lerian_badge}}" = I18n.t("lerian.invoice.status.#{{lerian_status}}", default: lerian_status.humanize)
      .head-rule

      / Summary
      .sec.sec-first.sec-summary class=("sec-#{{lerian_band}}" if lerian_band)
{rail("summary")}        .summary
          .sum-col.sum-amount class=('sum-long' if MoneyHelper.format(total_amount).to_s.count('0-9') > 8)
            .label = I18n.t(lerian_already_paid || %w[voided succeeded].include?(lerian_status) ? 'invoice.total' : 'lerian.invoice.summary.amount_due')
            == MoneyHelper.cell(total_amount, code: true)
          .sum-col
            .label = I18n.t('lerian.invoice.summary.due_date')
            - if lerian_already_paid
              .sum-value = I18n.t('invoice.already_paid')
            - else
              .sum-value
                span class=('chip' if lerian_band) = I18n.l(payment_due_date, format: :default)
              .sum-sub = I18n.t('lerian.invoice.summary.net_terms', days: I18n.t('invoice.payment_term_days', net_payment_term:))
          .sum-col
            .label = I18n.t('lerian.invoice.summary.issued')
            .sum-value = I18n.l(issuing_date, format: :default)

      / Parties
      .sec
{rail("parties")}        .parties
{parties_slim}
      / Charges and Total: the fee partials render once into a String, split at their section markers
      - lerian_html = +''
{capture}      - lerian_html = lerian_html.gsub('{SUB}', '')
      - lerian_charges, _, lerian_rest = lerian_html.partition('{TOTAL}')
      - lerian_total, _, lerian_rest = lerian_rest.partition('{APPENDIX}')
      - lerian_appendix, _, lerian_presentation = lerian_rest.partition('{PRESENTATION}')
      - lerian_notices = lerian_appendix.scan(/{NOTICE}(.*?){NOTICE_END}/m).flatten.map(&:strip).uniq
      - lerian_appendix = lerian_appendix.gsub(/{NOTICE}.*?{NOTICE_END}/m, '')
      - lerian_no_tax = applied_taxes.blank?
      .sec.sec-charges class=('no-tax' if lerian_no_tax)
{rail("charges")}        == lerian_charges
      .sec.sec-total
{rail("total")}        == lerian_total

      / Notes
      - lerian_footer_text = {footer_expr}
      .sec.sec-notes
{rail("notes")}        .notes
          - lerian_notices.each do |notice|
            == notice
{notes_extra}          - if lerian_footer_text.present?
            div
{payment_label}              p.payment-detail = LineBreakHelper.break_lines(lerian_footer_text)
          p == I18n.t('lerian.invoice.notes.payment_reference', number: "<span class=\\"ref\\">#{{ERB::Util.html_escape(number)}}</span>")

      / Usage by day (own page), then the upstream presentation breakdowns (own page)
      - if lerian_appendix.include?('appendix-table')
        .sec.sec-appendix
{indent(rail("appendix"), 2)}          == lerian_appendix
      == lerian_presentation
{after_notes}"""
    if multi:
        out += f"""
      / multi-subscription invoices: one page per subscription, with its charges, total and appendix
      - if subscriptions.length > 1
        - SlimHelper.render('templates/invoices/v4/_subscription_details', self, disable_presentation_breakdowns: false).split('{SUB}').drop(1).each do |chunk|
          - sub_charges, _, sub_rest = chunk.partition('{TOTAL}')
          - sub_total, _, sub_rest = sub_rest.partition('{APPENDIX}')
          - sub_appendix, _, sub_presentation = sub_rest.partition('{PRESENTATION}')
          .sec.sec-page.sec-charges class=('no-tax' if lerian_no_tax)
{indent(rail("details"), 4)}            == sub_charges
          .sec
{indent(rail("subscription_total"), 4)}            == sub_total
          - if sub_appendix.include?('appendix-table')
            .sec.sec-appendix.sec-inline
{indent(rail("appendix"), 6)}              == sub_appendix
          == sub_presentation
"""
    return out.replace("LOGO_B64", logo)


# 3. Partials: presentational edits only.
# 3a. td cells whose whole content is an amount become MoneyHelper.cell (bare number, see money_helper.rb)
cell_re = re.compile(r"^(\s*)(td\.body-\d\s+)?=\s*(?:'-'\s*\+\s*)?((?:MoneyHelper\.format|FeeDisplayHelper\.format_(?:amount|precise_unit_amount|as_currency|with_precision))\(.*\))\s*$")
# the final total row passes the Money itself, so the cell keeps its ISO code (the accent chip in the Total section)
TOTAL_CELL = {"== MoneyHelper.cell((MoneyHelper.format(total_amount)))": "== MoneyHelper.cell(total_amount, code: true)",
              "== MoneyHelper.cell((MoneyHelper.format(invoice_subscription.total_amount)))": "== MoneyHelper.cell(invoice_subscription.total_amount, code: true)"}


def convert_cells(text):
    out, changed = [], 0
    for ln in text.split("\n"):
        m = cell_re.match(ln)
        if m:
            ind, tag, expr = m.group(1), m.group(2) or "", m.group(3)
            sign = ", '-'" if "'-'" in ln else ""
            ln = f"{ind}{tag}== MoneyHelper.cell(({expr}){sign})"
            changed += 1
        out.append(ln)
    text = "\n".join(out)
    for old, new in TOTAL_CELL.items():
        text = text.replace(old, new)
    return text, changed


# 3b. column heads: Description | Qty | Unit price | (Tax rate) | Amount (<currency>), currency printed once
HEADS = [("I18n.t('invoice.item')", "I18n.t('lerian.invoice.charges.description')"),
         ("I18n.t('invoice.units')", "I18n.t('lerian.invoice.charges.qty')"),
         ("I18n.t('invoice.amount')", "I18n.t('lerian.invoice.charges.amount', currency:)")]
HEAD_ROW = re.compile(r"^( *)tr\n(\1  td\.body-2 = I18n\.t\('invoice\.item'\)\n)", re.M)


def column_heads(text, name):
    text = HEAD_ROW.sub(r"\1tr.first_child\n\2", text)
    for old, new in HEADS:
        text = text.replace(old, new)
    return text


# 3c. billing period heads become group rows: the column heads once, then `<kind> · <from> – <to>` per period
def period_head(ind, period_expr, kind_expr, first_expr, setup=""):
    i = " " * ind
    return indent(setup, ind) + f"""{i}/ Lerian: column heads once, then the billing period as a group row
{i}- if {first_expr}
{i}  tr.first_child
{i}    td.body-2 = I18n.t('lerian.invoice.charges.description')
{i}    td.body-2 = I18n.t('lerian.invoice.charges.qty')
{i}    td.body-2 = I18n.t('invoice.unit_price')
{i}    td.body-2 = I18n.t('invoice.tax_rate')
{i}    td.body-2 = I18n.t('lerian.invoice.charges.amount', currency:)
{i}tr.period-row
{i}  td colspan="5"
{i}    span.period-kind = {kind_expr}
{i}    span.period-dates = {period_expr}
"""


PERIOD_DATES = ("[billing_period.from_datetime, billing_period.to_datetime].compact"
                ".map { |t| I18n.l(t.in_time_zone(customer.applicable_timezone).to_date, format: :default) }.join(' – ')")
# the kind of a period group: subscription (plan or fixed charges), usage (charges, commitment) or both
SUB_KIND_SETUP = """- lerian_recurring = (fee_group.subscription_fee && FeeDisplayHelper.should_display_subscription_fee?(invoice_subscription)) || fee_group.fixed_charge_fees.any?
- lerian_usage = fee_group.charge_fees.any? || fee_group.commitment_fee.present?
"""
SUB_KIND = "I18n.t('lerian.invoice.charges.' + (lerian_recurring && lerian_usage ? 'subscription_and_usage' : (lerian_recurring ? 'subscription' : 'usage')))"


def upstream_period_head(ind, first_cell):
    i = " " * ind
    return (f"{i}tr.first_child\n{i}  td.body-2 = {first_cell}\n{i}  td.body-2 = I18n.t('invoice.units')\n"
            f"{i}  td.body-2 = I18n.t('invoice.unit_price')\n{i}  td.body-2 = I18n.t('invoice.tax_rate')\n"
            f"{i}  td.body-2 = I18n.t('invoice.amount')\n")


# 3d. "Daily detail in Usage by day" under a usage fee whose recurring breakdown goes to the appendix (the
# conditions of Invoice#recurring_fees, on a subscription invoice that renders _subscription_details)
def daily_hint(ind, fee):
    i = " " * ind
    return (f"{i}- if {fee}.charge? && !{fee}.invoice.progressive_billing? && !{fee}.charge.pay_in_advance? && {fee}.billable_metric&.recurring? "
            f"&& %w[sum_agg unique_count_agg].include?({fee}.billable_metric.aggregation_type.to_s) && {fee}.units.positive?\n"
            f"{i}  .body-3 = I18n.t('lerian.invoice.charges.daily_detail')\n")


HINTS = {
    "_default_fee": ("    - if fee.charge&.prorated? || fee.fixed_charge&.prorated?\n      .body-3 = I18n.t('invoice.fee_prorated')\n", 4, "fee"),
    "_fees_without_filters": ("      - if fee.charge.prorated?\n        .body-3 = I18n.t('invoice.fee_prorated')\n", 6, "fee"),
    "_fee_with_filters": ("    - if self.charge.prorated?\n      .body-3 = I18n.t('invoice.fee_prorated')\n", 4, "self"),
    "_default_fee_with_filters": ("    - if self.charge.prorated?\n      .body-3 = I18n.t('invoice.fee_prorated')\n", 4, "self"),
}

# 3e. section markers before the total block of every partial that has one
TOTAL_MARKS = {
    "_subscription_details": "    / Total section\n    .invoice-resume.overflow-auto\n      table.total-table width=\"100%\"\n",
    "_progressive_billing_details": "/ Total section\n.invoice-resume.overflow-auto\n  table.total-table width=\"100%\"\n",
    "_subscriptions_summary": "\ntable.total-table width=\"100%\"\n",
    "_one_off": "\ntable.total-table width=\"100%\"\n",
    "_charge": "\ntable.total-table width=\"100%\"\n",
    "_fixed_charge": "\ntable.total-table width=\"100%\"\n",
    "_credit": "\ntable.total-table width=\"100%\"\n",
}


def mark_total(text, name):
    old = TOTAL_MARKS[name]
    ind = len(old.lstrip("\n")) - len(old.lstrip("\n").lstrip(" "))
    lead = "\n" if old.startswith("\n") else ""
    return replace_once(text, old, f"{lead}{' ' * ind}/! lerian:total\n{old.lstrip(chr(10))}", f"{name}: total block")


# 3f. _subscription_details: the recurring fees breakdown becomes the usage-by-day appendix. Upstream prints one
# row per breakdown item, i.e. one `+1` row per distinct value of a unique count metric (a production invoice had
# 2,987 items). The appendix prints one row per [date, action, duration, total_duration] group with the amounts
# summed, in the order the breakdown service sorted them, never merging rows across fees, split in two columns,
# with the fee units as the total. The column of counts is titled with the fee's item name (free text from the
# plan). Presentation only: the breakdown, the fees and their totals are unchanged. The not-prorated/prorated
# notice is emitted between notice markers; the root moves it to the Notes section.
UPSTREAM_BREAKDOWN_START = "    / Recurring fees breakdown\n"
UPSTREAM_BREAKDOWN_END = "    - unless disable_presentation_breakdowns\n"
UPSTREAM_BREAKDOWN_FRAGMENTS = [
    "    - if grouped_fees.any? { |fg| fg.charge_fees.any? }\n",
    "        - recurring_fees(subscription.id).group_by(&:charge_id).each do |_charge_id, fees|\n",
    "          - next unless fees.sum(&:units) > 0\n",
    "          - number_of_days_in_period = 30\n",
    "          - if fees.all? { |f| f.charge_filter_id? }\n",
    "            - fees.select { |f| f.units.positive? }.each do |fee|\n",
    "              .body-1.mb-24 = I18n.t('invoice.breakdown_of', fee_filter_display_name: fee.filter_display_name(separator: ' • '))\n",
    "                  - recurring_breakdown(fee).each do |breakdown|\n",
    "                    - number_of_days_in_period = breakdown.total_duration\n",
    "                        .body-3 = I18n.t('invoice.breakdown_for_days', breakdown_duration: breakdown.duration, breakdown_total_duration: breakdown.total_duration)\n",
    "                        - if breakdown.action.to_sym == :add\n",
    "                          | #{breakdown.amount.negative? ? '' : '-'}#{breakdown.amount} #{fee.item_name}\n",
    "                          | +/-#{breakdown.amount} #{fee.item_name}\n",
    "          - if fees.first.charge.prorated?\n",
    "            .alert.body-3 = I18n.t('invoice.notice_prorated', days_in_month: number_of_days_in_period)\n",
    "            .alert.body-3 = I18n.t('invoice.notice_full')\n",
]
APPENDIX_SLIM = f"""    / Lerian: the recurring fees breakdown, as the usage-by-day appendix (rows grouped by date, action and
    / duration with the amounts summed, never one row per item; split in two columns; presentation only)
    /! lerian:appendix
    - if grouped_fees.any? {{ |fg| fg.charge_fees.any? }}
      - recurring_fees(subscription.id).group_by(&:charge_id).each do |_charge_id, fees|
        - next unless fees.sum(&:units) > 0

        - number_of_days_in_period = 30
        - lerian_tables = fees.all? {{ |f| f.charge_filter_id? }} ? fees.select {{ |f| f.units.positive? }}.map {{ |f| ["#{{fees.first.invoice_name}} • #{{f.filter_display_name(separator: ' • ')}}", [f]] }} : [[fees.first.invoice_name, fees]]
        - billing_period = FeeBoundariesHelper.billing_period_for(fees.first, invoice_subscription:)
        - lerian_period = {PERIOD_DATES}
        - lerian_tables.each do |title, table_fees|
          - rows = []
          - table_fees.each do |fee|
            - breakdowns = recurring_breakdown(fee)
            - number_of_days_in_period = breakdowns.last.total_duration if breakdowns.any?
            - breakdowns.group_by {{ |b| [b.date, b.action, b.duration, b.total_duration] }}.each_value do |items|
              - rows << [items.first, items.sum(&:amount)]
          - next if rows.empty?
          - half = (rows.size + 1) / 2
          - columns = [rows.first(half), rows.drop(half)].reject(&:empty?)
          .appendix-block
            .appendix-title = title
            p.appendix-intro = I18n.t('lerian.invoice.appendix.intro', item: fees.first.item_name, period: lerian_period) + ' ' + I18n.t(fees.first.charge.prorated? ? 'lerian.invoice.appendix.prorated' : 'lerian.invoice.appendix.not_prorated')
            .appendix-cols
              - columns.each_with_index do |column, column_index|
                table.appendix-table
                  tr.first_child
                    td = I18n.t('lerian.invoice.appendix.date')
                    td = I18n.t('lerian.invoice.appendix.days_active')
                    td = fees.first.item_name
                  - column.each do |breakdown, group_amount|
                    tr
                      td = I18n.l(breakdown.date, format: :default)
                      td = "#{{breakdown.duration}} / #{{breakdown.total_duration}}"
                      td
                        - if breakdown.action.to_sym == :add
                          | #{{group_amount}}
                        - elsif breakdown.action.to_sym == :remove
                          | #{{group_amount.negative? ? '' : '-'}}#{{group_amount}}
                        - else
                          | +/-#{{group_amount}}
                  - if column_index == columns.size - 1
                    tr.total-row
                      td = I18n.t('lerian.invoice.appendix.total')
                      td
                      td = RoundingHelper.round_decimal_part(table_fees.sum(&:units))

        /! lerian:notice
        - if fees.first.charge.prorated?
          p.notice = I18n.t('invoice.notice_prorated', days_in_month: number_of_days_in_period)
        - else
          p.notice = I18n.t('invoice.notice_full')
        /! lerian:notice-end

    /! lerian:presentation
"""


def subscription_details(text):
    text = replace_once(text, "    == SlimHelper.render('templates/invoices/v4/_subscription_name', self, subscription: subscription, page_break: subscriptions.length > 1)\n",
                        "    /! lerian:sub\n    == SlimHelper.render('templates/invoices/v4/_subscription_name', self, subscription: subscription, page_break: subscriptions.length > 1)\n",
                        "_subscription_details: subscription loop")
    text = replace_once(text, "          / Period header row\n" + upstream_period_head(10, "FeeBoundariesHelper.format_billing_period(billing_period, customer:)"),
                        period_head(10, PERIOD_DATES, SUB_KIND, "group_index == 0", SUB_KIND_SETUP), "_subscription_details: period head")
    start, end = text.index(UPSTREAM_BREAKDOWN_START), text.index(UPSTREAM_BREAKDOWN_END)
    assert text.count(UPSTREAM_BREAKDOWN_START) == 1 and start < end, "_subscription_details: breakdown block moved"
    block = text[start:end]
    for frag in UPSTREAM_BREAKDOWN_FRAGMENTS:
        assert block.count(frag) >= 1, f"_subscription_details: breakdown fragment moved: {frag.strip()}"
    return text[:start] + APPENDIX_SLIM + text[end:]


def fixed_charge(text):
    return replace_once(text, upstream_period_head(6, "FeeBoundariesHelper.format_billing_period(billing_period, customer:)"),
                        period_head(6, PERIOD_DATES, "I18n.t('lerian.invoice.charges.subscription')", "group_index == 0"),
                        "_fixed_charge: period head")


def progressive(text):
    first = ("I18n.t('invoice.fees_from_to_date', from_date: I18n.l(invoice_subscription.charges_from_datetime_in_customer_timezone&.to_date, format: :default), "
             "to_date: I18n.l(issuing_date, format: :default))")
    dates = ("[I18n.l(invoice_subscription.charges_from_datetime_in_customer_timezone&.to_date, format: :default), "
             "I18n.l(issuing_date, format: :default)].join(' – ')")
    return replace_once(text, upstream_period_head(4, first), period_head(4, dates, "I18n.t('lerian.invoice.charges.usage')", "true"),
                        "_progressive_billing_details: period head")


CUSTOM_SECTIONS_CSS = """css:
  .invoice-custom-section {
    margin-top: 24px;
    border-bottom: 1px solid #D9DEE7;
  }

  .invoice-custom-section p.section-name {
      margin-bottom: 8px;
  }
"""
CUSTOM_SECTIONS_NEW_CSS = """css:
  .invoice-custom-section + .invoice-custom-section {
    margin-top: 6px;
  }

  .invoice-custom-section p.section-name {
      margin-bottom: 2px;
  }
"""

# Root templates Lago picks per invoice (Invoices::GeneratePdfService#template): v4.slim for subscription and
# progressive billing invoices, the standalone ones for one-off, advance charge, fixed charge and self-billed
# invoices. All of them get the composition.
STANDALONE = {"one_off", "charge", "fixed_charge", "self_billed"}
# the no-tax row of the totals names the tax 'Tax' in every locale upstream ("Tax (0%)" on a pt-BR invoice); the
# upstream invoice.tax key carries the translation ("Imposto")
NO_TAX_NAME = ("name: 'Tax', rate: 0", "name: I18n.t('invoice.tax'), rate: 0")
src = compose(upstream(f"{TEMPLATES}/v4.slim"), "v4")

pdir = REPO / TEMPLATES / "v4"
pdir.mkdir(parents=True, exist_ok=True)
names = sorted(p for p in git("ls-tree", "--name-only", UPSTREAM_SHA, f"{TEMPLATES}/v4/").decode("utf-8").splitlines()
               if p.endswith(".slim"))
changed = 0
no_tax = 0
for name in names:
    stem = pathlib.PurePosixPath(name).stem
    text, n = convert_cells(upstream(name))
    changed += n
    if NO_TAX_NAME[0] in text:
        text = replace_once(text, *NO_TAX_NAME, f"{stem}: no-tax row name")
        no_tax += 1
    if stem in STANDALONE:
        text = compose(text, stem)
    else:
        if stem == "_subscription_details":
            text = subscription_details(text)
        if stem == "_fixed_charge":
            text = fixed_charge(text)
        if stem == "_progressive_billing_details":
            text = progressive(text)
        if stem in TOTAL_MARKS:
            text = mark_total(text, stem)
        text = column_heads(text, stem)
        if stem in HINTS:
            old, ind, fee = HINTS[stem]
            text = replace_once(text, old, old + daily_hint(ind, fee), f"{stem}: prorated line")
        if stem == "_custom_sections":
            text = replace_once(text, CUSTOM_SECTIONS_CSS, CUSTOM_SECTIONS_NEW_CSS, "_custom_sections: css")
    (pdir / pathlib.PurePosixPath(name).name).write_text(text, encoding="utf-8")
assert no_tax == 6, f"no-tax row name: expected in 6 partials, found in {no_tax}"
print(f"partials: {changed} amount cells converted in {len(names)} files under {pdir.relative_to(REPO)}")

out = REPO / TEMPLATES / "v4.slim"
out.write_text(src, encoding="utf-8")
print(f"wrote {out.relative_to(REPO)} ({len(src)} bytes) from upstream {UPSTREAM_SHA}")

# 4. Page footer: documents/footer.slim is the Gotenberg `footer.html` part (Utils::PdfGenerator), rendered by
# Chromium as page chrome at the bottom of every page, for invoices, credit notes and payment receipts. It comes
# from upstream #6489, cherry-picked onto the fork, so it is read from that commit (footer_source), not from upstream.sha.
# Chromium renders it in an isolated document: every style lives in its own <style> with an explicit size and
# colour on each text node (an unstyled footer renders at zero size), and fonts and the wordmark are base64
# (no network). Chromium injects its own stylesheet into the footer, with rules for .left, .center, .right,
# .date, .title, .url, .pageNumber and .totalPages: never use those class names for our own layout (only the
# page counter spans keep .pageNumber/.totalPages, which Chromium fills). Every @font-face has
# font-display: swap, otherwise text whose font is not loaded yet stays invisible in the footer. Inter
# prefers local() (the Gotenberg image ships the family) with the data: url as fallback.
# Gotenberg 8 (the version production runs) does not apply `scale: 1.28` to the footer, so every value is the body
# design value multiplied by 1.28. The footer has a fixed height (the legal name and the email stacked next to the
# wordmark, nowrap, ellipsized), so the bottom margin in Utils::PdfGenerator always fits it. Credit notes and payment receipts have the
# same methods it reads (number, billing_entity).
# FOOTER_SHA is the upstream commit, the identity of the patch. The upstream object is not reachable from any fork
# ref, so the file is read from the fork's cherry-pick of it (found by its `git cherry-pick -x` line; its sha
# changes on rebase), then from FOOTER_SHA itself (present once upstream.sha contains #6489).
FOOTER_SHA = "0447828b740d70a4417f9e15fae04e42f07f6f3e"
FOOTER = "app/views/templates/documents/footer.slim"


def footer_source():
    picks = git("log", "--all", "--format=%H", f"--grep=cherry picked from commit {FOOTER_SHA}").decode("utf-8").split()
    for rev in picks[:1] + [FOOTER_SHA]:
        shown = subprocess.run(["git", "show", f"{rev}:{FOOTER}"], cwd=REPO, capture_output=True)
        if shown.returncode == 0:
            return rev, shown.stdout.decode("utf-8")
    raise SystemExit(f"{FOOTER}: neither a cherry-pick of {FOOTER_SHA} nor the upstream commit is in this clone. "
                     f"Run: git fetch https://github.com/getlago/lago-api.git {FOOTER_SHA}")


footer_rev, footer = footer_source()

old_footer_style_start = """    style
      | @font-face {"""
old_footer_body = """  body
    .footer
      span = number
      span
        == page_numbering
"""
assert footer.count(old_footer_style_start) == 1 and footer.endswith(old_footer_body), \
    f"{FOOTER}: upstream style or body block moved"
new_footer_vars = """- entity = billing_entity if respond_to?(:billing_entity)
"""
new_footer_style = f"""    style
      | @font-face {{
          font-family: 'Inter';
          font-style: normal;
          font-weight: 400;
          font-display: swap;
          src: local("Inter"), local("Inter-Regular"), url(data:font/woff2;base64,{INTER[400]}) format('woff2');
        }}
        @font-face {{
          font-family: 'Inter';
          font-style: normal;
          font-weight: 500;
          font-display: swap;
          src: local("Inter Medium"), local("Inter-Medium"), url(data:font/woff2;base64,{INTER[500]}) format('woff2');
        }}

        body {{
          box-sizing: border-box;
          margin: 0;
          padding: 0 calc(0.42in + 15.36px);
          color: #6E6E77;
          print-color-adjust: exact;
          -webkit-print-color-adjust: exact;
          font-family: Inter, sans-serif;
          font-size: 11.52px;
          line-height: 15.36px;
        }}

        .footer {{
          box-sizing: border-box;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 15.36px;
          width: 100%;
          border-top: 1px solid #E4E4E7;
          padding: 10.24px 0 12.8px;
          font-variant-numeric: tabular-nums;
        }}

        .brand {{ display: flex; align-items: center; gap: 10.24px; min-width: 0; }}
        .brand img {{ display: block; height: 15.36px; flex: none; }}
        /* legal name above the email: a two-line block centred on the wordmark reads as aligned, where a single
           line next to it never looked centred */
        .entity {{ min-width: 0; }}
        .entity div {{ font-family: Inter, sans-serif; font-size: 11.52px; line-height: 14.08px; font-weight: 400; color: #6E6E77; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .meta {{ flex: none; font-family: Inter, sans-serif; font-size: 11.52px; line-height: 15.36px; font-weight: 400; color: #6E6E77; text-align: right; white-space: nowrap; }}
        .meta b {{ font-family: Inter, sans-serif; font-size: 11.52px; line-height: 15.36px; font-weight: 500; color: #3F3F46; }}
        .pageNumber, .totalPages {{ font-family: Inter, sans-serif; font-size: 11.52px; line-height: 15.36px; color: #6E6E77; }}
"""
new_footer_body = f"""  body
    .footer
      .brand
        img src="data:image/png;base64,{logo}" alt="Lerian"
        - if entity
          .entity
            div = entity.legal_name.presence || entity.name
            div = entity.email.presence || 'lerian.studio'
      .meta
        b = number
        = " · "
        == page_numbering
"""
style_at = footer.index(old_footer_style_start)
head_part = footer[:style_at]
# the localized counter line stays exactly as upstream builds it; the billing entity goes right after it
counter = '- page_numbering = I18n.t("document.page_numbering", current: \'<span class="pageNumber"></span>\', total: \'<span class="totalPages"></span>\')\n'
assert head_part.count(counter) == 1, f"{FOOTER}: upstream page_numbering line moved"
head_part = head_part.replace(counter, counter + new_footer_vars)
footer_out = head_part + new_footer_style + new_footer_body
(REPO / FOOTER).write_text(footer_out, encoding="utf-8")
print(f"wrote {FOOTER} ({len(footer_out)} bytes) from upstream {FOOTER_SHA} (read from {footer_rev})")
