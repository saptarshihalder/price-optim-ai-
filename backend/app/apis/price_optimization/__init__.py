
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import math
import json
from datetime import datetime
import os
from openai import OpenAI

# Databutton is optional in local/dev; avoid hard dependency on project id
try:  # pragma: no cover - optional dependency in local dev
    import databutton as db  # type: ignore
except Exception:  # Module may be missing or misconfigured
    db = None  # type: ignore

router = APIRouter()

# Resolve OpenAI API key from environment first, then Databutton secrets if available
def _resolve_openai_api_key() -> str | None:
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key
    if db is not None:
        try:
            return db.secrets.get("OPENAI_API_KEY")  # type: ignore[attr-defined]
        except Exception:
            return None
    return None

_OPENAI_API_KEY = _resolve_openai_api_key()

# Create client only if we have a key; downstream calls will gracefully fallback on failure
client = OpenAI(api_key=_OPENAI_API_KEY) if _OPENAI_API_KEY else None  # type: ignore[assignment]

# Pydantic Models
class ProductInput(BaseModel):
    id: str
    name: str
    current_price: float
    unit_cost: float
    currency: str = "EUR"
    category: Optional[str] = None
    brand: Optional[str] = None
    
class CompetitorData(BaseModel):
    store_name: str
    price: float
    currency: str
    in_stock: bool
    match_confidence: float
    product_url: str
    
class OptimizationConstraints(BaseModel):
    min_margin_percent: float = Field(default=20.0, description="Minimum profit margin %")
    max_price_increase_percent: float = Field(default=50.0, description="Maximum price increase %")
    psychological_pricing: bool = Field(default=True, description="Use psychological pricing (.95, .99)")
    competitive_positioning: str = Field(default="competitive", description="aggressive, competitive, or premium")
    demand_sensitivity: float = Field(default=1.0, description="Price elasticity multiplier")
    
class PriceOptimizationRequest(BaseModel):
    product: ProductInput
    competitors: List[CompetitorData] = []
    constraints: OptimizationConstraints = OptimizationConstraints()
    
class PriceRecommendation(BaseModel):
    product_id: str
    current_price: float
    recommended_price: float
    currency: str
    price_change: float
    price_change_percent: float
    expected_demand_change_percent: float
    expected_profit_change: float
    expected_revenue_change: float
    confidence_score: float  # 0-1
    risk_level: str  # low, medium, high
    rationale: str
    competitive_position: str
    psychological_price_applied: bool
    constraint_flags: List[str]
    scenario_analysis: Dict[str, Any]
    
class BatchOptimizationRequest(BaseModel):
    products: List[ProductInput]
    competitor_data: Dict[str, List[CompetitorData]] = {}  # product_id -> competitors
    global_constraints: OptimizationConstraints = OptimizationConstraints()
    
class BatchOptimizationResponse(BaseModel):
    recommendations: List[PriceRecommendation]
    summary: Dict[str, Any]
    optimization_timestamp: str
    
# Category-specific demand elasticity priors
CATEGORY_ELASTICITY = {
    "sunglasses": -1.2,  # Somewhat elastic - fashion/luxury item
    "bottle": -0.8,     # Moderately inelastic - utility item
    "mug": -0.9,        # Moderately inelastic
    "stand": -1.1,      # Elastic - accessory item
    "notebook": -1.0,   # Unit elastic - office supply
    "lunchbox": -0.7,   # Inelastic - necessity item
    "stole": -1.4,      # Highly elastic - luxury fashion
    "default": -1.0     # Unit elastic default
}

# Psychological pricing rules
def apply_psychological_pricing(price: float) -> float:
    """Apply psychological pricing rules (.95, .99 endings)"""
    if price < 10:
        return math.floor(price) + 0.95
    elif price < 50:
        return math.floor(price) + 0.99
    else:
        return math.floor(price) + 0.95

