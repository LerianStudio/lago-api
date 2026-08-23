# frozen_string_literal: true

module DataApi
  module Mrrs
    class PlansService < DataApi::BaseService
      Result = BaseResult[:data_mrrs_plans]

      def call
        return result.forbidden_failure! unless License.premium?

        data_mrrs_plans = http_client.get(headers:, params:)

        result.data_mrrs_plans = data_mrrs_plans
        result
      end

      private

      # See DataApi::BaseService#unconfigured_payload. This resolver reads
      # result.data_mrrs_plans["mrrs_plans"] and ["meta"], feeding
      # Types::DataApi::Metadata whose five fields are all `null: false`, so the
      # empty payload must be a keyed hash carrying full metadata, not an array.
      def unconfigured_payload
        {"mrrs_plans" => [], "meta" => DataApi::BaseService::EMPTY_METADATA}
      end

      def action_path
        "mrrs/#{organization.id}/plans/"
      end
    end
  end
end
