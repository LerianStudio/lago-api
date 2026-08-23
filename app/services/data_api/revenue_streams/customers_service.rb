# frozen_string_literal: true

module DataApi
  module RevenueStreams
    class CustomersService < DataApi::BaseService
      Result = BaseResult[:data_revenue_streams_customers]

      def call
        return result.forbidden_failure! unless License.premium?

        data_revenue_streams_customers = http_client.get(headers:, params:)
        result.data_revenue_streams_customers = data_revenue_streams_customers
        result
      end

      private

      # See DataApi::BaseService#unconfigured_payload. This resolver reads
      # result.data_revenue_streams_customers["revenue_streams_customers"] and ["meta"], feeding
      # Types::DataApi::Metadata whose five fields are all `null: false`, so the
      # empty payload must be a keyed hash carrying full metadata, not an array.
      def unconfigured_payload
        {"revenue_streams_customers" => [], "meta" => DataApi::BaseService::EMPTY_METADATA}
      end

      def action_path
        "revenue_streams/#{organization.id}/customers/"
      end
    end
  end
end