def calculate_demand_elasticity(product: ProductInput, competitors: List[CompetitorData]) -> float:
    """Calculate demand elasticity using category priors and competitive analysis"""
    base_elasticity = CATEGORY_ELASTICITY.get(product.category or "default", -1.0)
    
    # Adjust based on competitive intensity
    if len(competitors) > 5:
        # High competition = more elastic demand
        base_elasticity *= 1.2
    elif len(competitors) < 2:
        # Low competition = less elastic demand  
        base_elasticity *= 0.8
        
    # Adjust based on price level (luxury vs budget)
    if product.current_price > 100:
        # Higher price = more elastic
        base_elasticity *= 1.1
    elif product.current_price < 20:
        # Lower price = less elastic
        base_elasticity *= 0.9
        
    return base_elasticity

async def get_llm_demand_analysis(product: ProductInput, competitors: List[CompetitorData], 
                                market_position: str) -> Dict[str, Any]:
    """Use LLM to analyze demand characteristics and provide insights"""
    competitor_summary = "\n".join([
        f"- {c.store_name}: {c.currency} {c.price:.2f} ({'in stock' if c.in_stock else 'out of stock'})"
        for c in competitors[:5]  # Limit to top 5 for context
    ])
    
    prompt = f"""As a pricing strategist, analyze the demand characteristics for this product:

Product: {product.name}
Category: {product.category or 'Unknown'}
Current Price: {product.currency} {product.current_price:.2f}
Unit Cost: {product.currency} {product.unit_cost:.2f}
Current Margin: {((product.current_price - product.unit_cost) / product.current_price * 100):.1f}%

Competitor Prices:
{competitor_summary or 'No competitor data available'}

Market Position: {market_position}

Provide a JSON response with:
1. demand_elasticity_estimate (float between -0.5 to -2.0)
2. brand_strength_score (float 0-1, where 1 is premium brand)
3. market_saturation_level (string: low/medium/high)
4. price_sensitivity_factors (list of key factors affecting price sensitivity)
5. seasonal_considerations (string describing any seasonal factors)
6. recommended_positioning (string: budget/value/premium)

Return only valid JSON without markdown formatting."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert pricing strategist. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        analysis = json.loads(response.choices[0].message.content)
        return analysis
        
    except Exception as e:
        print(f"LLM analysis failed: {e}")
        # Fallback to basic analysis
        return {
            "demand_elasticity_estimate": -1.0,
            "brand_strength_score": 0.5,
            "market_saturation_level": "medium",
            "price_sensitivity_factors": ["competitor pricing", "product quality"],
            "seasonal_considerations": "No specific seasonal factors identified",
            "recommended_positioning": "value"
        }

def calculate_expected_demand_change(price_change_percent: float, elasticity: float) -> float:
    """Calculate expected demand change using price elasticity"""
    # Demand change = elasticity × price change
    return elasticity * price_change_percent

def assess_competitive_position(current_price: float, competitors: List[CompetitorData]) -> str:
    """Assess competitive position relative to market"""
    if not competitors:
        return "no_competition"
        
    competitor_prices = [c.price for c in competitors if c.price > 0]
    if not competitor_prices:
        return "no_pricing_data"
        
    min_price = min(competitor_prices)
    max_price = max(competitor_prices)
    median_price = sorted(competitor_prices)[len(competitor_prices) // 2]
    
    if current_price < min_price * 0.9:
        return "significantly_underpriced"
    elif current_price < median_price * 0.95:
        return "underpriced"
    elif current_price <= max_price * 1.05:
        return "competitive"
    elif current_price <= max_price * 1.2:
        return "premium"
    else:
        return "overpriced"

async def generate_pricing_rationale(product: ProductInput, recommended_price: float, 
                                   analysis: Dict[str, Any], competitive_position: str,
                                   constraints: OptimizationConstraints) -> str:
    """Generate LLM-based rationale for price recommendation"""
    
    price_change = recommended_price - product.current_price
    price_change_pct = (price_change / product.current_price) * 100
    
    prompt = f"""As a pricing expert, provide a clear, concise rationale for this price recommendation:

