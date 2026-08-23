# frozen_string_literal: true

require "lago_http_client"

module DataApi
  class BaseService < BaseService
    # Lerian patch: the Data API is a separate Lago component (getlago/data-api,
    # a private Docker Hub image) that is not deployed in any Lerian
    # environment, so LAGO_DATA_API_URL is unset.
    #
    # Upstream neither defaults nor validates it, so #endpoint_url produced a
    # host-less URL such as "/revenue_streams/<id>/". LagoHttpClient::Client
    # passes that straight to URI(), and the New Relic net/http wrapper then
    # rebuilds it as "http://:80/..." and raises URI::InvalidComponentError.
    # That surfaced as HTTP 500 on the Analytics and Forecasts screens and on
    # the public GET /api/v1/analytics/usage route.
    #
    # When the URL is missing we skip the HTTP call and return an empty but
    # SUCCESSFUL payload. A failed result would not work: the ten Data API
    # GraphQL resolvers read `result.<attribute>` directly, never call
    # raise_if_error!, and declare their field `null: false` - so a failure
    # makes them return nil and raise GraphQL::InvalidNullError, which is still
    # a 500, only with a different message. Raising does not work either: there
    # is no rescue_from at the schema or resolver level, and GraphqlController
    # re-raises outside development.
    #
    # Behaviour is unchanged whenever LAGO_DATA_API_URL is present.
    DATA_API_URL_ENV = "LAGO_DATA_API_URL"

    # Types::DataApi::Metadata declares current_page, next_page, prev_page,
    # total_count and total_pages as `null: false` Integer, so every key has to
    # be a real integer. next_page and prev_page are 0 because "no page" cannot
    # be expressed as nil here.
    EMPTY_METADATA = {
      "current_page" => 1,
      "next_page" => 0,
      "prev_page" => 0,
      "total_count" => 0,
      "total_pages" => 0
    }.freeze

    # Stands in for LagoHttpClient::Client and answers any verb with the empty
    # payload, so no service or resolver needs to know the Data API is absent.
    class UnconfiguredClient
      def initialize(payload)
        @payload = payload
      end

      def get(**_kwargs)
        @payload
      end

      def post(*_args, **_kwargs)
        @payload
      end
    end

    def initialize(organization, **params)
      @organization = organization
      @params = params

      super()
    end

    private

    attr_reader :organization, :params

    def http_client
      unless data_api_configured?
        Rails.logger.warn(
          "#{DATA_API_URL_ENV} is not set: returning an empty Data API payload for #{self.class.name}"
        )
        return UnconfiguredClient.new(unconfigured_payload)
      end

      @http_client ||= LagoHttpClient::Client.new(endpoint_url, retry_on_transient_errors: true)
    end

    def data_api_configured?
      ENV[DATA_API_URL_ENV].present?
    end

    # Default shape: the seven resolvers that return `result.<attribute>`
    # straight into a graphql-pagination collection_type, where BOTH the
    # `collection` and the `metadata` field resolve from that same object. A
    # bare [] would satisfy `collection` but blow up on `metadata`, which reads
    # current_page, limit_value, total_count and total_pages - none of which
    # Array responds to. A Kaminari paginatable array is an empty Array AND
    # answers all four with integers.
    #
    # Overridden by the three services whose resolver indexes the payload by key.
    def unconfigured_payload
      Kaminari.paginate_array([]).page(1)
    end

    def headers
      {
        "Authorization" => "Bearer #{ENV["LAGO_DATA_API_BEARER_TOKEN"]}"
      }
    end

    def endpoint_url
      "#{ENV[DATA_API_URL_ENV]}/#{action_path}"
    end

    def action_path
      raise NotImplementedError
    end
  end
end
