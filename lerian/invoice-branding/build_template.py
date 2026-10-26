#!/usr/bin/env python3
"""Build the Lerian-branded Lago invoice template from upstream v4.slim.

Visual reference: the Alfarrabio "standard report" export (Inter, zinc
neutrals, yellow only as a small accent, bordered header card with the
wordmark, light table heads with a 2px rule, hairline rows, a quiet footer
with the wordmark and document metadata).

Keeps every data partial Lago ships (fees, totals, taxes, custom sections)
and only changes typography, colours, header and footer.

Input: the pristine upstream templates, read with `git show <sha>:<path>`
where <sha> is `upstream.sha` in .lerian-fork.yml, so the patch is always
rebuilt from upstream and never from an already branded copy.
Output: app/views/templates/invoices/v4.slim and v4/*.slim, overwritten in
place. Run from anywhere inside the repo: python3 lerian/invoice-branding/build_template.py
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


src = upstream(f"{TEMPLATES}/v4.slim")
logo = base64.b64encode((HERE / "lerian-logo.png").read_bytes()).decode()
inter = base64.b64encode((HERE / "fonts/inter-400-normal.woff2").read_bytes()).decode()
mono400 = base64.b64encode((HERE / "fonts/ibm-plex-mono-400-latin.woff2").read_bytes()).decode()
mono600 = base64.b64encode((HERE / "fonts/ibm-plex-mono-600-latin.woff2").read_bytes()).decode()

# 1. Fonts and tokens replace the Inter local() block (first @font-face up to the h1/h2/p reset)
start = src.index("      @font-face {")
end = src.index("      h1, h2, p { margin: 0; padding: 0; }")
head = f"""      @font-face {{
        font-family: 'Inter';
        font-style: normal;
        font-weight: 100 900;
        font-display: swap;
        src: url(data:font/woff2;base64,{inter}) format('woff2');
      }}
      @font-face {{
        font-family: 'IBM Plex Mono';
        font-style: normal;
        font-weight: 400;
        src: url(data:font/woff2;base64,{mono400}) format('woff2');
      }}
      @font-face {{
        font-family: 'IBM Plex Mono';
        font-style: normal;
        font-weight: 600;
        src: url(data:font/woff2;base64,{mono600}) format('woff2');
      }}

      :root {{
        --border-color: #E4E4E7;
        --ink: #18181B;
        --muted: #71717A;
        --head: #F4F4F5;
        --chip: #E4E4E7;
        --accent: #FACC15;
        --mono: 'IBM Plex Mono', 'DejaVu Sans Mono', ui-monospace, Menlo, monospace;
      }}
