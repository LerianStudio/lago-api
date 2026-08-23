# frozen_string_literal: true

require "rails_helper"

# Lerian patch: guard for a Data API that is not deployed.
# See DataApi::BaseService for the full rationale.
RSpec.describe DataApi::BaseService do
  let(:organization) { create(:organization) }

  around do |example|
    previous = ENV["LAGO_DATA_API_URL"]
    example.run
  ensure
    ENV["LAGO_DATA_API_URL"] = previous
  end

  context "when LAGO_DATA_API_URL is not set" do
    before { ENV.delete("LAGO_DATA_API_URL") }

    it "returns a successful, empty result instead of raising" do
      result = DataApi::RevenueStreamsService.call(organization)

      expect(result).to be_success
      expect(result.revenue_streams).to eq([])
    end

    it "makes no HTTP request at all" do
      DataApi::RevenueStreamsService.call(organization)

      expect(a_request(:any, //)).not_to have_been_made
    end

    it "answers the pagination metadata the collection_type resolves from" do
      payload = DataApi::RevenueStreamsService.call(organization).revenue_streams

      # graphql-pagination resolves both `collection` and `metadata` from this
      # same object, so a bare [] would raise NoMethodError on `metadata`.
      expect(payload.current_page).to eq(1)
      expect(payload.limit_value).to be_a(Integer)
      expect(payload.total_count).to eq(0)
      expect(payload.total_pages).to eq(0)
    end

    it "returns a keyed payload for the services whose resolver indexes it" do
      payload = DataApi::Mrrs::PlansService.call(organization).data_mrrs_plans

      expect(payload["mrrs_plans"]).to eq([])
      expect(payload["meta"]).to include(
        "current_page" => 1,
        "next_page" => 0,
        "prev_page" => 0,
        "total_count" => 0,
        "total_pages" => 0
      )
    end

    it "keeps every Types::DataApi::Metadata field non-null" do
      meta = DataApi::RevenueStreams::PlansService
        .call(organization).data_revenue_streams_plans["meta"]

      %w[current_page next_page prev_page total_count total_pages].each do |field|
        expect(meta[field]).to be_a(Integer), "#{field} must be a non-null Integer"
      end
    end
  end

  context "when LAGO_DATA_API_URL is blank" do
    before { ENV["LAGO_DATA_API_URL"] = "  " }

    it "is treated the same as unset" do
      result = DataApi::RevenueStreamsService.call(organization)

      expect(result).to be_success
      expect(result.revenue_streams).to eq([])
    end
  end

  context "when LAGO_DATA_API_URL is set" do
    let(:body_response) { File.read("spec/fixtures/lago_data_api/revenue_streams.json") }

    before do
      ENV["LAGO_DATA_API_URL"] = "http://data-api.test"
      stub_request(:get, "http://data-api.test/revenue_streams/#{organization.id}/")
        .to_return(status: 200, body: body_response, headers: {})
    end

    it "still performs the HTTP request, unchanged" do
      result = DataApi::RevenueStreamsService.call(organization)

      expect(result).to be_success
      expect(result.revenue_streams.count).to eq(12)
      expect(a_request(:get, "http://data-api.test/revenue_streams/#{organization.id}/"))
        .to have_been_made.once
    end
  end
end
