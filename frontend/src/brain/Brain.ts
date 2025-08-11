import {
  BatchOptimizationRequest,
  CheckHealthData,
  HealthCheckData,
  OptimizeBatchData,
  OptimizeBatchError,
  OptimizePriceData,
  OptimizePriceError,
  PriceOptimizationRequest,
} from "./data-contracts";
import { ContentType, HttpClient, RequestParams } from "./http-client";

export class Brain<SecurityDataType = unknown> extends HttpClient<SecurityDataType> {
  /**
   * @description Check health of application. Returns 200 when OK, 500 when not.
   *
   * @name check_health
   * @summary Check Health
   * @request GET:/_healthz
   */
  check_health = (params: RequestParams = {}) =>
    this.request<CheckHealthData, any>({
      path: `/_healthz`,
      method: "GET",
      ...params,
    });

  /**
   * @description Optimize price for a single product using AI and competitive analysis
   *
   * @tags dbtn/module:price_optimization, dbtn/hasAuth
   * @name optimize_price
   * @summary Optimize Price
   * @request POST:/routes/optimize-price
   */
  optimize_price = (data: PriceOptimizationRequest, params: RequestParams = {}) =>
    this.request<OptimizePriceData, OptimizePriceError>({
      path: `/routes/optimize-price`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params,
    });

  /**
   * @description Optimize prices for multiple products in batch
   *
   * @tags dbtn/module:price_optimization, dbtn/hasAuth
   * @name optimize_batch
   * @summary Optimize Batch
   * @request POST:/routes/optimize-batch
   */
  optimize_batch = (data: BatchOptimizationRequest, params: RequestParams = {}) =>
    this.request<OptimizeBatchData, OptimizeBatchError>({
      path: `/routes/optimize-batch`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params,
    });

  /**
   * @description Health check endpoint
   *
   * @tags dbtn/module:price_optimization, dbtn/hasAuth
   * @name health_check
   * @summary Health Check
   * @request GET:/routes/health
   */
  health_check = (params: RequestParams = {}) =>
    this.request<HealthCheckData, any>({
      path: `/routes/health`,
      method: "GET",
      ...params,
    });
}
