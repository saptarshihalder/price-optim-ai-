


import React, { useState, useEffect, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useNavigate } from 'react-router-dom';
import { useUserGuardContext } from 'app/auth';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Target, 
  AlertTriangle, 
  CheckCircle, 
  Download, 
  Filter,
  Eye,
  Zap,
  BarChart3,
  PieChart,
  Sparkles,
  ArrowLeft
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  Area,
  AreaChart,
  ScatterChart,
  Scatter
} from 'recharts';
import brain from 'brain';
import { PriceRecommendation } from 'types';
import { toast } from 'sonner';

interface Product {
  id: string;
  name: string;
  current_price: number;
  unit_cost: number;
  currency: string;
  category: string;
  brand: string;
}

interface RecommendationWithSelection extends PriceRecommendation {
  selected: boolean;
  priority_rank?: number;
}

interface FilterOptions {
  category: string;
  minProfitThreshold: number;
  minConfidence: number;
  riskLevel: string;
}

const PricingRecommendations = () => {
  const navigate = useNavigate();
  const { user } = useUserGuardContext();
  const [recommendations, setRecommendations] = useState<RecommendationWithSelection[]>([]);
  const [loading, setLoading] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
  const [filters, setFilters] = useState<FilterOptions>({
    category: 'all',
    minProfitThreshold: 0,
    minConfidence: 0,
    riskLevel: 'all'
  });
  const [selectedAll, setSelectedAll] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  // Sample products data - in real app, this would come from database
  const sampleProducts: Product[] = [
    {
      id: 'SG0001',
      name: 'Reiek Peak Wooden Sunglasses (Incl. cork casing)',
      current_price: 57.95,
      unit_cost: 14.23,
      currency: 'EUR',
      category: 'sunglasses',
      brand: 'Dzukou'
    },
    {
      id: 'SG0002',
      name: 'Fibonacci Wooden Sunglasses (Incl. cork casing)',
      current_price: 61.50,
      unit_cost: 14.23,
      currency: 'EUR',
      category: 'sunglasses',
      brand: 'Dzukou'
    },
    {
      id: 'BT0005',
      name: 'Elephant Falls Thermos Bottle',
      current_price: 31.95,
      unit_cost: 8.34,
      currency: 'EUR',
      category: 'bottle',
      brand: 'Dzukou'
    },
    {
      id: 'NB0011-12',
      name: 'Tiger Trail Notebooks',
      current_price: 25.95,
      unit_cost: 6.79,
      currency: 'EUR',
      category: 'notebook',
      brand: 'Dzukou'
    }
  ];

  // Generate AI-powered pricing recommendations
  const generateRecommendations = async () => {
    setOptimizing(true);
    try {
      const batchRequest = {
        products: sampleProducts.map(p => ({
          id: p.id,
          name: p.name,
          current_price: p.current_price,
          unit_cost: p.unit_cost,
          currency: p.currency,
          category: p.category,
          brand: p.brand
        })),
        competitor_data: {},
        global_constraints: {
          min_margin_percent: 25.0,
          max_price_increase_percent: 30.0,
          psychological_pricing: true,
          competitive_positioning: 'competitive',
          demand_sensitivity: 1.0
        }
      };

      const response = await brain.optimize_batch(batchRequest);
      const data = await response.json();

      if (data.recommendations) {
        // Add selection state and priority ranking
        const rankedRecommendations = data.recommendations
          .map((rec: PriceRecommendation, index: number) => ({
            ...rec,
            selected: false,
            priority_rank: index + 1
          }))
          .sort((a: PriceRecommendation, b: PriceRecommendation) => 
            b.expected_profit_change - a.expected_profit_change
          );

        setRecommendations(rankedRecommendations);
        toast.success(`Generated ${rankedRecommendations.length} pricing recommendations`);
      }
    } catch (error) {
      console.error('Optimization failed:', error);
      toast.error('Failed to generate recommendations');
    } finally {
      setOptimizing(false);
    }
  };

  // Apply filters to recommendations
  const filteredRecommendations = useMemo(() => {
    return recommendations.filter(rec => {
      if (filters.category !== 'all') {
        const product = sampleProducts.find(p => p.id === rec.product_id);
        if (!product || product.category !== filters.category) return false;
      }
      if (rec.expected_profit_change < filters.minProfitThreshold) return false;
      if (rec.confidence_score < filters.minConfidence / 100) return false;
      if (filters.riskLevel !== 'all' && rec.risk_level !== filters.riskLevel) return false;
      return true;
    });
  }, [recommendations, filters, sampleProducts]);

  // Calculate summary statistics
  const summary = useMemo(() => {
    const selected = filteredRecommendations.filter(r => r.selected);
    return {
      totalProducts: filteredRecommendations.length,
      selectedProducts: selected.length,
      totalProfitUpift: selected.reduce((sum, r) => sum + r.expected_profit_change, 0),
      avgPriceIncrease: selected.length > 0 
        ? selected.reduce((sum, r) => sum + r.price_change_percent, 0) / selected.length 
        : 0,
      highConfidenceCount: filteredRecommendations.filter(r => r.confidence_score > 0.8).length,
      implementationReady: selected.filter(r => r.risk_level === 'low').length
    };
  }, [filteredRecommendations]);

  // Toggle selection
  const toggleSelection = (productId: string) => {
    setRecommendations(prev => 
      prev.map(rec => 
        rec.product_id === productId 
          ? { ...rec, selected: !rec.selected }
          : rec
      )
    );
  };

  const toggleSelectAll = () => {
    const newSelectedState = !selectedAll;
    setSelectedAll(newSelectedState);
    setRecommendations(prev => 
      prev.map(rec => ({ ...rec, selected: newSelectedState }))
    );
  };

  // Export to CSV
  const exportToCSV = () => {
    const selectedRecs = recommendations.filter(r => r.selected);
    if (selectedRecs.length === 0) {
      toast.error('Please select recommendations to export');
      return;
    }

    const csvHeaders = [
      'Product ID',
      'Product Name', 
      'Current Price',
      'Recommended Price',
      'Price Change %',
      'Expected Profit Change',
      'Expected Demand Change %',
      'Confidence Score',
      'Risk Level',
      'Competitive Position',
      'Rationale'
    ];

    const csvData = selectedRecs.map(rec => {
      const product = sampleProducts.find(p => p.id === rec.product_id);
      return [
        rec.product_id,
        product?.name || '',
        rec.current_price,
        rec.recommended_price,
        rec.price_change_percent,
        rec.expected_profit_change,
        rec.expected_demand_change_percent,
        rec.confidence_score,
        rec.risk_level,
        rec.competitive_position,
        `"${rec.rationale.replace(/"/g, '""')}"`
      ];
    });

    const csvContent = [csvHeaders, ...csvData]
      .map(row => row.join(','))
      .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pricing-recommendations-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);

    toast.success(`Exported ${selectedRecs.length} recommendations to CSV`);
  };

  // Get risk color
  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low': return 'text-green-400 border-green-400/30 bg-green-400/10';
      case 'medium': return 'text-amber-400 border-amber-400/30 bg-amber-400/10';
      case 'high': return 'text-red-400 border-red-400/30 bg-red-400/10';
      default: return 'text-gray-400 border-gray-400/30 bg-gray-400/10';
    }
  };

  // Get profit impact color
  const getProfitColor = (change: number) => {
    if (change > 50) return 'text-green-400';
    if (change > 0) return 'text-green-300';
    if (change > -25) return 'text-amber-400';
    return 'text-red-400';
  };

  // Prepare chart data
  const chartData = useMemo(() => {
    // Profit impact chart data
    const profitImpactData = filteredRecommendations.map(rec => {
      const product = sampleProducts.find(p => p.id === rec.product_id);
      return {
        name: product?.name.substring(0, 20) + '...' || rec.product_id,
        profit_change: rec.expected_profit_change,
        current_price: rec.current_price,
        recommended_price: rec.recommended_price,
        confidence: rec.confidence_score * 100,
        risk_level: rec.risk_level,
        category: product?.category || 'unknown'
      };
    }).sort((a, b) => b.profit_change - a.profit_change);

    // Risk distribution data
    const riskDistribution = [
      { name: 'Low Risk', value: filteredRecommendations.filter(r => r.risk_level === 'low').length, color: '#10b981' },
      { name: 'Medium Risk', value: filteredRecommendations.filter(r => r.risk_level === 'medium').length, color: '#f59e0b' },
      { name: 'High Risk', value: filteredRecommendations.filter(r => r.risk_level === 'high').length, color: '#ef4444' }
    ];

    // Category performance data
    const categoryData = Object.entries(
      filteredRecommendations.reduce((acc, rec) => {
        const product = sampleProducts.find(p => p.id === rec.product_id);
        const category = product?.category || 'unknown';
        if (!acc[category]) {
          acc[category] = { total_profit: 0, count: 0, avg_confidence: 0 };
        }
        acc[category].total_profit += rec.expected_profit_change;
        acc[category].count += 1;
        acc[category].avg_confidence += rec.confidence_score;
        return acc;
      }, {} as Record<string, { total_profit: number; count: number; avg_confidence: number }>)
    ).map(([category, data]) => ({
      category: category.charAt(0).toUpperCase() + category.slice(1),
      total_profit: data.total_profit,
      avg_profit: data.total_profit / data.count,
      avg_confidence: (data.avg_confidence / data.count) * 100,
      count: data.count
    }));

    // Price vs confidence scatter data
    const scatterData = filteredRecommendations.map(rec => {
      const product = sampleProducts.find(p => p.id === rec.product_id);
      return {
        x: rec.price_change_percent,
        y: rec.confidence_score * 100,
        profit: rec.expected_profit_change,
        name: product?.name || rec.product_id,
        risk: rec.risk_level
      };
    });

    return {
      profitImpactData: profitImpactData.slice(0, 10), // Top 10 for readability
      riskDistribution,
      categoryData,
      scatterData
    };
  }, [filteredRecommendations, sampleProducts]);

  // Custom tooltip components
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-lg">
          <p className="text-white font-medium">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ color: entry.color }}>
              {entry.dataKey}: {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  // Implementation timeline suggestions
  const getImplementationPriority = () => {
    const highImpact = filteredRecommendations
      .filter(r => r.expected_profit_change > 10 && r.risk_level === 'low')
      .length;
    const mediumImpact = filteredRecommendations
      .filter(r => r.expected_profit_change > 5 && r.risk_level !== 'high')
      .length;
    const lowImpact = filteredRecommendations.length - highImpact - mediumImpact;

    return {
      immediate: highImpact,
      shortTerm: mediumImpact,
      longTerm: lowImpact
    };
  };

  const implementationPriority = getImplementationPriority();

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white">
      {/* Cyberpunk Grid Background */}
      <div className="absolute inset-0 opacity-20" style={{
        backgroundImage: `url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiMwNTk2NjkiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTAgMGgzMHYzMEgwVjB6bTMwIDMwaDMwdjMwSDMwVjMweiIvPjwvZz48L2c+PC9zdmc+')`
      }} />
      
      <div className="relative z-10 p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <Button 
              variant="ghost" 
              onClick={() => navigate('/')}
              className="text-gray-400 hover:text-white hover:bg-gray-800/50"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Dashboard
            </Button>
            <div className="h-8 w-px bg-gray-600" />
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-green-400 to-blue-400 bg-clip-text text-transparent">
                AI Pricing Recommendations
              </h1>
              <p className="text-gray-400 mt-1">Optimize prices with AI-powered competitive analysis</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <Button 
              onClick={() => navigate('/competitive-analysis')}
              variant="outline"
              className="border-blue-500/50 text-blue-400 hover:bg-blue-500/10"
            >
              <Eye className="w-4 h-4 mr-2" />
              View Analysis
            </Button>
            <Button 
              onClick={generateRecommendations}
              disabled={optimizing}
              className="bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white border-0"
            >
              {optimizing ? (
                <div className="animate-spin w-4 h-4 mr-2 border-2 border-white/30 border-t-white rounded-full" />
              ) : (
                <Zap className="w-4 h-4 mr-2" />
              )}
              {optimizing ? 'Optimizing...' : 'Generate Recommendations'}
            </Button>
          </div>
        </div>

        {recommendations.length === 0 ? (
          // Empty State
          <Card className="border-gray-700 bg-gray-800/50 backdrop-blur">
            <CardContent className="flex flex-col items-center justify-center py-16 text-center">
              <div className="w-16 h-16 rounded-full bg-gradient-to-r from-green-500/20 to-blue-500/20 flex items-center justify-center mb-6">
                <Sparkles className="w-8 h-8 text-green-400" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Ready to Optimize Pricing</h3>
              <p className="text-gray-400 mb-6 max-w-md">
                Generate AI-powered pricing recommendations based on competitive analysis and profit optimization algorithms.
              </p>
              <Button 
                onClick={generateRecommendations}
                disabled={optimizing}
                className="bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700"
              >
                {optimizing ? (
                  <div className="animate-spin w-4 h-4 mr-2 border-2 border-white/30 border-t-white rounded-full" />
                ) : (
                  <Zap className="w-4 h-4 mr-2" />
                )}
                {optimizing ? 'Generating...' : 'Generate Recommendations'}
              </Button>
            </CardContent>
          </Card>
        ) : (
          <>
            {/* Executive Summary */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <Card className="border-green-500/30 bg-gradient-to-r from-green-500/10 to-green-600/5 backdrop-blur">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-green-400 text-sm font-medium">Total Profit Uplift</p>
                      <p className="text-2xl font-bold text-white">
                        €{summary.totalProfitUpift.toFixed(2)}
                      </p>
                    </div>
                    <DollarSign className="w-8 h-8 text-green-400" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-blue-500/30 bg-gradient-to-r from-blue-500/10 to-blue-600/5 backdrop-blur">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-blue-400 text-sm font-medium">Avg Price Change</p>
                      <p className="text-2xl font-bold text-white">
                        {summary.avgPriceIncrease >= 0 ? '+' : ''}{summary.avgPriceIncrease.toFixed(1)}%
                      </p>
                    </div>
                    <TrendingUp className="w-8 h-8 text-blue-400" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-amber-500/30 bg-gradient-to-r from-amber-500/10 to-amber-600/5 backdrop-blur">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-amber-400 text-sm font-medium">High Confidence</p>
                      <p className="text-2xl font-bold text-white">
                        {summary.highConfidenceCount}/{summary.totalProducts}
                      </p>
                    </div>
                    <Target className="w-8 h-8 text-amber-400" />
                  </div>
                </CardContent>
              </Card>

              <Card className="border-purple-500/30 bg-gradient-to-r from-purple-500/10 to-purple-600/5 backdrop-blur">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-purple-400 text-sm font-medium">Ready to Implement</p>
                      <p className="text-2xl font-bold text-white">
                        {summary.implementationReady}
                      </p>
                    </div>
                    <CheckCircle className="w-8 h-8 text-purple-400" />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Filters and Actions */}
            <Card className="border-gray-700 bg-gray-800/50 backdrop-blur mb-6">
              <CardContent className="p-6">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="flex items-center gap-2">
                    <Filter className="w-4 h-4 text-gray-400" />
                    <span className="text-sm font-medium text-gray-300">Filters:</span>
                  </div>
                  
                  <Select value={filters.category} onValueChange={(value) => setFilters(prev => ({ ...prev, category: value }))}>
                    <SelectTrigger className="w-40 border-gray-600 bg-gray-700">
                      <SelectValue placeholder="Category" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Categories</SelectItem>
                      <SelectItem value="sunglasses">Sunglasses</SelectItem>
                      <SelectItem value="bottle">Bottles</SelectItem>
                      <SelectItem value="notebook">Notebooks</SelectItem>
                      <SelectItem value="mug">Mugs</SelectItem>
                      <SelectItem value="stand">Stands</SelectItem>
                      <SelectItem value="lunchbox">Lunchboxes</SelectItem>
                      <SelectItem value="stole">Stoles</SelectItem>
                    </SelectContent>
                  </Select>

                  <Select value={filters.riskLevel} onValueChange={(value) => setFilters(prev => ({ ...prev, riskLevel: value }))}>
                    <SelectTrigger className="w-32 border-gray-600 bg-gray-700">
                      <SelectValue placeholder="Risk" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Risk Levels</SelectItem>
                      <SelectItem value="low">Low Risk</SelectItem>
                      <SelectItem value="medium">Medium Risk</SelectItem>
                      <SelectItem value="high">High Risk</SelectItem>
                    </SelectContent>
                  </Select>

                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-400">Min Confidence:</span>
                    <Input 
                      type="number" 
                      min="0" 
                      max="100" 
                      value={filters.minConfidence}
                      onChange={(e) => setFilters(prev => ({ ...prev, minConfidence: Number(e.target.value) }))}
                      className="w-20 border-gray-600 bg-gray-700"
                    />
                    <span className="text-sm text-gray-400">%</span>
                  </div>

                  <Separator orientation="vertical" className="h-6 bg-gray-600" />
                  
                  <div className="flex items-center gap-3">
                    <Checkbox 
                      checked={selectedAll}
                      onCheckedChange={toggleSelectAll}
                      className="border-gray-500"
                    />
                    <span className="text-sm text-gray-300">Select All ({summary.selectedProducts} selected)</span>
                  </div>

                  <Button 
                    onClick={exportToCSV}
                    disabled={summary.selectedProducts === 0}
                    variant="outline"
                    className="border-green-500/50 text-green-400 hover:bg-green-500/10 ml-auto"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Export CSV
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Recommendations Table */}
            <Card className="border-gray-700 bg-gray-800/50 backdrop-blur">
              <CardHeader>
                <CardTitle className="text-xl font-semibold text-white flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-green-400" />
                  Pricing Recommendations ({filteredRecommendations.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="border-b border-gray-700">
                      <tr className="text-left">
                        <th className="p-4 text-sm font-medium text-gray-300">Select</th>
                        <th className="p-4 text-sm font-medium text-gray-300">Product</th>
                        <th className="p-4 text-sm font-medium text-gray-300">Current Price</th>
                        <th className="p-4 text-sm font-medium text-gray-300">Recommended</th>
                        <th className="p-4 text-sm font-medium text-gray-300">Change</th>
                        <th className="p-4 text-sm font-medium text-gray-300">Profit Impact</th>
                        <th className="p-4 text-sm font-medium text-gray-300">Confidence</th>
                        <th className="p-4 text-sm font-medium text-gray-300">Risk</th>
                        <th className="p-4 text-sm font-medium text-gray-300">Rationale</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredRecommendations.map((rec) => {
                        const product = sampleProducts.find(p => p.id === rec.product_id);
                        return (
                          <tr key={rec.product_id} className="border-b border-gray-700/50 hover:bg-gray-700/20">
                            <td className="p-4">
                              <Checkbox 
                                checked={rec.selected}
                                onCheckedChange={() => toggleSelection(rec.product_id)}
                                className="border-gray-500"
                              />
                            </td>
                            <td className="p-4">
                              <div>
                                <p className="font-medium text-white">{product?.name}</p>
                                <p className="text-sm text-gray-400">{product?.category} • {product?.brand}</p>
                              </div>
                            </td>
                            <td className="p-4">
                              <span className="text-white font-mono">€{rec.current_price.toFixed(2)}</span>
                            </td>
                            <td className="p-4">
                              <span className="text-green-400 font-mono font-semibold">€{rec.recommended_price.toFixed(2)}</span>
                            </td>
                            <td className="p-4">
                              <div className="flex items-center gap-2">
                                {rec.price_change_percent >= 0 ? (
                                  <TrendingUp className="w-4 h-4 text-green-400" />
                                ) : (
                                  <TrendingDown className="w-4 h-4 text-red-400" />
                                )}
                                <span className={rec.price_change_percent >= 0 ? 'text-green-400' : 'text-red-400'}>
                                  {rec.price_change_percent >= 0 ? '+' : ''}{rec.price_change_percent.toFixed(1)}%
                                </span>
                              </div>
                            </td>
                            <td className="p-4">
                              <span className={getProfitColor(rec.expected_profit_change)}>
                                €{rec.expected_profit_change.toFixed(2)}
                              </span>
                            </td>
                            <td className="p-4">
                              <div className="flex items-center gap-2">
                                <Progress 
                                  value={rec.confidence_score * 100} 
                                  className="w-12 h-2 bg-gray-700"
                                />
                                <span className="text-blue-400 text-sm">{(rec.confidence_score * 100).toFixed(0)}%</span>
                              </div>
                            </td>
                            <td className="p-4">
                              <Badge className={getRiskColor(rec.risk_level)}>
                                {rec.risk_level}
                              </Badge>
                            </td>
                            <td className="p-4 max-w-xs">
                              <p className="text-sm text-gray-300 truncate" title={rec.rationale}>
                                {rec.rationale}
                              </p>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </div>
  );
};

export default PricingRecommendations;
