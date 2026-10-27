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
place. v4.slim and the standalone roots (v4/one_off, charge, fixed_charge,
self_billed) get the brand; the other partials only get aligned amount cells.
Also app/views/templates/documents/footer.slim, the page footer Gotenberg
repeats on every page, built from the upstream #6489 file (FOOTER_SHA, read from its cherry-pick).
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


logo = base64.b64encode((HERE / "lerian-logo.png").read_bytes()).decode()
inter = base64.b64encode((HERE / "fonts/inter-400-normal.woff2").read_bytes()).decode()
mono400 = base64.b64encode((HERE / "fonts/ibm-plex-mono-400-latin.woff2").read_bytes()).decode()
mono600 = base64.b64encode((HERE / "fonts/ibm-plex-mono-600-latin.woff2").read_bytes()).decode()

# 1. Fonts and tokens replace the Inter local() block (first @font-face up to the h1/h2/p reset)
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

# 2. Typography and colours (applied in brand() below), plus the extra rules inserted before `.alert {`

extra_css = """
      .brand-card { display: flex; align-items: center; justify-content: space-between; border: 1px solid var(--border-color); border-radius: 8px; padding: 6px 16px; margin-bottom: 10px; }
      .brand-card img { height: 18px; }
      .brand-card .doc-kind { font-family: var(--mono); font-size: 9px; font-weight: 600; letter-spacing: 1.2px; text-transform: uppercase; color: var(--muted); }
      .doc-title { margin-bottom: 6px; }
      .body-1, .body-2 { line-height: 14px !important; }
      .body-3 { line-height: 13px !important; }
      .invoice-resume-table tr td { padding-top: 3px; padding-bottom: 3px; }
      .mb-24 { margin-bottom: 10px; }
      /* gap between billing-period groups (upstream 24px); kept tight so two-period invoices fit one page */
      .mt-24 { margin-top: 14px; }
      .chips { display: flex; gap: 8px; margin-bottom: 10px; }
      .chip { display: inline-block; font-family: var(--mono); font-size: 8.5px; font-weight: 500; letter-spacing: 0.3px; line-height: 14px; padding: 2px 8px; border-radius: 4px; background: var(--chip); color: var(--ink); }
      .chip.dark { background: #27272A; color: #FFFFFF; }
      .chip.accent { background: var(--accent); color: var(--ink); }
      .invoice-information-table tr td:first-child { color: var(--muted); }
      .invoice-information-table tr td:last-child { font-family: var(--mono); font-size: 10px; }
      .amount-due { display: flex; align-items: baseline; gap: 14px; padding: 6px 16px; background: var(--head); border-radius: 8px; }
      .amount-due .title-2 { font-size: 22px; font-weight: 600; font-variant-numeric: tabular-nums; }
      .invoice-resume-table tr.first_child td, .invoice-resume-table tr:first-child td { background: var(--head); color: var(--muted); font-weight: 600; font-size: 8.5px; text-transform: uppercase; letter-spacing: 0.6px; padding: 6px 12px; border-bottom: 1px solid var(--accent); font-family: Inter, sans-serif; white-space: normal; line-height: 12px; }
      .invoice-resume-table tr td { padding-left: 12px; padding-right: 12px; }
      .invoice-resume-table td:not(:first-child) { font-family: var(--mono); font-size: 10px; font-variant-numeric: tabular-nums; white-space: nowrap; }
      .invoice-resume .total-table td:nth-child(3) { font-family: var(--mono); font-size: 10px; font-variant-numeric: tabular-nums; white-space: nowrap; }
      .invoice-resume .total-table tr:last-child td { font-size: 12px; font-weight: 700; }
      .invoice-resume .total-table tr:last-child td:nth-child(3) { font-family: var(--mono); font-weight: 600; font-size: 10px; }
      .money { display: inline-grid; grid-template-columns: auto minmax(11ch, auto); column-gap: 5px; white-space: nowrap; }
      .money .cur { text-align: left; }
      .money .num { text-align: right; font-variant-numeric: tabular-nums; }
      .amount-due .money { grid-template-columns: auto auto; column-gap: 8px; }
      /* own bottom margin, so the payment block keeps the lerian.4 spacing whatever follows it */
      .payment-block { break-inside: avoid; margin-bottom: 8px; }
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
      /* one_off.slim sets `tr td:last-child { width: 18% }` (higher specificity): keep the 5th column at 19% so every root shares one grid */
      .invoice-resume-table tr td:nth-child(5):last-child { width: 19%; }
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
      .invoice-resume .total-table tr td { padding-top: 5px; padding-bottom: 5px; }
      .payment-detail { white-space: pre-line; }
"""