Product: {product.name}
Current Price: {product.currency} {product.current_price:.2f}
Recommended Price: {product.currency} {recommended_price:.2f}
Price Change: {price_change:+.2f} ({price_change_pct:+.1f}%)

Market Analysis:
- Competitive Position: {competitive_position}
- Brand Strength: {analysis.get('brand_strength_score', 0.5):.1f}/1.0
- Market Saturation: {analysis.get('market_saturation_level', 'medium')}
- Positioning: {analysis.get('recommended_positioning', 'value')}

Constraints Applied:
- Min Margin: {constraints.min_margin_percent}%
- Max Increase: {constraints.max_price_increase_percent}%
- Psychological Pricing: {constraints.psychological_pricing}
- Strategy: {constraints.competitive_positioning}

Provide a 2-3 sentence rationale explaining:
1. Why this price is optimal
2. Key market factors considered
3. Expected business impact

Be specific about profit/demand implications and sound confident but data-driven."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a pricing expert providing clear, actionable rationale. Be concise and confident."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Rationale generation failed: {e}")
        return f"Recommended price increase of {price_change_pct:.1f}% based on competitive analysis and profit optimization. This adjustment balances market positioning with margin improvement while considering demand elasticity."

def optimize_single_product_price(product: ProductInput, competitors: List[CompetitorData],
                                constraints: OptimizationConstraints, 
                                llm_analysis: Dict[str, Any]) -> tuple[float, List[str]]:
    """Core price optimization algorithm"""
    
    constraint_flags = []
    
    # Get market data
    competitor_prices = [c.price for c in competitors if c.price > 0]
    
    # Calculate elasticity
    base_elasticity = llm_analysis.get('demand_elasticity_estimate', -1.0)
    elasticity = base_elasticity * constraints.demand_sensitivity
    
    # Market bounds
    if competitor_prices:
        market_min = min(competitor_prices) * 0.8  # Can be 20% below market min
        market_max = max(competitor_prices) * 1.3  # Can be 30% above market max
    else:
        market_min = product.current_price * 0.5
        market_max = product.current_price * 2.0
    
    # Price optimization based on strategy
    if constraints.competitive_positioning == "aggressive":
        target_percentile = 0.3  # Target 30th percentile (lower prices)
    elif constraints.competitive_positioning == "premium":
        target_percentile = 0.8  # Target 80th percentile (higher prices)
    else:  # competitive
        target_percentile = 0.6  # Target 60th percentile (slightly above median)
    
    if competitor_prices:
        target_price = sorted(competitor_prices)[int(len(competitor_prices) * target_percentile)]
    else:
        target_price = product.current_price * 1.1  # 10% increase if no competition
    
    # Apply constraints
    min_price_margin = product.unit_cost / (1 - constraints.min_margin_percent / 100)
    max_price_increase = product.current_price * (1 + constraints.max_price_increase_percent / 100)
    
    # Start with target price and apply constraints
    optimized_price = target_price
    
    # Constraint 1: Minimum margin
    if optimized_price < min_price_margin:
        optimized_price = min_price_margin
        constraint_flags.append("min_margin_applied")
    
    # Constraint 2: Maximum price increase
    if optimized_price > max_price_increase:
        optimized_price = max_price_increase
        constraint_flags.append("max_increase_applied")
    
    # Constraint 3: Market bounds (sanity check)
    if optimized_price < market_min:
        optimized_price = market_min
        constraint_flags.append("market_floor_applied")
    elif optimized_price > market_max:
        optimized_price = market_max
        constraint_flags.append("market_ceiling_applied")
    
    # Constraint 4: Psychological pricing
    if constraints.psychological_pricing:
        psychological_price = apply_psychological_pricing(optimized_price)
        # Only apply if it doesn't violate other constraints significantly
        if abs(psychological_price - optimized_price) / optimized_price < 0.05:  # Within 5%
            optimized_price = psychological_price
            constraint_flags.append("psychological_pricing_applied")
    
    return optimized_price, constraint_flags

