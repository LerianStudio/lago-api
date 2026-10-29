# frozen_string_literal: true

class MoneyHelper
  SYMBOLS_CURRENCIES = %w[$ € £ ¥].freeze
  DEFAULT_STUB_CURRENCY = "USD"

  def self.format(money)
    money&.format(
      format: currency_format(money&.currency),
      decimal_mark: I18n.t("money.decimal_mark"),
      thousands_separator: I18n.t("money.thousands_separator")
    )
  end

  # Lerian invoice branding (lerian/invoice-branding): renders a table amount as a bare number, because the
  # invoice tables print the document currency once, in the amount column head. Accepts a Money or an already
  # formatted String; the currency may be a prefix or a suffix. A fiat currency (ISO code or symbol) is dropped;
  # any other unit, i.e. a pricing unit short name ("12.00 CREDITS"), stays as a suffix. With code: true the
  # currency stays as a suffix too, as the ISO code for a Money (the amount due and the total).
  # A minus in the amount ("-1.00 BRL", "-BRL 1.00", "BRL -1.00", "R$-1.00") is rendered once, in front of the
  # number, also when the sign argument is already "-". The number is the one format produces, unchanged.
  # A space, NBSP or narrow NBSP is a thousands separator ("1 234,56" in fr, nb, sv) only when a digit follows, so
  # the gap before a suffix currency stays outside the number; the gaps match [[:space:]], NBSP included.
  def self.cell(money, sign = "", code: false)
    text = money.is_a?(String) ? money : format(money).to_s
    match = text.match(/\A[[:space:]]*(-?)[[:space:]]*(\D*?)[[:space:]]*(-?)[[:space:]]*(\d(?:[\d.,]|[ \u00A0\u202F](?=\d))*)[[:space:]]*(\D*?)[[:space:]]*\z/)
    currency = match ? (match[2].presence || match[5]) : ""
    number = match ? match[4] : text
    negative = match && (match[1] == "-" || match[3] == "-")
    prefix = (negative && !sign.include?("-")) ? "-#{sign}" : sign
    unit = if code
      money.respond_to?(:currency) ? money.currency.iso_code : currency
    elsif !fiat_currency?(currency)
      currency
    end

    html = "<span class=\"money\"><span class=\"num\">#{ERB::Util.html_escape(prefix + number)}</span>"
    html += "<span class=\"cur\">#{ERB::Util.html_escape(unit)}</span>" if unit.present?
    "#{html}</span>"
  end

  def self.fiat_currency?(text)
    return false if text.blank?

    SYMBOLS_CURRENCIES.include?(text) || Money::Currency.find(text).present? || fiat_symbols.include?(text)
  end

  def self.fiat_symbols
    @fiat_symbols ||= Money::Currency.all.map(&:symbol).compact.to_set
  end

  def self.format_with_precision(amount_cents, currency)
    amount_cents = normalize_precision(amount_cents)
    money = Utils::MoneyWithPrecision.from_amount(amount_cents, currency)
    format(money)
  end

  def self.format_pricing_unit(amount_cents, currency)
    format_with_custom_currency(amount_cents, currency.short_name)
  end

  def self.format_pricing_unit_with_precision(amount_cents, currency)
    amount_cents = normalize_precision(amount_cents)
    format_with_custom_currency(amount_cents, currency.short_name)
  end

  def self.currency_format(money_currency)
    if SYMBOLS_CURRENCIES.include?(money_currency&.symbol)
      I18n.t("money.format")
    else
      I18n.t("money.custom_format", iso_code: money_currency&.iso_code)
    end
  end

  def self.normalize_precision(amount_cents)
    if amount_cents < 1
      BigDecimal("%.6g" % amount_cents)
    else
      amount_cents.round(6)
    end
  end

  def self.format_with_custom_currency(amount, currency_code)
    stub = Utils::MoneyWithPrecision.from_amount(amount, DEFAULT_STUB_CURRENCY)
    stub.format(
      format: "%n #{currency_code}",
      decimal_mark: I18n.t("money.decimal_mark"),
      thousands_separator: I18n.t("money.thousands_separator")
    )
  end
end