# 3. Header card + title + chips. self_billed has no billing entity logo upstream (the document is
# issued on behalf of the customer), so it only gets the Lerian wordmark.
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
        span.chip.accent = DUE_EXPR
"""
old_header_self_billed = """    .wrapper
      .mb-24
        h1.invoice-title = document_invoice_name
"""
new_header_self_billed = new_header.replace("""        - if billing_entity.logo.present?
          img src="data:#{billing_entity.logo.content_type};base64,#{billing_entity.base64_logo}"
        - else
          img src="data:image/png;base64,LOGO_B64" alt="Lerian"
""", """        img src="data:image/png;base64,LOGO_B64" alt="Lerian"
""")

# 4. Amount due as a quiet panel. The line under the amount (due date, or "already paid" for advance
# charges) moves into the accent chip of the header.
amount_re = re.compile(r"^      \.mb-24\n        h2\.title-2\.mb-4 = (.+)\n        \.body-1 = (.+)\n", re.M)


def new_amount(total_expr):
    # one_off.slim formats the total with total_amount.format(money.format, ...), i.e. the currency symbol;
    # every root passes the Money itself so the panel reads the ISO code like the tables (BRL, not R$).
    m = re.fullmatch(r"MoneyHelper\.format\((.+)\)", total_expr)
    money = m.group(1) if m else ("total_amount" if total_expr.startswith("total_amount.format(") else total_expr)
    return f"""      .mb-24.amount-due
        .body-1 = I18n.t('invoice.total')
        h2.title-2 == MoneyHelper.cell({money})
"""

# 5. Footer: invoice_footer becomes "Payment detail" and the watermark is dropped. The brand footer is not
# part of the body: it is Gotenberg page chrome (documents/footer.slim, step 7), repeated on every page.
# self_billed keeps its legal self-billing statement and only drops the watermark.
old_footer = """      p.body-3.mb-24 = LineBreakHelper.break_lines(billing_entity.invoice_footer)

      == SlimHelper.render('templates/invoices/v4/_powered_by_logo', self)
"""
old_footer_self_billed = """
      == SlimHelper.render('templates/invoices/v4/_powered_by_logo', self)
"""
payment_block = """      - if billing_entity.invoice_footer.present?
        .mb-24.payment-block
          p.body-1.mb-4 = I18n.locale.to_s.start_with?('pt') ? 'Dados de pagamento' : 'Payment detail'
          p.body-2.payment-detail = LineBreakHelper.break_lines(billing_entity.invoice_footer)