def calculate_scenario_analysis(product: ProductInput, recommended_price: float,
                              elasticity: float, competitors: List[CompetitorData]) -> Dict[str, Any]:
    """Calculate different pricing scenarios"""
    current_price = product.current_price
    base_margin = current_price - product.unit_cost
    
    scenarios = {}
    
    # Test different price points
    for scenario_name, price_multiplier in [
        ("conservative", 0.95),  # 5% below recommended
        ("recommended", 1.0),    # Recommended price
        ("aggressive", 1.05)     # 5% above recommended
    ]:
        scenario_price = recommended_price * price_multiplier
        price_change_pct = ((scenario_price - current_price) / current_price) * 100
        
        # Calculate demand impact
        demand_change_pct = calculate_expected_demand_change(price_change_pct, elasticity)
        
        # Calculate financial impact
        new_margin = scenario_price - product.unit_cost
        margin_change = new_margin - base_margin
        
        # Assume base demand of 100 units for relative comparison
        base_units = 100
        new_units = base_units * (1 + demand_change_pct / 100)
        
        revenue_change = (scenario_price * new_units) - (current_price * base_units)
        profit_change = (new_margin * new_units) - (base_margin * base_units)
        
        scenarios[scenario_name] = {
            "price": round(scenario_price, 2),
            "price_change_percent": round(price_change_pct, 1),
            "demand_change_percent": round(demand_change_pct, 1),
            "expected_units": round(new_units, 0),
            "revenue_change": round(revenue_change, 2),
            "profit_change": round(profit_change, 2),
            "margin_percent": round((new_margin / scenario_price) * 100, 1)
        }
    
    return scenarios

def calculate_confidence_score(product: ProductInput, competitors: List[CompetitorData],
                             llm_analysis: Dict[str, Any], constraint_flags: List[str]) -> tuple[float, str]:
    """Calculate confidence score and risk level"""
    confidence = 1.0
    
    # Reduce confidence based on data quality
    if len(competitors) < 3:
        confidence *= 0.8  # Limited competitive data
    
    if not product.category:
        confidence *= 0.9  # No category for elasticity estimation
    
    # Brand strength affects confidence
    brand_strength = llm_analysis.get('brand_strength_score', 0.5)
    if brand_strength < 0.3:
        confidence *= 0.9  # Weak brand = higher uncertainty
    
    # Market saturation affects confidence
    saturation = llm_analysis.get('market_saturation_level', 'medium')
    if saturation == 'high':
        confidence *= 0.85  # High saturation = more competitive pressure
    
    # Constraint violations reduce confidence
    if len(constraint_flags) > 2:
        confidence *= 0.9  # Multiple constraints = limited optimization space
    
    # Ensure confidence is between 0 and 1
    confidence = max(0.1, min(1.0, confidence))
    
    # Determine risk level
    if confidence > 0.8:
        risk_level = "low"
    elif confidence > 0.6:
        risk_level = "medium"
    else:
        risk_level = "high"
    
    return confidence, risk_level

