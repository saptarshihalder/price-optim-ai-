@@ .. @@
import {
  BatchOptimizationRequest,
  CheckHealthData,
  HealthCheckData,
  OptimizeBatchData,
  OptimizePriceData,
  PriceOptimizationRequest,
+  ScrapingRequest,
+  ScrapingResponse,
+  ScrapingProgress,
+  ScrapedProduct,
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

+  /**
+   * @description Start competitor price scraping
+   * @tags dbtn/module:competitor_scraping, dbtn/hasAuth
+   * @name start_scraping
+   * @summary Start Scraping
+   * @request POST:/routes/start-scraping
+   */
+  export namespace start_scraping {
+    export type RequestParams = {};
+    export type RequestQuery = {};
+    export type RequestBody = ScrapingRequest;
+    export type RequestHeaders = {};
+    export type ResponseBody = ScrapingResponse;
+  }
+
+  /**
+   * @description Get scraping progress for a task
+   * @tags dbtn/module:competitor_scraping, dbtn/hasAuth
+   * @name get_scraping_progress
+   * @summary Get Scraping Progress
+   * @request GET:/routes/scraping-progress/{task_id}
+   */
+  export namespace get_scraping_progress {
+    export type RequestParams = { taskId: string };
+    export type RequestQuery = {};
+    export type RequestBody = never;
+    export type RequestHeaders = {};
+    export type ResponseBody = ScrapingProgress;
+  }
+
+  /**
+   * @description Get scraping results for a completed task
+   * @tags dbtn/module:competitor_scraping, dbtn/hasAuth
+   * @name get_scraping_results
+   * @summary Get Scraping Results
+   * @request GET:/routes/scraping-results/{task_id}
+   */
+  export namespace get_scraping_results {
+    export type RequestParams = { taskId: string };
+    export type RequestQuery = {};
+    export type RequestBody = never;
+    export type RequestHeaders = {};
+    export type ResponseBody = ScrapedProduct[];
+  }
}