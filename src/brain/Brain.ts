@@ .. @@
import {
  BatchOptimizationRequest,
  CheckHealthData,
  HealthCheckData,
  OptimizeBatchData,
  OptimizeBatchError,
  OptimizePriceData,
  OptimizePriceError,
  PriceOptimizationRequest,
+  ScrapingRequest,
+  ScrapingResponse,
+  ScrapingProgress,
+  ScrapedProduct,
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

+  /**
+   * @description Start competitor price scraping
+   *
+   * @tags dbtn/module:competitor_scraping, dbtn/hasAuth
+   * @name start_scraping
+   * @summary Start Scraping
+   * @request POST:/routes/start-scraping
+   */
+  start_scraping = (data: ScrapingRequest, params: RequestParams = {}) =>
+    this.request<ScrapingResponse, any>({
+      path: `/routes/start-scraping`,
+      method: "POST",
+      body: data,
+      type: ContentType.Json,
+      ...params,
+    });
+
+  /**
+   * @description Get scraping progress for a task
+   *
+   * @tags dbtn/module:competitor_scraping, dbtn/hasAuth
+   * @name get_scraping_progress
+   * @summary Get Scraping Progress
+   * @request GET:/routes/scraping-progress/{task_id}
+   */
+  get_scraping_progress = (taskId: string, params: RequestParams = {}) =>
+    this.request<ScrapingProgress, any>({
+      path: `/routes/scraping-progress/${taskId}`,
+      method: "GET",
+      ...params,
+    });
+
+  /**
+   * @description Get scraping results for a completed task
+   *
+   * @tags dbtn/module:competitor_scraping, dbtn/hasAuth
+   * @name get_scraping_results
+   * @summary Get Scraping Results
+   * @request GET:/routes/scraping-results/{task_id}
+   */
+  get_scraping_results = (taskId: string, params: RequestParams = {}) =>
+    this.request<ScrapedProduct[], any>({
+      path: `/routes/scraping-results/${taskId}`,
+      method: "GET",
+      ...params,
+    });
}