"""


def replace_once(src, old, new, what):
    assert src.count(old) == 1, f"{what}: expected exactly one match upstream, found {src.count(old)}"
    return src.replace(old, new)


def brand(src, name):
    """Apply steps 1-5 to a root invoice template (v4.slim or a standalone v4/<kind>.slim)."""
    start = src.index("      @font-face {")
    end = src.index("      h1, h2, p { margin: 0; padding: 0; }")
    src = src[:start] + head + src[end:]
    src = src.replace("html { font-family: Inter, sans-serif; }",
                      "html { font-family: Inter, sans-serif; color: var(--ink); }\n      body { padding-bottom: 0; }")
    src = src.replace("#19212e", "var(--ink)").replace("#19212E", "var(--ink)")
    src = src.replace("#66758f", "var(--muted)").replace("#66758F", "var(--muted)")
    src = src.replace("h1 { color: var(--ink); font-weight: 700; font-size: 24px; line-height: 32px; }",
                      "h1 { color: var(--ink); font-weight: 700; font-size: 26px; line-height: 32px; letter-spacing: -0.3px; }")
    src = src.replace("      .body-1 {\n        color: var(--ink);\n        font-weight: 600;",
                      "      .body-1 {\n        color: var(--muted);\n        font-weight: 600;\n        text-transform: uppercase;\n        letter-spacing: 0.5px;")
    src = replace_once(src, "      .alert {", extra_css + "      .alert {", f"{name}: .alert")

    amounts = amount_re.findall(src)
    assert len(amounts) == 1, f"{name}: expected one amount block upstream, found {len(amounts)}"
    total_expr, due_expr = amounts[0]
    src = amount_re.sub(lambda _: new_amount(total_expr), src)

    if name == "self_billed":
        src = replace_once(src, old_header_self_billed, new_header_self_billed.replace("DUE_EXPR", due_expr), f"{name}: header")
        src = replace_once(src, old_footer_self_billed, "", f"{name}: footer")
    else:
        src = replace_once(src, old_header, new_header.replace("DUE_EXPR", due_expr), f"{name}: header")
        src = replace_once(src, old_footer, payment_block, f"{name}: footer")
    return src.replace("LOGO_B64", logo)


# Root templates Lago picks per invoice (Invoices::GeneratePdfService#template): v4.slim for subscription
# and progressive billing invoices, the standalone ones for one-off, advance charge, fixed charge and
# self-billed invoices. All of them get the brand.
STANDALONE = {"one_off", "charge", "fixed_charge", "self_billed"}
src = brand(upstream(f"{TEMPLATES}/v4.slim"), "v4")

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
    text = "\n".join(out_lines)
    stem = pathlib.PurePosixPath(name).stem
    if stem in STANDALONE:
        text = brand(text, stem)
    (pdir / pathlib.PurePosixPath(name).name).write_text(text, encoding="utf-8")
print(f"partials: {changed} amount cells converted in {len(names)} files under {pdir.relative_to(REPO)}")

out = REPO / TEMPLATES / "v4.slim"
out.write_text(src, encoding="utf-8")
print(f"wrote {out.relative_to(REPO)} ({len(src)} bytes) from upstream {UPSTREAM_SHA}")

# 7. Page footer: documents/footer.slim is the Gotenberg `footer.html` part (Utils::PdfGenerator), rendered by
# Chromium as page chrome at the bottom of every page, for invoices, credit notes and payment receipts. It comes
# from upstream #6489, cherry-picked onto the fork, so it is read from that commit (footer_source), not from upstream.sha.
# Chromium renders it in an isolated document: every style lives in its own <style> with an explicit size and
# colour on each text node (an unstyled footer renders at zero size), and fonts and the wordmark are base64
# (no network). Chromium injects its own stylesheet into the footer, with rules for .left, .center, .right,
# .date, .title, .url, .pageNumber and .totalPages: never use those class names for our own layout (only the
# page counter spans keep .pageNumber/.totalPages, which Chromium fills). Every @font-face has
# font-display: swap, otherwise text whose font is not loaded yet stays invisible in the footer. Inter
# prefers local() (the Gotenberg image ships it) with the data: url as fallback; the image has no
# IBM Plex Mono, so its data: url comes first and the stack falls back to DejaVu Sans Mono.
# Gotenberg 8 (the version production runs) does not apply `scale: 1.28` to the footer, so every value is the body design value
# (the former in-flow .brand-footer) multiplied by 1.28. Only invoices have document_invoice_name; credit notes
# and payment receipts fall back to upstream's content (number and page counter). The footer is always two lines
# (nowrap, the legal name is ellipsized) so the bottom margin in Utils::PdfGenerator always fits it.
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
new_footer_vars = """- doc_name = document_invoice_name if respond_to?(:document_invoice_name)
- doc_date = I18n.l(issuing_date, format: :default) if respond_to?(:issuing_date) && issuing_date
- entity = billing_entity if respond_to?(:billing_entity)
- doc_ref = [[doc_name, number].compact.join(" "), doc_date].compact.join(" · ")
"""
new_footer_style = f"""    style
      | @font-face {{
          font-family: 'Inter';
          font-style: normal;
          font-weight: 100 900;
          font-display: swap;
          src: local("Inter"), local("Inter-Regular"), url(data:font/woff2;base64,{inter}) format('woff2');
        }}
        @font-face {{
          font-family: 'IBM Plex Mono';
          font-style: normal;
          font-weight: 400;
          font-display: swap;
          src: url(data:font/woff2;base64,{mono400}) format('woff2'), local("IBM Plex Mono");
        }}
        @font-face {{
          font-family: 'IBM Plex Mono';
          font-style: normal;
          font-weight: 600;
          font-display: swap;
          src: url(data:font/woff2;base64,{mono600}) format('woff2'), local("IBM Plex Mono SemiBold");
        }}

        :root {{
          --border-color: #E4E4E7;
          --ink: #18181B;
          --muted: #71717A;
          --mono: 'IBM Plex Mono', 'DejaVu Sans Mono', monospace;
        }}

        body {{
          box-sizing: border-box;
          margin: 0;
          padding: 0 calc(0.42in + 10.24px);
          color: #71717A;
          print-color-adjust: exact;
          -webkit-print-color-adjust: exact;
          font-family: Inter, sans-serif;
          font-size: 10.88px;
          line-height: 14.08px;
        }}

        .footer {{
          box-sizing: border-box;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12.8px;
          width: 100%;
          border-top: 1px solid #E4E4E7;
          border-top-color: var(--border-color);
          padding: 7.68px 0 15.36px;
        }}

        .brand {{ display: flex; align-items: center; gap: 12.8px; min-width: 0; }}
        .brand img {{ display: block; height: 15.36px; flex: none; }}
        .studio {{ min-width: 0; font-family: Inter, sans-serif; font-size: 10.88px; line-height: 14.08px; font-weight: 600; color: #18181B; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .studio span {{ display: block; font-size: 10.88px; line-height: 14.08px; font-weight: 400; color: #71717A; overflow: hidden; text-overflow: ellipsis; }}
        .meta {{ flex: none; font-family: var(--mono); font-size: 9.6px; line-height: 14.08px; color: #71717A; text-align: right; white-space: nowrap; }}
        .meta b {{ font-family: var(--mono); font-size: 9.6px; line-height: 14.08px; font-weight: 600; color: #18181B; }}
        .meta span, .pageNumber, .totalPages {{ font-family: var(--mono); font-size: 9.6px; line-height: 14.08px; color: #71717A; }}
"""
new_footer_body = f"""  body
    .footer
      .brand
        img src="data:image/png;base64,{logo}" alt="Lerian"
        - if entity
          .studio
            | #{{entity.legal_name.presence || entity.name}}
            span = entity.email.presence || 'lerian.studio'
      .meta
        b Lerian Clients · Billing
        br
        span
          = "#{{doc_ref}} · "
          == page_numbering
"""
style_at = footer.index(old_footer_style_start)
body_at = footer.index(old_footer_body)
head_part = footer[:style_at]
# the localized counter line stays exactly as upstream builds it; the document reference goes right after it
counter = '- page_numbering = I18n.t("document.page_numbering", current: \'<span class="pageNumber"></span>\', total: \'<span class="totalPages"></span>\')\n'
assert head_part.count(counter) == 1, f"{FOOTER}: upstream page_numbering line moved"
head_part = head_part.replace(counter, counter + new_footer_vars)
footer_out = head_part + new_footer_style + new_footer_body
(REPO / FOOTER).write_text(footer_out, encoding="utf-8")
print(f"wrote {FOOTER} ({len(footer_out)} bytes) from upstream {FOOTER_SHA} (read from {footer_rev})")
