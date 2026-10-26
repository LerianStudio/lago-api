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

  # Lerian invoice branding (lerian/invoice-branding): renders a table amount as separate currency
  # and number spans so currency codes and decimals line up across the invoice tables.
  # Accepts a Money or an already formatted String; the currency may be a prefix or a suffix.
  # A minus in the amount ("-1.00 BRL", "-BRL 1.00", "BRL -1.00", "R$-1.00") is taken apart from the
  # currency and rendered once, in front of it, also when the sign argument is already "-".
  def self.cell(money, sign = "")
    text = money.is_a?(String) ? money : format(money).to_s
    match = text.match(/\A\s*(-?)\s*(\D*?)\s*(-?)\s*(\d[\d.,]*)\s*(\D*?)\s*\z/)
    currency = match ? (match[2].presence || match[5]) : ""
    number = match ? match[4] : text
    negative = match && (match[1] == "-" || match[3] == "-")
    prefix = (negative && !sign.include?("-")) ? "-#{sign}" : sign

    "<span class=\"money\"><span class=\"cur\">#{ERB::Util.html_escape(prefix + currency)}</span>" \
      "<span class=\"num\">#{ERB::Util.html_escape(number)}</span></span>"
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
