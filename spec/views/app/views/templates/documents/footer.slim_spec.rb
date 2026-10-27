# frozen_string_literal: true

require "rails_helper"

RSpec.describe "templates/documents/footer.slim" do
  subject(:rendered_template) { I18n.with_locale(locale) { SlimHelper.render("templates/documents/footer", context) } }

  let(:locale) { :"pt-BR" }
  let(:organization) { create(:organization) }
  let(:billing_entity) do
    create(:billing_entity, organization:, name: "Lerian", legal_name: "Lerian Studio Ltda", email: "billing@lerian.studio")
  end

  context "with an invoice" do
    let(:context) do
      create(:invoice, organization:, billing_entity:, number: "LER-2026-001", issuing_date: Date.new(2026, 10, 27))
    end

    it "renders the brand, the document reference and the localized page counter" do
      expect(rendered_template).to include('alt="Lerian"')
      expect(rendered_template).to include('<div class="brand">')
      expect(rendered_template).not_to match(/class="(left|center|right|date|title|url)"/)
      expect(rendered_template).to include("Lerian Studio Ltda")
      expect(rendered_template).to include("billing@lerian.studio")
      expect(rendered_template).to include("Lerian Clients · Billing")
      expect(rendered_template).to include(
        "Fatura LER-2026-001 · 27/10/2026 · " \
        'Página <span class="pageNumber"></span> de <span class="totalPages"></span>'
      )
    end

    context "when the billing entity has no legal name" do
      let(:billing_entity) { create(:billing_entity, organization:, name: "Lerian", legal_name: nil, email: nil) }

      it "falls back to its name and the default email" do
        expect(rendered_template).to include("Lerian")
        expect(rendered_template).to include("lerian.studio")
      end
    end
  end

  context "with a credit note" do
    let(:invoice) { create(:invoice, organization:, billing_entity:) }
    let(:context) { create(:credit_note, invoice:, number: "CN-123", issuing_date: Date.new(2026, 10, 27)) }

    it "renders the number and issuing date without an invoice name" do
      expect(rendered_template).to include("Lerian Studio Ltda")
      expect(rendered_template).to include(
        'CN-123 · 27/10/2026 · Página <span class="pageNumber"></span> de <span class="totalPages"></span>'
      )
    end
  end

  context "with a payment receipt" do
    let(:locale) { :en }
    let(:context) { create(:payment_receipt, organization:, billing_entity:, number: "PR-123") }

    it "falls back to the number and the page counter" do
      expect(rendered_template).to include("Lerian Studio Ltda")
      expect(rendered_template).to include(
        'PR-123 · Page <span class="pageNumber"></span> of <span class="totalPages"></span>'
      )
    end
  end
end
