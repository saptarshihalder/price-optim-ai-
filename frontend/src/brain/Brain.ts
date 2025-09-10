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

  /**
   * @description Start competitor scraping task
   * @request POST:/routes/start-scraping
   */
  start_scraping = (data: { target_products: string[]; max_products_per_store?: number }, params: RequestParams = {}) =>
    this.request<{ task_id: string; status: string; message: string }, any>({
      path: `/routes/start-scraping`,
      method: "POST",
      body: data,
      type: ContentType.Json,
      ...params,
    });

  /**
   * @description Get scraping progress for a task
   * @request GET:/routes/scraping-progress/{task_id}
   */
  get_scraping_progress = (data: { taskId: string }, params: RequestParams = {}) =>
    this.request<
      { status: string; current_store?: string | null; completed_stores: number; total_stores: number; products_found: number; errors: string[]; started_at?: string | null; completed_at?: string | null },
      any
    >({
      path: `/routes/scraping-progress/${encodeURIComponent(data.taskId)}`,
      method: "GET",
      ...params,
    });

  /**
   * @description Get scraping results for a task
   * @request GET:/routes/scraping-results/{task_id}
   */
  get_scraping_results = (data: { taskId: string }, params: RequestParams = {}) =>
    this.request<Array<{
      store_name: string;
      title: string;
      price?: number | null;
      currency: string;
      brand?: string | null;
      product_url: string;
      in_stock: boolean;
      scraped_at: string;
      match_score?: number | null;
      match_confidence?: string | null;
      match_reasoning?: string | null;
    }>, any>({
      path: `/routes/scraping-results/${encodeURIComponent(data.taskId)}`,
      method: "GET",
      ...params,
    });

  /**
   * @description Load canonical target products from the catalog CSV
   * @request GET:/routes/load-target-products
   */
  load_target_products = (params: RequestParams = {}) =>
    this.request<{ targets: string[]; count: number }, any>({
      path: `/routes/load-target-products`,
      method: "GET",
      ...params,
    });
}
