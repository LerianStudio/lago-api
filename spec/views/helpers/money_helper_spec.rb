# frozen_string_literal: true

require "rails_helper"

RSpec.describe MoneyHelper do
  subject(:helper) { described_class }

  describe ".format" do
    let(:currency) { "USD" }
    let(:amount) { Money.new(100, currency) }

    it "formats the amount" do
      expect(helper.format(amount)).to eq("$1.00")
    end

    context "when currency does not use a well known symbol" do
      let(:currency) { "BHD" }

      it "formats the amount" do
        expect(helper.format(amount)).to eq("BHD 0.100")
      end
    end
  end

  describe ".cell" do
    def cell_html(number, unit = nil)
      unit_html = unit ? "<span class=\"cur\">#{unit}</span>" : ""
      "<span class=\"money\"><span class=\"num\">#{number}</span>#{unit_html}</span>"
    end

    it "drops a prefixed ISO code" do
      expect(helper.cell("BRL 1.234,56")).to eq(cell_html("1.234,56"))
    end

    it "drops a prefixed symbol" do
      expect(helper.cell("$1,234.56")).to eq(cell_html("1,234.56"))
    end

    it "drops a suffixed fiat currency" do
      expect(helper.cell("1.234,56 €")).to eq(cell_html("1.234,56"))
    end

    it "keeps a pricing unit as a suffix" do
      expect(helper.cell("12.50 CREDITS")).to eq(cell_html("12.50", "CREDITS"))
    end

    it "prepends the sign to the number" do
      expect(helper.cell("$1,234.56", "-")).to eq(cell_html("-1,234.56"))
    end

    it "keeps the sign of a suffixed currency amount" do
      expect(helper.cell("-1.00 BRL")).to eq(cell_html("-1.00"))
    end

    it "keeps a sign written before a prefixed currency" do
      expect(helper.cell("-BRL 1.00")).to eq(cell_html("-1.00"))
    end

    it "moves the minus of a prefixed ISO code amount in front of the number" do
      expect(helper.cell("BRL -1.00")).to eq(cell_html("-1.00"))
    end

    it "moves the minus of a symbol amount in front of the number" do
      expect(helper.cell("R$-1.234,56")).to eq(cell_html("-1.234,56"))
    end

    it "renders the sign once when the amount is already negative" do
      expect(helper.cell("-1.00 BRL", "-")).to eq(cell_html("-1.00"))
    end

    it "formats a negative Money before taking the number" do
      expect(helper.cell(Money.new(-123_456, "USD"))).to eq(cell_html("-1,234.56"))
    end

    it "formats a Money before taking the number" do
      expect(helper.cell(Money.new(123_456, "USD"))).to eq(cell_html("1,234.56"))
    end

    it "keeps the ISO code of a Money with code: true" do
      expect(helper.cell(Money.new(123_456, "USD"), code: true)).to eq(cell_html("1,234.56", "USD"))
    end

    it "keeps the formatted currency of a String with code: true" do
      expect(helper.cell("BRL 24,657.40", code: true)).to eq(cell_html("24,657.40", "BRL"))
    end

    it "keeps a plain String without currency as the number" do
      expect(helper.cell("12.5")).to eq(cell_html("12.5"))
    end

    it "keeps a String without digits whole and escapes it" do
      expect(helper.cell("<b>N/A</b>")).to eq(cell_html("&lt;b&gt;N/A&lt;/b&gt;"))
    end

    it "renders an empty number for nil" do
      expect(helper.cell(nil)).to eq(cell_html(""))
    end

    it "keeps space thousands separators in the number" do
      expect(helper.cell("1 234,56 BRL")).to eq(cell_html("1 234,56"))
    end

    it "keeps the ISO code once after a number with space thousands separators" do
      expect(helper.cell("1 234,56 BRL", code: true)).to eq(cell_html("1 234,56", "BRL"))
    end

    it "renders the sign once before a number with space thousands separators" do
      expect(helper.cell("-1 234,56 BRL")).to eq(cell_html("-1 234,56"))
    end

    it "keeps NBSP and narrow NBSP thousands separators in the number" do
      expect(helper.cell("1\u00A0234\u202F567,89\u00A0BRL")).to eq(cell_html("1\u00A0234\u202F567,89"))
    end

    it "renders a Money formatted in a locale with space thousands separators" do
      html = I18n.with_locale(:fr) { helper.cell(Money.new(123_456, "BRL"), code: true) }
      expect(html).to eq(cell_html("1 234,56", "BRL"))
    end
  end

  describe ".format_with_precision" do
    let(:currency) { "USD" }

    it "rounds big decimals to 6 digits" do
      html = helper.format_with_precision(BigDecimal("123.12345678"), currency)

      expect(html).to eq("$123.123457")
    end

    it "shows six significant digits for values < 1" do
      html = helper.format_with_precision(BigDecimal("0.000000012345"), currency)

      expect(html).to eq("$0.000000012345")
    end

    it "shows only six significant digits for values < 1" do
      html = helper.format_with_precision(BigDecimal("0.100000012345"), currency)

      expect(html).to eq("$0.10")
    end

    context "when currency does not use a well known symbol" do
      let(:currency) { "BHD" }

      it "rounds big decimals to 6 digits" do
        html = helper.format_with_precision(BigDecimal("123.12345678"), currency)

        expect(html).to eq("BHD 123.123457")
      end

      it "shows six significant digits for values < 1" do
        html = helper.format_with_precision(BigDecimal("0.000000012345"), currency)

        expect(html).to eq("BHD 0.000000012345")
      end

      it "shows only six significant digits for values < 1" do
        html = helper.format_with_precision(BigDecimal("0.100000012345"), currency)

        expect(html).to eq("BHD 0.100")
      end
    end
  end

  describe ".format_pricing_unit" do
    subject { helper.format_pricing_unit(amount_cents, currency) }

    let(:currency) { build_stubbed(:pricing_unit) }
    let(:amount_cents) { 100 }

    it "formats the amount" do
      expect(subject).to eq "100.00 #{currency.short_name}"
    end
  end

  describe ".format_pricing_unit_with_precision" do
    subject { helper.format_pricing_unit_with_precision(amount, currency) }

    let(:currency) { build_stubbed(:pricing_unit) }

    context "when amount bigger than 1" do
      let(:amount) { BigDecimal("123.12345678") }

      it "rounds big decimals to 6 digits" do
        expect(subject).to eq "123.123457 #{currency.short_name}"
      end
    end

    context "when amount smaller than 1" do
      let(:amount) { BigDecimal("0.000000012345") }

      it "shows six significant digits for values < 1" do
        expect(subject).to eq "0.000000012345 #{currency.short_name}"
      end
    end
  end
end
