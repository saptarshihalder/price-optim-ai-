import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { processProductData, calculateMetrics } from "utils/productData";
import { TrendingUp, TrendingDown, DollarSign, Package, Target, Zap, Activity, ArrowRight, BarChart3 } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function App() {
  const navigate = useNavigate();
  const products = processProductData();
  const metrics = calculateMetrics(products);

  const formatCurrency = (amount: number) => `€${amount.toFixed(2)}`;
  const formatPercent = (percent: number) => `${percent.toFixed(1)}%`;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Cyberpunk Grid Background */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-20"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23334155' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`
        }}
      />
      
      <div className="relative z-10 container mx-auto px-6 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-6xl font-bold bg-gradient-to-r from-emerald-400 via-cyan-400 to-blue-400 bg-clip-text text-transparent mb-4 font-mono tracking-wider">
            PriceOptim AI
          </h1>
          <p className="text-xl text-slate-300 mb-2">AI-Powered Competitive Price Optimization Platform</p>
          <div className="flex items-center justify-center gap-2 text-emerald-400">
            <Zap className="w-5 h-5" />
            <span className="text-sm font-mono">REAL-TIME PRICING INTELLIGENCE</span>
            <Zap className="w-5 h-5" />
          </div>
        </div>

        {/* Action Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="bg-gradient-to-r from-green-600/20 to-green-500/10 border-green-500/30 backdrop-blur-sm hover:from-green-600/30 hover:to-green-500/20 transition-all cursor-pointer" 
                onClick={() => navigate('/scraping')}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-green-400 mb-2">Start Competitor Analysis</h3>
                  <p className="text-sm text-gray-300">Scrape competitor prices across multiple stores</p>
                </div>
                <Activity className="w-8 h-8 text-green-400" />
              </div>
              <Button className="w-full mt-4 bg-green-600 hover:bg-green-700 text-white" 
                      onClick={(e) => { e.stopPropagation(); navigate('/scraping'); }}>
                Launch Scraping <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-r from-blue-600/20 to-blue-500/10 border-blue-500/30 backdrop-blur-sm hover:from-blue-600/30 hover:to-blue-500/20 transition-all cursor-pointer" 
                onClick={() => navigate('/competitive-analysis')}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-blue-400 mb-2">View Market Analysis</h3>
                  <p className="text-sm text-gray-300">Compare prices across competitor stores</p>
                </div>
                <BarChart3 className="w-8 h-8 text-blue-400" />
              </div>
              <Button className="w-full mt-4 bg-blue-600 hover:bg-blue-700 text-white" 
                      onClick={(e) => { e.stopPropagation(); navigate('/competitive-analysis'); }}>
                View Analysis <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-r from-purple-600/20 to-purple-500/10 border-purple-500/30 backdrop-blur-sm hover:from-purple-600/30 hover:to-purple-500/20 transition-all cursor-pointer" 
                onClick={() => navigate('/pricing-recommendations')}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-purple-400 mb-2">AI Price Optimization</h3>
                  <p className="text-sm text-gray-300">Get intelligent pricing recommendations</p>
                </div>
                <Zap className="w-8 h-8 text-purple-400" />
              </div>
              <Button className="w-full mt-4 bg-purple-600 hover:bg-purple-700 text-white" 
                      onClick={(e) => { e.stopPropagation(); navigate('/pricing-recommendations'); }}>
                Optimize Prices <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Metrics Dashboard */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="bg-slate-800/50 border-emerald-500/30 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-300">Total Products</CardTitle>
              <Package className="h-4 w-4 text-emerald-400" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-emerald-400 font-mono">{metrics.totalProducts}</div>
              <p className="text-xs text-slate-400 mt-1">Active portfolio items</p>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-blue-500/30 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-300">Avg Margin</CardTitle>
              <Target className="h-4 w-4 text-blue-400" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-blue-400 font-mono">{formatPercent(metrics.avgMargin)}</div>
              <p className="text-xs text-slate-400 mt-1">Current profit margin</p>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-amber-500/30 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-300">Profit Uplift</CardTitle>
              <TrendingUp className="h-4 w-4 text-amber-400" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-amber-400 font-mono">{formatCurrency(metrics.totalProfitUplift)}</div>
              <p className="text-xs text-slate-400 mt-1">Potential increase</p>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-violet-500/30 backdrop-blur-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-slate-300">Avg Price Increase</CardTitle>
              <DollarSign className="h-4 w-4 text-violet-400" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-violet-400 font-mono">{formatPercent(metrics.avgPriceIncrease)}</div>
              <p className="text-xs text-slate-400 mt-1">Recommended adjustment</p>
            </CardContent>
          </Card>
        </div>

        {/* Product Portfolio Table */}
        <Card className="bg-slate-800/30 border-slate-700/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="text-2xl text-slate-100 flex items-center gap-2">
              <div className="w-3 h-3 bg-emerald-400 rounded-full animate-pulse" />
              Product Portfolio & Pricing Recommendations
            </CardTitle>
            <p className="text-slate-400">AI-generated pricing optimization based on competitive analysis</p>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border border-slate-700/50 overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-slate-900/50 border-slate-700/50">
                    <TableHead className="text-slate-300 font-mono">Product ID</TableHead>
                    <TableHead className="text-slate-300 font-mono">Product Name</TableHead>
                    <TableHead className="text-slate-300 font-mono text-right">Current Price</TableHead>
                    <TableHead className="text-slate-300 font-mono text-right">Unit Cost</TableHead>
                    <TableHead className="text-slate-300 font-mono text-right">Current Margin</TableHead>
                    <TableHead className="text-slate-300 font-mono text-right">Suggested Price</TableHead>
                    <TableHead className="text-slate-300 font-mono text-right">Price Change</TableHead>
                    <TableHead className="text-slate-300 font-mono text-right">Profit Uplift</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {products.map((product) => (
                    <TableRow key={product.id} className="border-slate-700/30 hover:bg-slate-800/30 transition-colors">
                      <TableCell className="font-mono text-emerald-400 font-medium">{product.id}</TableCell>
                      <TableCell className="text-slate-200 max-w-xs">
                        <div className="truncate" title={product.name}>{product.name}</div>
                      </TableCell>
                      <TableCell className="text-right font-mono text-slate-300">{formatCurrency(product.currentPrice)}</TableCell>
                      <TableCell className="text-right font-mono text-slate-400">{formatCurrency(product.unitCost)}</TableCell>
                      <TableCell className="text-right">
                        <Badge variant="outline" className="border-blue-500/30 text-blue-400 font-mono">
                          {formatPercent(product.marginPercent)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono text-emerald-400 font-semibold">
                        {formatCurrency(product.suggestedPrice || 0)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          {(product.priceChange || 0) > 0 ? (
                            <TrendingUp className="w-4 h-4 text-emerald-400" />
                          ) : (
                            <TrendingDown className="w-4 h-4 text-red-400" />
                          )}
                          <span className={`font-mono font-semibold ${
                            (product.priceChange || 0) > 0 ? 'text-emerald-400' : 'text-red-400'
                          }`}>
                            {product.priceChange && product.priceChange > 0 ? '+' : ''}{formatCurrency(product.priceChange || 0)}
                          </span>
                        </div>
                        <div className="text-xs text-slate-500 font-mono">
                          ({product.priceChangePercent && product.priceChangePercent > 0 ? '+' : ''}{formatPercent(product.priceChangePercent || 0)})
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <span className="font-mono font-semibold text-amber-400">
                          +{formatCurrency(product.profitUplift || 0)}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            
            {/* Summary Footer */}
            <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-slate-900/30 rounded-lg border border-slate-700/30">
              <div className="text-center">
                <div className="text-sm text-slate-400 mb-1">Total Current Revenue</div>
                <div className="text-xl font-mono font-bold text-blue-400">{formatCurrency(metrics.totalCurrentRevenue)}</div>
              </div>
              <div className="text-center">
                <div className="text-sm text-slate-400 mb-1">Optimized Revenue</div>
                <div className="text-xl font-mono font-bold text-emerald-400">{formatCurrency(metrics.totalSuggestedRevenue)}</div>
              </div>
              <div className="text-center">
                <div className="text-sm text-slate-400 mb-1">Revenue Uplift</div>
                <div className="text-xl font-mono font-bold text-amber-400">+{formatCurrency(metrics.totalSuggestedRevenue - metrics.totalCurrentRevenue)}</div>
              </div>
            </div>
          </CardContent>
        </Card>
        
        {/* Footer */}
        <div className="text-center mt-12 text-slate-500">
          <p className="font-mono text-sm">⚡ Powered by AI • Real-time Competitive Intelligence • Profit Maximization ⚡</p>
        </div>
      </div>
    </div>
  );
}