@router.post("/optimize-price")
async def optimize_price(request: PriceOptimizationRequest) -> PriceRecommendation:
    """Optimize price for a single product using AI and competitive analysis"""
    
    try:
        product = request.product
        competitors = request.competitors
        constraints = request.constraints
        
        # Step 1: LLM-based demand analysis
        competitive_position = assess_competitive_position(product.current_price, competitors)
        llm_analysis = await get_llm_demand_analysis(product, competitors, competitive_position)
        
        # Step 2: Core price optimization
        recommended_price, constraint_flags = optimize_single_product_price(
            product, competitors, constraints, llm_analysis
        )
        
        # Step 3: Calculate metrics
        price_change = recommended_price - product.current_price
        price_change_percent = (price_change / product.current_price) * 100
        
        elasticity = llm_analysis.get('demand_elasticity_estimate', -1.0) * constraints.demand_sensitivity
        expected_demand_change_percent = calculate_expected_demand_change(price_change_percent, elasticity)
        
        # Financial impact calculations
        current_margin = product.current_price - product.unit_cost
        new_margin = recommended_price - product.unit_cost
        margin_change = new_margin - current_margin
        
        # Assume base demand for relative calculations
        base_demand = 100
        new_demand = base_demand * (1 + expected_demand_change_percent / 100)
        
        expected_profit_change = (new_margin * new_demand) - (current_margin * base_demand)
        expected_revenue_change = (recommended_price * new_demand) - (product.current_price * base_demand)
        
        # Step 4: Confidence and risk assessment
        confidence_score, risk_level = calculate_confidence_score(
            product, competitors, llm_analysis, constraint_flags
        )
        
        # Step 5: Scenario analysis
        scenario_analysis = calculate_scenario_analysis(
            product, recommended_price, elasticity, competitors
        )
        
        # Step 6: Generate rationale
        rationale = await generate_pricing_rationale(
            product, recommended_price, llm_analysis, competitive_position, constraints
        )
        
        return PriceRecommendation(
            product_id=product.id,
            current_price=product.current_price,
            recommended_price=round(recommended_price, 2),
            currency=product.currency,
            price_change=round(price_change, 2),
            price_change_percent=round(price_change_percent, 1),
            expected_demand_change_percent=round(expected_demand_change_percent, 1),
            expected_profit_change=round(expected_profit_change, 2),
            expected_revenue_change=round(expected_revenue_change, 2),
            confidence_score=round(confidence_score, 2),
            risk_level=risk_level,
            rationale=rationale,
            competitive_position=competitive_position,
            psychological_price_applied="psychological_pricing_applied" in constraint_flags,
            constraint_flags=constraint_flags,
            scenario_analysis=scenario_analysis
        )
        
    except Exception as e:
        print(f"Price optimization error: {e}")
        raise HTTPException(status_code=500, detail=f"Price optimization failed: {str(e)}") from e

@router.post("/optimize-batch")
async def optimize_batch(request: BatchOptimizationRequest) -> BatchOptimizationResponse:
    """Optimize prices for multiple products in batch"""
    
    try:
        recommendations = []
        
        # Process each product
        for product in request.products:
            competitors = request.competitor_data.get(product.id, [])
            
            optimization_request = PriceOptimizationRequest(
                product=product,
                competitors=competitors,
                constraints=request.global_constraints
            )
            
            recommendation = await optimize_price(optimization_request)
            recommendations.append(recommendation)
        
        # Calculate summary statistics
        total_current_revenue = sum(r.current_price for r in recommendations)
        total_recommended_revenue = sum(r.recommended_price for r in recommendations)
        total_profit_change = sum(r.expected_profit_change for r in recommendations)
        
        avg_price_increase = sum(r.price_change_percent for r in recommendations) / len(recommendations)
        high_confidence_count = sum(1 for r in recommendations if r.confidence_score > 0.8)
        
        summary = {
            "total_products": len(recommendations),
            "avg_price_increase_percent": round(avg_price_increase, 1),
            "total_current_revenue": round(total_current_revenue, 2),
            "total_recommended_revenue": round(total_recommended_revenue, 2),
            "total_revenue_uplift": round(total_recommended_revenue - total_current_revenue, 2),
            "total_profit_change": round(total_profit_change, 2),
            "high_confidence_recommendations": high_confidence_count,
            "confidence_rate": round(high_confidence_count / len(recommendations) * 100, 1)
        }
        
        return BatchOptimizationResponse(
            recommendations=recommendations,
            summary=summary,
            optimization_timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        print(f"Batch optimization error: {e}")
        raise HTTPException(status_code=500, detail=f"Batch optimization failed: {str(e)}") from e

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "price_optimization"}
