/** BatchOptimizationRequest */
export interface BatchOptimizationRequest {
  /** Products */
  products: ProductInput[];
  /**
   * Competitor Data
   * @default {}
   */
  competitor_data?: Record<string, CompetitorData[]>;
  /** @default {"min_margin_percent":20,"max_price_increase_percent":50,"psychological_pricing":true,"competitive_positioning":"competitive","demand_sensitivity":1} */
  global_constraints?: OptimizationConstraints;
}

/** BatchOptimizationResponse */
export interface BatchOptimizationResponse {
  /** Recommendations */
  recommendations: PriceRecommendation[];
  /** Summary */
  summary: Record<string, any>;
  /** Optimization Timestamp */
  optimization_timestamp: string;
}

/** CompetitorData */
export interface CompetitorData {
  /** Store Name */
  store_name: string;
  /** Price */
  price: number;
  /** Currency */
  currency: string;
  /** In Stock */
  in_stock: boolean;
  /** Match Confidence */
  match_confidence: number;
  /** Product Url */
  product_url: string;
}

/** HTTPValidationError */
export interface HTTPValidationError {
  /** Detail */
  detail?: ValidationError[];
}

/** HealthResponse */
export interface HealthResponse {
  /** Status */
  status: string;
}

/** OptimizationConstraints */
export interface OptimizationConstraints {
  /**
   * Min Margin Percent
   * Minimum profit margin %
   * @default 20
   */
  min_margin_percent?: number;
  /**
   * Max Price Increase Percent
   * Maximum price increase %
   * @default 50
   */
  max_price_increase_percent?: number;
  /**
   * Psychological Pricing
   * Use psychological pricing (.95, .99)
   * @default true
   */
  psychological_pricing?: boolean;
  /**
   * Competitive Positioning
   * aggressive, competitive, or premium
   * @default "competitive"
   */
  competitive_positioning?: string;
  /**
   * Demand Sensitivity
   * Price elasticity multiplier
   * @default 1
   */
  demand_sensitivity?: number;
}

/** PriceOptimizationRequest */
export interface PriceOptimizationRequest {
  product: ProductInput;
  /**
   * Competitors
   * @default []
   */
  competitors?: CompetitorData[];
  /** @default {"min_margin_percent":20,"max_price_increase_percent":50,"psychological_pricing":true,"competitive_positioning":"competitive","demand_sensitivity":1} */
  constraints?: OptimizationConstraints;
}

/** PriceRecommendation */
export interface PriceRecommendation {
  /** Product Id */
  product_id: string;
  /** Current Price */
  current_price: number;
  /** Recommended Price */
  recommended_price: number;
  /** Currency */
  currency: string;
  /** Price Change */
  price_change: number;
  /** Price Change Percent */
  price_change_percent: number;
  /** Expected Demand Change Percent */
  expected_demand_change_percent: number;
  /** Expected Profit Change */
  expected_profit_change: number;
  /** Expected Revenue Change */
  expected_revenue_change: number;
  /** Confidence Score */
  confidence_score: number;
  /** Risk Level */
  risk_level: string;
  /** Rationale */
  rationale: string;
  /** Competitive Position */
  competitive_position: string;
  /** Psychological Price Applied */
  psychological_price_applied: boolean;
  /** Constraint Flags */
  constraint_flags: string[];
  /** Scenario Analysis */
  scenario_analysis: Record<string, any>;
}

/** ProductInput */
export interface ProductInput {
  /** Id */
  id: string;
  /** Name */
  name: string;
  /** Current Price */
  current_price: number;
  /** Unit Cost */
  unit_cost: number;
  /**
   * Currency
   * @default "EUR"
   */
  currency?: string;
  /** Category */
  category?: string | null;
  /** Brand */
  brand?: string | null;
}

/** ValidationError */
export interface ValidationError {
  /** Location */
  loc: (string | number)[];
  /** Message */
  msg: string;
  /** Error Type */
  type: string;
}

/** ScrapedProduct */
export interface ScrapedProduct {
  /** Store Name */
  store_name: string;
  /** Product Id */
  product_id?: string | null;
  /** Title */
  title: string;
  /** Price */
  price?: number | null;
  /**
   * Currency
   * @default "USD"
   */
  currency?: string;
  /** Brand */
  brand?: string | null;
  /** Description */
  description?: string | null;
  /** Image Url */
  image_url?: string | null;
  /** Product Url */
  product_url: string;
  /**
   * In Stock
   * @default true
   */
  in_stock?: boolean;
  /**
   * Scraped At
   * @format date-time
   */
  scraped_at: string;
  /** Match Score */
  match_score?: number | null;
  /** Match Confidence */
  match_confidence?: string | null;
  /** Match Reasoning */
  match_reasoning?: string | null;
  /**
   * Raw Data
   * @default {}
   */
  raw_data?: Record<string, any>;
}

/** ScrapingProgress */
export interface ScrapingProgress {
  status: ScrapingStatus;
  /** Current Store */
  current_store?: string | null;
  /**
   * Completed Stores
   * @default 0
   */
  completed_stores?: number;
  /**
   * Total Stores
   * @default 0
   */
  total_stores?: number;
  /**
   * Products Found
   * @default 0
   */
  products_found?: number;
  /**
   * Errors
   * @default []
   */
  errors?: string[];
  /** Started At */
  started_at?: string | null;
  /** Completed At */
  completed_at?: string | null;
}

/** ScrapingRequest */
export interface ScrapingRequest {
  /** Target Products */
  target_products: string[];
  /**
   * Max Products Per Store
   * @default 15
   */
  max_products_per_store?: number;
}

/** ScrapingResponse */
export interface ScrapingResponse {
  /** Task Id */
  task_id: string;
  status: ScrapingStatus;
  /** Message */
  message: string;
}

/** ScrapingStatus */
export enum ScrapingStatus {
  Pending = "pending",
  Running = "running",
  Completed = "completed",
  Failed = "failed",
}

export type CheckHealthData = HealthResponse;

export type OptimizePriceData = PriceRecommendation;

export type OptimizePriceError = HTTPValidationError;

export type OptimizeBatchData = BatchOptimizationResponse;

export type OptimizeBatchError = HTTPValidationError;

export type HealthCheckData = any;
