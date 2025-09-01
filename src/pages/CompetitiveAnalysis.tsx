import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  TrendingUp, 
  TrendingDown, 
  Download, 
  Filter, 
  Search, 
  Target, 
  DollarSign,
  AlertTriangle,
  CheckCircle,
  BarChart3,
  Zap,
  RefreshCw,
  ArrowLeft
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { brain } from 'brain';
import { ScrapedProduct } from 'types';
import { StorageUtils } from 'utils/storage';

interface OurProduct {
  id: string;
  name: string;
  current_price: number;
  unit_cost: number;
  currency: string;
  category?: string;
}

interface ComparisonRow {
  our_product: OurProduct;
  competitors: ScrapedProduct[];
  min_price: number;
  max_price: number;
  median_price: number;
  avg_price: number;
  our_position: 'underpriced' | 'competitive' | 'overpriced';
  profit_opportunity: number;
  competitor_count: number;
}

const CompetitiveAnalysis: React.FC = () => {
  const navigate = useNavigate();
  const [comparisonData, setComparisonData] = useState<ComparisonRow[]>([]);
  const [filteredData, setFilteredData] = useState<ComparisonRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<string>('profit_opportunity');
  const [filterBy, setFilterBy] = useState<string>('all');
  const [selectedProduct, setSelectedProduct] = useState<ComparisonRow | null>(null);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [hasScrapingData, setHasScrapingData] = useState(false);

  // Our product catalog from the CSV data
  const ourProducts: OurProduct[] = [
    { id: 'SG0001', name: 'Reiek Peak Wooden Sunglasses', current_price: 57.95, unit_cost: 14.23, currency: 'EUR', category: 'sunglasses' },
    { id: 'SG0002', name: 'Fibonacci Wooden Sunglasses', current_price: 61.50, unit_cost: 14.23, currency: 'EUR', category: 'sunglasses' },
    { id: 'BT0005', name: 'Elephant Falls Thermos Bottle', current_price: 31.95, unit_cost: 8.34, currency: 'EUR', category: 'bottle' },
    { id: 'BT0012-13', name: 'Saint Elias Thermos bottles', current_price: 32.95, unit_cost: 9.31, currency: 'EUR', category: 'bottle' },
    { id: 'BT0015-16', name: 'Inca Trail Coffee Mugs', current_price: 31.95, unit_cost: 8.55, currency: 'EUR', category: 'mug' },
    { id: 'PS0007', name: 'Woodland Mouse Phone Stand', current_price: 18.95, unit_cost: 3.01, currency: 'EUR', category: 'stand' },
    { id: 'NB0011-12', name: 'Tiger Trail Notebooks', current_price: 25.95, unit_cost: 6.79, currency: 'EUR', category: 'notebook' },
    { id: 'NB0013-15', name: 'Papillon Notebooks', current_price: 23.95, unit_cost: 5.21, currency: 'EUR', category: 'notebook' },
    { id: 'LB0017', name: 'Jim Corbett Lunchbox Band 1200ML', current_price: 32.95, unit_cost: 19.45, currency: 'EUR', category: 'lunchbox' },
    { id: 'LB0019', name: 'Jim Corbett Lunchbox Band 800ML', current_price: 30.95, unit_cost: 7.59, currency: 'EUR', category: 'lunchbox' },
    { id: 'SH0017-26', name: 'Timeless Silk Colored Stole', current_price: 73.95, unit_cost: 39.48, currency: 'EUR', category: 'stole' },
    { id: 'SH0025', name: 'Silk Uncut White Stole', current_price: 114.95, unit_cost: 33.92, currency: 'EUR', category: 'stole' }
  ];

  // Load scraping results on component mount
  useEffect(() => {
    loadLatestScrapingResults();
  }, []);

  const loadLatestScrapingResults = async () => {
    try {
      setLoading(true);
      
      // Try to get the latest task ID from localStorage
      const latestTaskId = StorageUtils.getLatestScrapingTaskId();
      
      if (!latestTaskId) {
        setHasScrapingData(false);
        setLoading(false);
        return;
      }

      // Check if the task is completed
      const progressResponse = await brain.get_scraping_progress(latestTaskId);
      const progressData = progressResponse.data;

      if (progressData.status !== 'completed') {
        setHasScrapingData(false);
        setLoading(false);
        toast.error('Latest scraping task is not completed yet. Please wait or start a new scraping task.');
        return;
      }

      // Fetch the actual results
      const resultsResponse = await brain.get_scraping_results(latestTaskId);
      const results = resultsResponse.data;
      
      if (results.length === 0) {
        setHasScrapingData(false);
        setLoading(false);
        toast.error('No scraping results found. Please run a scraping task first.');
        return;
      }

      setHasScrapingData(true);
      generateComparisonData(results);
      setLastRefresh(new Date());
      
    } catch (error) {
      console.error('Error loading scraping results:', error);
      setHasScrapingData(false);
      toast.error('Failed to load scraping results. Please run a scraping task first.');
    } finally {
      setLoading(false);
    }
  };

  const generateComparisonData = (results: ScrapedProduct[]) => {
    const comparisonRows: ComparisonRow[] = [];
    
    ourProducts.forEach(product => {
      // Find competitors for this product based on category and match score
      const competitors = results.filter(result => {
        const categoryMatch = product.category && result.title.toLowerCase().includes(product.category);
        const nameMatch = result.match_score && result.match_score > 0.1;
        return categoryMatch || nameMatch;
      });
      
      if (competitors.length > 0) {
        const prices = competitors.filter(c => c.price && c.price > 0).map(c => c.price!);
        
        if (prices.length > 0) {
          const min_price = Math.min(...prices);
          const max_price = Math.max(...prices);
          const avg_price = prices.reduce((a, b) => a + b, 0) / prices.length;
          const sorted_prices = [...prices].sort((a, b) => a - b);
          const median_price = sorted_prices.length % 2 === 0 
            ? (sorted_prices[sorted_prices.length / 2 - 1] + sorted_prices[sorted_prices.length / 2]) / 2
            : sorted_prices[Math.floor(sorted_prices.length / 2)];
          
          // Convert our price to USD for comparison (assuming 1 EUR = 1.1 USD)
          const our_price_usd = product.currency === 'EUR' ? product.current_price * 1.1 : product.current_price;
          
          let our_position: 'underpriced' | 'competitive' | 'overpriced';
          if (our_price_usd < min_price) {
            our_position = 'underpriced';
          } else if (our_price_usd > max_price) {
            our_position = 'overpriced';
          } else {
            our_position = 'competitive';
          }
          
          // Calculate profit opportunity (potential price increase)
          const profit_opportunity = our_position === 'underpriced' 
            ? (median_price - our_price_usd) * 0.8 // Conservative 80% of the gap
            : 0;
          
          comparisonRows.push({
            our_product: product,
            competitors,
            min_price,
            max_price,
            median_price,
            avg_price,
            our_position,
            profit_opportunity,
            competitor_count: competitors.length
          });
        }
      }
    });
    
    setComparisonData(comparisonRows);
    setFilteredData(comparisonRows);
  };

  const refreshData = async () => {
    setRefreshing(true);
    try {
      await loadLatestScrapingResults();
      toast.success('Data refreshed successfully!');
    } catch (error) {
      toast.error('Failed to refresh data');
    } finally {
      setRefreshing(false);
    }
  };

  const startNewScraping = () => {
    navigate('/scraping');
  };

  // Apply filters and sorting
  useEffect(() => {
    let filtered = [...comparisonData];
    
    // Search filter
    if (searchTerm) {
      filtered = filtered.filter(row => 
        row.our_product.name.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }
    
    // Category filter
    if (filterBy !== 'all') {
      filtered = filtered.filter(row => {
        if (filterBy === 'underpriced') return row.our_position === 'underpriced';
        if (filterBy === 'overpriced') return row.our_position === 'overpriced';
        if (filterBy === 'competitive') return row.our_position === 'competitive';
        return true;
      });
    }
    
    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'profit_opportunity':
          return b.profit_opportunity - a.profit_opportunity;
        case 'competitor_count':
          return b.competitor_count - a.competitor_count;
        case 'price_gap':
          return Math.abs(b.median_price - (b.our_product.current_price * 1.1)) - 
                 Math.abs(a.median_price - (a.our_product.current_price * 1.1));
        default:
          return 0;
      }
    });
    
    setFilteredData(filtered);
  }, [comparisonData, searchTerm, filterBy, sortBy]);

  const getPositionColor = (position: string) => {
    switch (position) {
      case 'underpriced': return 'text-green-400 bg-green-500/20';
      case 'overpriced': return 'text-red-400 bg-red-500/20';
      case 'competitive': return 'text-blue-400 bg-blue-500/20';
      default: return 'text-gray-400 bg-gray-500/20';
    }
  };

  const getPositionIcon = (position: string) => {
    switch (position) {
      case 'underpriced': return <TrendingUp className="h-4 w-4" />;
      case 'overpriced': return <TrendingDown className="h-4 w-4" />;
      case 'competitive': return <Target className="h-4 w-4" />;
      default: return <DollarSign className="h-4 w-4" />;
    }
  };

  const exportData = () => {
    if (filteredData.length === 0) {
      toast.error('No data to export');
      return;
    }

    const csvData = filteredData.map(row => ({
      'Product ID': row.our_product.id,
      'Product Name': row.our_product.name,
      'Our Price (EUR)': row.our_product.current_price,
      'Our Price (USD)': (row.our_product.current_price * 1.1).toFixed(2),
      'Min Competitor': row.min_price.toFixed(2),
      'Median Competitor': row.median_price.toFixed(2),
      'Max Competitor': row.max_price.toFixed(2),
      'Position': row.our_position,
      'Profit Opportunity': row.profit_opportunity.toFixed(2),
      'Competitors Found': row.competitor_count
    }));
    
    const csv = [
      Object.keys(csvData[0]).join(','),
      ...csvData.map(row => Object.values(row).join(','))
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `competitive-analysis-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast.success('Competitive analysis data exported successfully!');
  };

  // Prepare chart data
  const chartData = filteredData.map(row => ({
    name: row.our_product.name.substring(0, 20) + '...',
    ourPrice: row.our_product.current_price * 1.1,
    minCompetitor: row.min_price,
    maxCompetitor: row.max_price,
    medianCompetitor: row.median_price,
    profitOpportunity: row.profit_opportunity
  }));

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 border-4 border-green-400 border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-gray-300">Loading competitive analysis...</p>
        </div>
      </div>
    );
  }

  // No scraping data available state
  if (!hasScrapingData) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black p-6">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="flex items-center gap-4 mb-8">
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
              <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-green-400 via-blue-500 to-purple-600">
                Competitive Analysis Dashboard
              </h1>
            </div>
          </div>

          {/* No Data State */}
          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="flex flex-col items-center justify-center py-16 text-center">
              <div className="w-16 h-16 rounded-full bg-gradient-to-r from-blue-500/20 to-purple-500/20 flex items-center justify-center mb-6">
                <BarChart3 className="w-8 h-8 text-blue-400" />
              </div>
              <h3 className="text-xl font-semibold mb-2 text-white">No Competitive Data Available</h3>
              <p className="text-gray-400 mb-6 max-w-md">
                To perform competitive analysis, you need to first run a competitor scraping task to collect pricing data from competitor stores.
              </p>
              <div className="flex gap-3">
                <Button 
                  onClick={startNewScraping}
                  className="bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700"
                >
                  <Search className="w-4 h-4 mr-2" />
                  Start Scraping Task
                </Button>
                <Button 
                  onClick={refreshData}
                  variant="outline"
                  className="border-blue-500/50 text-blue-400 hover:bg-blue-500/10"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Check for Data
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black p-6">
      <div className="max-w-7xl mx-auto space-y-6">
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
              <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-green-400 via-blue-500 to-purple-600">
                Competitive Analysis Dashboard
              </h1>
              <p className="text-gray-300 text-lg">
                Real-time price comparison matrix across competitor stores
              </p>
            </div>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-green-400">{filteredData.filter(r => r.our_position === 'underpriced').length}</div>
              <div className="text-xs text-gray-400">Underpriced Products</div>
              <div className="text-xs text-green-300 mt-1">Profit Opportunities</div>
            </CardContent>
          </Card>
          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-blue-400">{filteredData.filter(r => r.our_position === 'competitive').length}</div>
              <div className="text-xs text-gray-400">Competitive Products</div>
              <div className="text-xs text-blue-300 mt-1">Well Positioned</div>
            </CardContent>
          </Card>
          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-red-400">{filteredData.filter(r => r.our_position === 'overpriced').length}</div>
              <div className="text-xs text-gray-400">Overpriced Products</div>
              <div className="text-xs text-red-300 mt-1">Price Reduction Needed</div>
            </CardContent>
          </Card>
          <Card className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-amber-400">
                ${filteredData.reduce((sum, row) => sum + row.profit_opportunity, 0).toFixed(0)}
              </div>
              <div className="text-xs text-gray-400">Total Profit Opportunity</div>
              <div className="text-xs text-amber-300 mt-1">Potential Revenue</div>
            </CardContent>
          </Card>
        </div>

        {/* Controls */}
        <Card className="bg-gray-800/50 border-gray-700">
          <CardContent className="p-4">
            <div className="flex flex-wrap gap-4 items-center">
              <div className="flex-1 min-w-64">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                  <Input
                    placeholder="Search products..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10 bg-gray-700 border-gray-600 text-gray-200"
                  />
                </div>
              </div>
              <Select value={filterBy} onValueChange={setFilterBy}>
                <SelectTrigger className="w-48 bg-gray-700 border-gray-600">
                  <Filter className="h-4 w-4 mr-2" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Products</SelectItem>
                  <SelectItem value="underpriced">Underpriced</SelectItem>
                  <SelectItem value="competitive">Competitive</SelectItem>
                  <SelectItem value="overpriced">Overpriced</SelectItem>
                </SelectContent>
              </Select>
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger className="w-48 bg-gray-700 border-gray-600">
                  <BarChart3 className="h-4 w-4 mr-2" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="profit_opportunity">Profit Opportunity</SelectItem>
                  <SelectItem value="competitor_count">Competitor Count</SelectItem>
                  <SelectItem value="price_gap">Price Gap</SelectItem>
                </SelectContent>
              </Select>
              <Button onClick={exportData} className="bg-green-600 hover:bg-green-700">
                <Download className="h-4 w-4 mr-2" />
                Export CSV
              </Button>
              <Button 
                onClick={refreshData} 
                disabled={refreshing}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {refreshing ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                ) : (
                  <RefreshCw className="h-4 w-4 mr-2" />
                )}
                Refresh Data
              </Button>
              <Button 
                onClick={startNewScraping} 
                disabled={refreshing}
                className="bg-purple-600 hover:bg-purple-700"
              >
                <Zap className="h-4 w-4 mr-2" />
                New Scraping
              </Button>
            </div>
            <div className="text-xs text-gray-400 mt-2">
              Last updated: {lastRefresh.toLocaleString()}
            </div>
          </CardContent>
        </Card>

        {/* Price Comparison Chart */}
        {chartData.length > 0 && (
          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-green-400">Price Comparison Overview</CardTitle>
              <CardDescription className="text-gray-400">
                Our prices vs competitor range (USD)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis 
                      dataKey="name" 
                      stroke="#9CA3AF" 
                      fontSize={12}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis stroke="#9CA3AF" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#1F2937', 
                        border: '1px solid #374151',
                        borderRadius: '6px'
                      }}
                    />
                    <Bar dataKey="ourPrice" fill="#10B981" name="Our Price" />
                    <Bar dataKey="minCompetitor" fill="#3B82F6" name="Min Competitor" />
                    <Bar dataKey="maxCompetitor" fill="#EF4444" name="Max Competitor" />
                    <Bar dataKey="medianCompetitor" fill="#F59E0B" name="Median Competitor" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Comparison Table */}
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="text-blue-400 flex items-center gap-2">
              <Zap className="h-5 w-5" />
              Price Comparison Matrix
            </CardTitle>
            <CardDescription className="text-gray-400">
              Detailed competitor analysis with profit opportunities
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-gray-700">
                    <TableHead className="text-gray-300">Product</TableHead>
                    <TableHead className="text-gray-300">Our Price</TableHead>
                    <TableHead className="text-gray-300">Min/Med/Max</TableHead>
                    <TableHead className="text-gray-300">Position</TableHead>
                    <TableHead className="text-gray-300">Competitors</TableHead>
                    <TableHead className="text-gray-300">Profit Opportunity</TableHead>
                    <TableHead className="text-gray-300">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredData.map((row, index) => (
                    <TableRow key={index} className="border-gray-700/50 hover:bg-gray-700/30">
                      <TableCell>
                        <div>
                          <div className="font-medium text-gray-200">{row.our_product.name}</div>
                          <div className="text-sm text-gray-400">{row.our_product.id}</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-gray-200">
                          €{row.our_product.current_price.toFixed(2)}
                        </div>
                        <div className="text-sm text-gray-400">
                          ~${(row.our_product.current_price * 1.1).toFixed(2)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1 text-sm">
                          <div className="text-blue-400">${row.min_price.toFixed(2)}</div>
                          <div className="text-amber-400">${row.median_price.toFixed(2)}</div>
                          <div className="text-red-400">${row.max_price.toFixed(2)}</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className={`${getPositionColor(row.our_position)} border-none`}>
                          {getPositionIcon(row.our_position)}
                          <span className="ml-1">{row.our_position}</span>
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="text-gray-200">{row.competitor_count} stores</div>
                        <div className="text-xs text-gray-400">
                          Avg confidence: {(row.competitors.reduce((sum, c) => sum + (c.match_score || 0), 0) / row.competitors.length * 100).toFixed(0)}%
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className={`text-lg font-bold ${
                          row.profit_opportunity > 0 ? 'text-green-400' : 'text-gray-400'
                        }`}>
                          ${row.profit_opportunity.toFixed(2)}
                        </div>
                        {row.profit_opportunity > 0 && (
                          <div className="text-xs text-green-300">
                            +{((row.profit_opportunity / (row.our_product.current_price * 1.1)) * 100).toFixed(1)}%
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <Button 
                          size="sm" 
                          variant="outline" 
                          onClick={() => setSelectedProduct(row)}
                          className="border-gray-600 text-gray-300 hover:bg-gray-700"
                        >
                          View Details
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>

        {/* Product Detail Modal/Card */}
        {selectedProduct && (
          <Card className="bg-gray-800/50 border-green-500/30">
            <CardHeader>
              <CardTitle className="text-green-400 flex items-center justify-between">
                {selectedProduct.our_product.name}
                <Button 
                  size="sm" 
                  variant="ghost" 
                  onClick={() => setSelectedProduct(null)}
                  className="text-gray-400 hover:text-gray-200"
                >
                  ×
                </Button>
              </CardTitle>
              <CardDescription className="text-gray-400">
                Detailed competitor analysis for {selectedProduct.our_product.id}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div>
                  <h4 className="text-lg font-medium text-gray-200 mb-3">Competitor Details</h4>
                  <div className="space-y-3">
                    {selectedProduct.competitors.map((competitor, index) => (
                      <div key={index} className="bg-gray-700/50 p-3 rounded-lg">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <div className="font-medium text-gray-200">{competitor.store_name}</div>
                            <div className="text-sm text-gray-300 mt-1">{competitor.title}</div>
                            {competitor.brand && (
                              <div className="text-sm text-gray-400">Brand: {competitor.brand}</div>
                            )}
                          </div>
                          <div className="text-right">
                            <div className="text-lg font-bold text-green-400">
                              {competitor.currency} {competitor.price?.toFixed(2) || 'N/A'}
                            </div>
                            <Badge variant={competitor.in_stock ? 'default' : 'destructive'} className="text-xs mt-1">
                              {competitor.in_stock ? 'In Stock' : 'Out of Stock'}
                            </Badge>
                          </div>
                        </div>
                        <div className="mt-2 flex justify-between items-center">
                          <div className="text-sm text-gray-400">
                            Match: {((competitor.match_score || 0) * 100).toFixed(0)}% ({competitor.match_confidence || 'unknown'})
                          </div>
                          <a 
                            href={competitor.product_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-blue-400 hover:text-blue-300 text-sm"
                          >
                            View Product →
                          </a>
                        </div>
                        {competitor.match_reasoning && (
                          <div className="text-xs text-gray-500 mt-1">
                            {competitor.match_reasoning}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <h4 className="text-lg font-medium text-gray-200 mb-3">Pricing Insights</h4>
                  <div className="space-y-4">
                    <div className="bg-gray-700/50 p-3 rounded-lg">
                      <div className="text-sm text-gray-400 mb-2">Price Distribution</div>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-gray-300">Our Price:</span>
                          <span className="text-green-400 font-bold">${(selectedProduct.our_product.current_price * 1.1).toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-300">Market Min:</span>
                          <span className="text-blue-400">${selectedProduct.min_price.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-300">Market Median:</span>
                          <span className="text-amber-400">${selectedProduct.median_price.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-300">Market Max:</span>
                          <span className="text-red-400">${selectedProduct.max_price.toFixed(2)}</span>
                        </div>
                      </div>
                    </div>
                    
                    {selectedProduct.profit_opportunity > 0 && (
                      <Alert className="bg-green-500/10 border-green-500/30">
                        <TrendingUp className="h-4 w-4" />
                        <AlertDescription className="text-green-300">
                          <div className="font-medium mb-1">Profit Opportunity Detected!</div>
                          <div className="text-sm">
                            You could potentially increase price by <strong>${selectedProduct.profit_opportunity.toFixed(2)}</strong> 
                            ({((selectedProduct.profit_opportunity / (selectedProduct.our_product.current_price * 1.1)) * 100).toFixed(1)}%) 
                            while remaining competitive.
                          </div>
                        </AlertDescription>
                      </Alert>
                    )}
                    
                    {selectedProduct.our_position === 'overpriced' && (
                      <Alert className="bg-red-500/10 border-red-500/30">
                        <AlertTriangle className="h-4 w-4" />
                        <AlertDescription className="text-red-300">
                          <div className="font-medium mb-1">Price Adjustment Needed</div>
                          <div className="text-sm">
                            Your product is priced above market maximum. Consider reducing price to improve competitiveness.
                          </div>
                        </AlertDescription>
                      </Alert>
                    )}
                    
                    {selectedProduct.our_position === 'competitive' && (
                      <Alert className="bg-blue-500/10 border-blue-500/30">
                        <CheckCircle className="h-4 w-4" />
                        <AlertDescription className="text-blue-300">
                          <div className="font-medium mb-1">Well Positioned</div>
                          <div className="text-sm">
                            Your product is competitively priced within the market range.
                          </div>
                        </AlertDescription>
                      </Alert>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default CompetitiveAnalysis;