"""
src = src[:start] + head + src[end:]

# 2. Typography and colours
src = src.replace("html { font-family: Inter, sans-serif; }",
                  "html { font-family: Inter, sans-serif; color: var(--ink); }\n      body { padding-bottom: 0; }")
src = src.replace("#19212e", "var(--ink)").replace("#19212E", "var(--ink)")
src = src.replace("#66758f", "var(--muted)").replace("#66758F", "var(--muted)")
src = src.replace("h1 { color: var(--ink); font-weight: 700; font-size: 24px; line-height: 32px; }",
                  "h1 { color: var(--ink); font-weight: 700; font-size: 26px; line-height: 32px; letter-spacing: -0.3px; }")
src = src.replace("      .body-1 {\n        color: var(--ink);\n        font-weight: 600;",
                  "      .body-1 {\n        color: var(--muted);\n        font-weight: 600;\n        text-transform: uppercase;\n        letter-spacing: 0.5px;")

extra_css = """
      .brand-card { display: flex; align-items: center; justify-content: space-between; border: 1px solid var(--border-color); border-radius: 8px; padding: 10px 16px; margin-bottom: 16px; }
      .brand-card img { height: 18px; }
      .brand-card .doc-kind { font-family: var(--mono); font-size: 9px; font-weight: 600; letter-spacing: 1.2px; text-transform: uppercase; color: var(--muted); }
      .doc-title { margin-bottom: 8px; }
      .body-1, .body-2 { line-height: 14px !important; }
      .body-3 { line-height: 13px !important; }
      .invoice-resume-table tr td { padding-top: 3px; padding-bottom: 3px; }
      .mb-24 { margin-bottom: 14px; }
      .chips { display: flex; gap: 8px; margin-bottom: 18px; }
      .chip { display: inline-block; font-family: var(--mono); font-size: 8.5px; font-weight: 500; letter-spacing: 0.3px; line-height: 14px; padding: 2px 8px; border-radius: 4px; background: var(--chip); color: var(--ink); }
      .chip.dark { background: #27272A; color: #FFFFFF; }
      .chip.accent { background: var(--accent); color: var(--ink); }
      .invoice-information-table tr td:first-child { color: var(--muted); }
      .invoice-information-table tr td:last-child { font-family: var(--mono); font-size: 10px; }
      .amount-due { display: flex; align-items: baseline; gap: 14px; padding: 8px 16px; background: var(--head); border-radius: 8px; }
      .amount-due .title-2 { font-size: 22px; font-weight: 600; font-variant-numeric: tabular-nums; }
      .invoice-resume-table tr.first_child td, .invoice-resume-table tr:first-child td { background: var(--head); color: var(--muted); font-weight: 600; font-size: 8.5px; text-transform: uppercase; letter-spacing: 0.6px; padding: 8px 12px; border-bottom: 1px solid var(--accent); font-family: Inter, sans-serif; white-space: normal; line-height: 12px; }
      .invoice-resume-table tr td { padding-left: 12px; padding-right: 12px; }
      .invoice-resume-table td:not(:first-child) { font-family: var(--mono); font-size: 10px; font-variant-numeric: tabular-nums; white-space: nowrap; }
      .invoice-resume .total-table td:nth-child(3) { font-family: var(--mono); font-size: 10px; font-variant-numeric: tabular-nums; white-space: nowrap; }
      .invoice-resume .total-table tr:last-child td { font-size: 12px; font-weight: 700; }
      .invoice-resume .total-table tr:last-child td:nth-child(3) { font-family: var(--mono); font-weight: 600; font-size: 10px; }
      .money { display: inline-grid; grid-template-columns: auto minmax(11ch, auto); column-gap: 5px; white-space: nowrap; }
      .money .cur { text-align: left; }
      .money .num { text-align: right; font-variant-numeric: tabular-nums; }
      .amount-due .money { grid-template-columns: auto auto; column-gap: 8px; }
      .payment-block { break-inside: avoid; }
      /* tables: plain ink inside cells, body-1 muted/uppercase is for section labels only */
      .invoice-resume-table td.body-1, .invoice-resume-table td .body-1, .total-table td.body-1, .invoice-resume-table tr.charge-name td { color: var(--ink); text-transform: none; letter-spacing: 0; font-weight: 500; }
      .invoice-resume-table td, .total-table td { vertical-align: middle; }
      /* 5-column fee tables: widths that fit the mono amounts without clipping (upstream caps cols at 10vw) */
      .invoice-resume-table { table-layout: fixed; width: 100%; }
      .invoice-resume-table td:first-child { width: 38%; }
      .invoice-resume-table td:first-child:nth-last-child(2) { width: 70%; }
      .invoice-resume-table td:nth-child(2):nth-last-child(1) { width: 30%; }
      .invoice-resume-table td:nth-child(2) { width: 8%; max-width: none; }
      .invoice-resume-table td:nth-child(3) { width: 19%; max-width: none; }
      .invoice-resume-table td:nth-child(4) { width: 16%; }
      .invoice-resume-table td:nth-child(5) { width: 19%; max-width: none; }
      .invoice-resume-table td:not(:first-child) { padding-left: 8px; padding-right: 8px; }
      .invoice-resume-table td:last-child { padding-right: 12px; }
      .invoice-resume-table:has(td:nth-child(5)) { width: calc(100% - 1px); }
      .invoice-resume-table tr.first_child td, .invoice-resume-table tr:first-child td { white-space: nowrap; letter-spacing: 0.3px; vertical-align: middle; }
      .invoice-resume-table tr.first_child td:not(:first-child), .invoice-resume-table tr:first-child td:not(:first-child) { padding-left: 8px; padding-right: 8px; }
      .invoice-resume-table tr.first_child td:last-child, .invoice-resume-table tr:first-child td:last-child { padding-right: 12px; }
      /* totals block: same right edge and padding as the tables above it */
      .invoice-resume .total-table td:nth-child(3) { padding-right: 12px; }
      .invoice-resume .total-table td:nth-child(2) { padding-left: 12px; }
      .invoice-resume .total-table tr:last-child td { color: var(--ink); }
      .invoice-resume .total-table tr td { padding-top: 6px; padding-bottom: 6px; }
      .payment-detail { white-space: pre-line; }
            .brand-footer { border-top: 1px solid var(--border-color); padding-top: 10px; margin-top: 20px; display: flex; align-items: center; justify-content: space-between; }
      .brand-footer .left { display: flex; align-items: center; gap: 10px; }
      .brand-footer img { height: 12px; }
      .brand-footer .studio { font-size: 8.5px; line-height: 11px; font-weight: 600; color: var(--ink); }
      .brand-footer .studio span { display: block; font-weight: 400; color: var(--muted); }
      .brand-footer .meta { font-family: var(--mono); font-size: 7.5px; line-height: 11px; color: var(--muted); text-align: right; }
      .brand-footer .meta b { color: var(--ink); font-weight: 600; }
"""
src = src.replace("      .alert {", extra_css + "      .alert {", 1)

# 3. Header card + title + chips
old_header = """    .wrapper
      .mb-24
        h1.invoice-title = document_invoice_name
        - if billing_entity.logo.present?
          img.header-logo src="data:#{billing_entity.logo.content_type};base64,#{billing_entity.base64_logo}"
"""
# Amount cells call MoneyHelper.cell (app/views/helpers/money_helper.rb, part of this patch):
# it splits a formatted amount into currency and number spans so they align across tables.
new_header = """    .wrapper
      .brand-card
        - if billing_entity.logo.present?
          img src="data:#{billing_entity.logo.content_type};base64,#{billing_entity.base64_logo}"
        - else
          img src="data:image/png;base64,LOGO_B64" alt="Lerian"
        .doc-kind = document_invoice_name
      h1.doc-title = number
      - pt = I18n.locale.to_s.start_with?('pt')
      - status_label = status.to_s == 'voided' ? (pt ? 'Cancelada' : 'Voided') : ({pending: (pt ? 'Pendente' : 'Pending'), succeeded: (pt ? 'Pago' : 'Paid'), failed: (pt ? 'Falhou' : 'Failed')}[payment_status.to_s.to_sym] || payment_status.to_s)
      .chips
        span.chip.dark = status_label
        span.chip = I18n.l(issuing_date, format: :default)
        span.chip.accent = I18n.t('invoice.due_date', date: I18n.l(payment_due_date, format: :default))
"""
assert old_header in src
src = src.replace(old_header, new_header).replace("LOGO_B64", logo)

# 4. Amount due as a quiet panel
old_amount = """      .mb-24
        h2.title-2.mb-4 = MoneyHelper.format(total_amount)
        .body-1 = I18n.t('invoice.due_date', date: I18n.l(payment_due_date, format: :default))
"""
new_amount = """      .mb-24.amount-due
        .body-1 = I18n.t('invoice.total')
        h2.title-2 == MoneyHelper.cell(total_amount)
"""
assert old_amount in src
src = src.replace(old_amount, new_amount)

# 5. Footer: invoice_footer becomes "Payment detail"; drop the watermark; add the quiet brand footer
old_footer = """      p.body-3.mb-24 = LineBreakHelper.break_lines(billing_entity.invoice_footer)

      == SlimHelper.render('templates/invoices/v4/_powered_by_logo', self)
"""
new_footer = """      - if billing_entity.invoice_footer.present?
        .mb-24.payment-block
          p.body-1.mb-4 = I18n.locale.to_s.start_with?('pt') ? 'Dados de pagamento' : 'Payment detail'
          p.body-2.payment-detail = LineBreakHelper.break_lines(billing_entity.invoice_footer)

      .brand-footer
        .left
          img src="data:image/png;base64,LOGO_B64" alt="Lerian"
          .studio
            | #{billing_entity.legal_name.presence || billing_entity.name}
            span = billing_entity.email.presence || 'lerian.studio'
        .meta
          b Lerian Clients · Billing
          br
          | #{document_invoice_name} #{number} · #{I18n.l(issuing_date, format: :default)}

"""
assert old_footer in src
src = src.replace(old_footer, new_footer).replace("LOGO_B64", logo)

# 6. Partials: td cells whose whole content is MoneyHelper.format(...) become MoneyHelper.cell(...)
cell_re = re.compile(r"^(\s*)(td\.body-\d\s+)?=\s*(?:'-'\s*\+\s*)?((?:MoneyHelper\.format|FeeDisplayHelper\.format_(?:amount|precise_unit_amount|as_currency|with_precision))\(.*\))\s*$")
pdir = REPO / TEMPLATES / "v4"
pdir.mkdir(parents=True, exist_ok=True)
names = sorted(p for p in git("ls-tree", "--name-only", UPSTREAM_SHA, f"{TEMPLATES}/v4/").decode("utf-8").splitlines()
               if p.endswith(".slim"))
changed = 0
for name in names:
    lines = upstream(name).split("\n")
    out_lines = []
    for ln in lines:
        m = cell_re.match(ln)
        if m:
            indent, tag, expr = m.group(1), m.group(2) or "", m.group(3)
            sign = ", '-'" if "'-'" in ln else ""
            ln = f"{indent}{tag}== MoneyHelper.cell(({expr}){sign})"
            changed += 1
        out_lines.append(ln)
    (pdir / pathlib.PurePosixPath(name).name).write_text("\n".join(out_lines), encoding="utf-8")
print(f"partials: {changed} amount cells converted in {len(names)} files under {pdir.relative_to(REPO)}")

out = REPO / TEMPLATES / "v4.slim"
out.write_text(src, encoding="utf-8")
print(f"wrote {out.relative_to(REPO)} ({len(src)} bytes) from upstream {UPSTREAM_SHA}")
