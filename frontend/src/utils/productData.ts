export interface Product {
  id: string;
  name: string;
  currentPrice: number;
  unitCost: number;
  currency: string;
  margin: number;
  marginPercent: number;
  suggestedPrice?: number;
  priceChange?: number;
  priceChangePercent?: number;
  profitUplift?: number;
}

// Product data from the CSV
export const rawProductData: Omit<Product, 'margin' | 'marginPercent' | 'suggestedPrice' | 'priceChange' | 'priceChangePercent' | 'profitUplift'>[] = [
  {
    id: "SG0001",
    name: "Reiek Peak Wooden Sunglasses (Incl. cork casing)",
    currentPrice: 57.95,
    unitCost: 14.23,
    currency: "EUR"
  },
  {
    id: "SG0002",
    name: "Fibonacci Wooden Sunglasses (Incl. cork casing)",
    currentPrice: 61.50,
    unitCost: 14.23,
    currency: "EUR"
  },
  {
    id: "BT0005",
    name: "Elephant Falls Thermos Bottle",
    currentPrice: 31.95,
    unitCost: 8.34,
    currency: "EUR"
  },
  {
    id: "BT0012-13",
    name: "Saint Elias Thermos bottles",
    currentPrice: 32.95,
    unitCost: 9.31,
    currency: "EUR"
  },
  {
    id: "BT0015-16",
    name: "Inca Trail Coffee Mugs",
    currentPrice: 31.95,
    unitCost: 8.55,
    currency: "EUR"
  },
  {
    id: "PS0007",
    name: "Woodland Mouse Phone Stand",
    currentPrice: 18.95,
    unitCost: 3.01,
    currency: "EUR"
  },
  {
    id: "NB0011-12",
    name: "Tiger Trail Notebooks",
    currentPrice: 25.95,
    unitCost: 6.79,
    currency: "EUR"
  },
  {
    id: "NB0013-15",
    name: "Papillon Notebooks",
    currentPrice: 23.95,
    unitCost: 5.21,
    currency: "EUR"
  },
  {
    id: "LB0017",
    name: "Jim Corbett Lunchbox Band 1200ML",
    currentPrice: 32.95,
    unitCost: 19.45,
    currency: "EUR"
  },
  {
    id: "LB0019",
    name: "Jim Corbett Lunchbox Band 800ML",
    currentPrice: 30.95,
    unitCost: 7.59,
    currency: "EUR"
  },
  {
    id: "SH0017-26",
    name: "Timeless Silk Colored Stole",
    currentPrice: 73.95,
    unitCost: 39.48,
    currency: "EUR"
  },
  {
    id: "SH0025",
    name: "Silk Uncut White Stole",
    currentPrice: 114.95,
    unitCost: 33.92,
    currency: "EUR"
  }
];

// Calculate margins and add suggested pricing
export const processProductData = (): Product[] => {
  return rawProductData.map(product => {
    const margin = product.currentPrice - product.unitCost;
    const marginPercent = (margin / product.currentPrice) * 100;
    
    // Simple pricing optimization (10-15% increase based on margin)
    const optimizationFactor = marginPercent < 50 ? 1.15 : 1.10;
    const suggestedPrice = Math.round(product.currentPrice * optimizationFactor * 100) / 100;
    const priceChange = suggestedPrice - product.currentPrice;
    const priceChangePercent = (priceChange / product.currentPrice) * 100;
    const profitUplift = priceChange; // Simplified - actual would be (suggestedPrice - unitCost) - (currentPrice - unitCost)
    
    return {
      ...product,
      margin,
      marginPercent,
      suggestedPrice,
      priceChange,
      priceChangePercent,
      profitUplift
    };
  });
};

// Calculate dashboard metrics
export const calculateMetrics = (products: Product[]) => {
  const totalProducts = products.length;
  const avgMargin = products.reduce((sum, p) => sum + p.marginPercent, 0) / totalProducts;
  const totalCurrentRevenue = products.reduce((sum, p) => sum + p.currentPrice, 0);
  const totalSuggestedRevenue = products.reduce((sum, p) => sum + (p.suggestedPrice || 0), 0);
  const totalProfitUplift = products.reduce((sum, p) => sum + (p.profitUplift || 0), 0);
  const avgPriceIncrease = products.reduce((sum, p) => sum + (p.priceChangePercent || 0), 0) / totalProducts;
  
  return {
    totalProducts,
    avgMargin,
    totalCurrentRevenue,
    totalSuggestedRevenue,
    totalProfitUplift,
    avgPriceIncrease
  };
};
