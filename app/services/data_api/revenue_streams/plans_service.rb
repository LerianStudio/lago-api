# frozen_string_literal: true

module DataApi
  module RevenueStreams
    class PlansService < DataApi::BaseService
      Result = BaseResult[:data_revenue_streams_plans]

      def call
        return result.forbidden_failure! unless License.premium?

        data_revenue_streams_plans = http_client.get(headers:, params:)

        result.data_revenue_streams_plans = data_revenue_streams_plans
        result
      end

      private

      # See DataApi::BaseService#unconfigured_payload. This resolver reads
      # result.data_revenue_streams_plans["revenue_streams_plans"] and ["meta"], feeding
      # Types::DataApi::Metadata whose five fields are all `null: false`, so the
      # empty payload must be a keyed hash carrying full metadata, not an array.
      def unconfigured_payload
        {"revenue_streams_plans" => [], "meta" => DataApi::BaseService::EMPTY_METADATA}
      end

      def action_path
        "revenue_streams/#{organization.id}/plans/"
      end
    end
  end
end
