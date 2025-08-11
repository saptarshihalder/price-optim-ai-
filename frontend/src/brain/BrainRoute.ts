import {
  BatchOptimizationRequest,
  CheckHealthData,
  HealthCheckData,
  OptimizeBatchData,
  OptimizePriceData,
  PriceOptimizationRequest,
} from "./data-contracts";

export namespace Brain {
  /**
   * @description Check health of application. Returns 200 when OK, 500 when not.
   * @name check_health
   * @summary Check Health
   * @request GET:/_healthz
   */
  export namespace check_health {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = CheckHealthData;
  }

  /**
   * @description Optimize price for a single product using AI and competitive analysis
   * @tags dbtn/module:price_optimization, dbtn/hasAuth
   * @name optimize_price
   * @summary Optimize Price
   * @request POST:/routes/optimize-price
   */
  export namespace optimize_price {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = PriceOptimizationRequest;
    export type RequestHeaders = {};
    export type ResponseBody = OptimizePriceData;
  }

  /**
   * @description Optimize prices for multiple products in batch
   * @tags dbtn/module:price_optimization, dbtn/hasAuth
   * @name optimize_batch
   * @summary Optimize Batch
   * @request POST:/routes/optimize-batch
   */
  export namespace optimize_batch {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = BatchOptimizationRequest;
    export type RequestHeaders = {};
    export type ResponseBody = OptimizeBatchData;
  }

  /**
   * @description Health check endpoint
   * @tags dbtn/module:price_optimization, dbtn/hasAuth
   * @name health_check
   * @summary Health Check
   * @request GET:/routes/health
   */
  export namespace health_check {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = HealthCheckData;
  }
}
