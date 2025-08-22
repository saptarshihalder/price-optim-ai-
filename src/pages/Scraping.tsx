import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Search, CheckCircle, XCircle, Clock, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

interface ScrapingProgress {
  status: 'pending' | 'running' | 'completed' | 'failed';
  current_store?: string;
  completed_stores: number;
  total_stores: number;
  products_found: number;
  errors: string[];
  started_at?: string;
  completed_at?: string;
}

interface ScrapedProduct {
  store_name: string;
  title: string;
  price?: number;
  currency: string;
  brand?: string;
  product_url: string;
  in_stock: boolean;
  scraped_at: string;
  match_score?: number;
}

const ScrapingDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState<ScrapingProgress | null>(null);
  const [results, setResults] = useState<ScrapedProduct[]>([]);
  const [targetProducts, setTargetProducts] = useState<string[]>([
    'Wooden Sunglasses',
    'Thermos Bottle',
    'Coffee Mugs',
    'Phone Stand',
    'Notebooks',
    'Lunchbox',
    'Silk Stole'
  ]);

  const startScraping = async () => {
    try {
      setIsLoading(true);
      setResults([]);
      
      // Simulate API call
      const mockTaskId = `scrape_${Date.now()}`;
      setTaskId(mockTaskId);
      
      // Simulate progress updates
      const mockProgress: ScrapingProgress = {
        status: 'running',
        current_store: 'EarthHero',
        completed_stores: 0,
        total_stores: 15,
        products_found: 0,
        errors: []
      };
      setProgress(mockProgress);
      
      toast.success('Scraping started successfully!');
      
    } catch (error) {
      console.error('Error starting scraping:', error);
      toast.error('Failed to start scraping');
      setIsLoading(false);
    }
  };

  // Simulate progress updates
  useEffect(() => {
    if (!taskId || !isLoading) return;

    const stores = [
      'EarthHero', 'GOODEE', 'Made Trade', 'Package Free Shop', 'The Citizenry',
      'Ten Thousand Villages', 'NOVICA', 'The Little Market', 'DoneGood',
      'Folksy', 'IndieCart', 'Zero Waste Store', 'EcoRoots', 'Wild Minimalist', 'Green Eco Dream'
    ];

    let currentStore = 0;
    let productsFound = 0;

    const interval = setInterval(() => {
      if (currentStore >= stores.length) {
        // Scraping completed
        const sampleResults: ScrapedProduct[] = [
          {
            store_name: 'EarthHero',
            title: 'Bamboo Wooden Sunglasses',
            price: 45.00,
            currency: 'USD',
            brand: 'EcoShades',
            product_url: 'https://earthhero.com/products/bamboo-sunglasses',
            in_stock: true,
            scraped_at: new Date().toISOString(),
            match_score: 0.85
          },
          {
            store_name: 'GOODEE',
            title: 'Sustainable Wood Frame Glasses',
            price: 52.00,
            currency: 'USD',
            brand: 'GreenVision',
            product_url: 'https://goodeeworld.com/products/wood-glasses',
            in_stock: true,
            scraped_at: new Date().toISOString(),
            match_score: 0.78
          },
          {
            store_name: 'Made Trade',
            title: 'Eco-Friendly Wooden Sunglasses',
            price: 65.00,
            currency: 'USD',
            brand: 'SustainShades',
            product_url: 'https://madetrade.com/products/wooden-sunglasses',
            in_stock: false,
            scraped_at: new Date().toISOString(),
            match_score: 0.92
          },
          {
            store_name: 'Package Free Shop',
            title: 'Stainless Steel Water Bottle',
            price: 28.00,
            currency: 'USD',
            brand: 'HydroClean',
            product_url: 'https://packagefreeshop.com/products/steel-bottle',
            in_stock: true,
            scraped_at: new Date().toISOString(),
            match_score: 0.65
          },
          {
            store_name: 'Zero Waste Store',
            title: 'Insulated Thermos Flask',
            price: 35.00,
            currency: 'USD',
            brand: 'EcoFlask',
            product_url: 'https://zerowaste.store/products/thermos-flask',
            in_stock: true,
            scraped_at: new Date().toISOString(),
            match_score: 0.72
          }
        ];

        setProgress({
          status: 'completed',
          completed_stores: stores.length,
          total_stores: stores.length,
          products_found: sampleResults.length,
          errors: [],
          completed_at: new Date().toISOString()
        });
        setResults(sampleResults);
        setIsLoading(false);
        toast.success(`Scraping completed! Found ${sampleResults.length} products.`);
        clearInterval(interval);
        return;
      }

      productsFound += Math.floor(Math.random() * 3) + 1;
      
      setProgress({
        status: 'running',
        current_store: stores[currentStore],
        completed_stores: currentStore,
        total_stores: stores.length,
        products_found: productsFound,
        errors: []
      });

      currentStore++;
    }, 1500);

    return () => clearInterval(interval);
  }, [taskId, isLoading]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'running':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-yellow-500/20 text-yellow-300';
      case 'running': return 'bg-blue-500/20 text-blue-300';
      case 'completed': return 'bg-green-500/20 text-green-300';
      case 'failed': return 'bg-red-500/20 text-red-300';
      default: return 'bg-gray-500/20 text-gray-300';
    }
  };

  const progressPercentage = progress ? (progress.completed_stores / progress.total_stores) * 100 : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black p-6">
      <div className="max-w-6xl mx-auto space-y-6">
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
              <h1 className="text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-blue-500">
                Competitor Price Scraping Engine
              </h1>
              <p className="text-gray-300 text-lg">
                Concurrent multi-store data collection from 15 target competitors
              </p>
            </div>
          </div>
        </div>

        {/* Control Panel */}
        <Card className="bg-gray-800/50 border-gray-700">
          <CardHeader>
            <CardTitle className="text-green-400 flex items-center gap-2">
              <Search className="h-5 w-5" />
              Scraping Control Panel
            </CardTitle>
            <CardDescription className="text-gray-400">
              Configure and monitor competitor price scraping across multiple stores
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-300 mb-2 block">
                Target Products ({targetProducts.length})
              </label>
              <div className="flex flex-wrap gap-2">
                {targetProducts.map((product, index) => (
                  <Badge key={index} variant="outline" className="bg-gray-700 text-gray-300 border-gray-600">
                    {product}
                  </Badge>
                ))}
              </div>
            </div>
            
            <Button 
              onClick={startScraping} 
              disabled={isLoading}
              className="w-full bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Scraping in Progress...
                </>
              ) : (
                <>
                  <Search className="mr-2 h-4 w-4" />
                  Start Competitor Scraping
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Progress Tracking */}
        {progress && (
          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-blue-400 flex items-center gap-2">
                {getStatusIcon(progress.status)}
                Scraping Progress
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-300">Overall Progress</span>
                  <span className="text-gray-300">
                    {progress.completed_stores}/{progress.total_stores} stores
                  </span>
                </div>
                <Progress value={progressPercentage} className="h-3" />
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-3 bg-gray-700/50 rounded-lg">
                  <div className="text-2xl font-bold text-green-400">{progress.completed_stores}</div>
                  <div className="text-xs text-gray-400">Stores Completed</div>
                </div>
                <div className="text-center p-3 bg-gray-700/50 rounded-lg">
                  <div className="text-2xl font-bold text-blue-400">{progress.products_found}</div>
                  <div className="text-xs text-gray-400">Products Found</div>
                </div>
                <div className="text-center p-3 bg-gray-700/50 rounded-lg">
                  <div className="text-2xl font-bold text-amber-400">{progress.errors.length}</div>
                  <div className="text-xs text-gray-400">Errors</div>
                </div>
                <div className="text-center p-3 bg-gray-700/50 rounded-lg">
                  <Badge className={getStatusColor(progress.status)}>
                    {progress.status.toUpperCase()}
                  </Badge>
                  <div className="text-xs text-gray-400 mt-1">Status</div>
                </div>
              </div>
              
              {progress.current_store && (
                <Alert className="bg-blue-500/10 border-blue-500/30">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <AlertDescription className="text-blue-300">
                    Currently scraping: <strong>{progress.current_store}</strong>
                  </AlertDescription>
                </Alert>
              )}
              
              {progress.errors.length > 0 && (
                <Alert className="bg-red-500/10 border-red-500/30">
                  <XCircle className="h-4 w-4" />
                  <AlertDescription className="text-red-300">
                    <div className="font-medium mb-1">Errors encountered:</div>
                    <ul className="text-xs space-y-1">
                      {progress.errors.map((error, index) => (
                        <li key={index}>• {error}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        )}

        {/* Results */}
        {results.length > 0 && (
          <Card className="bg-gray-800/50 border-gray-700">
            <CardHeader>
              <CardTitle className="text-green-400">Scraping Results</CardTitle>
              <CardDescription className="text-gray-400">
                Found {results.length} products across {new Set(results.map(r => r.store_name)).size} stores
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700">
                      <th className="text-left p-2 text-gray-300">Store</th>
                      <th className="text-left p-2 text-gray-300">Product</th>
                      <th className="text-left p-2 text-gray-300">Price</th>
                      <th className="text-left p-2 text-gray-300">Brand</th>
                      <th className="text-left p-2 text-gray-300">Stock</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.slice(0, 50).map((product, index) => (
                      <tr key={index} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                        <td className="p-2 text-gray-300">{product.store_name}</td>
                        <td className="p-2 text-gray-300 max-w-xs truncate" title={product.title}>
                          {product.title}
                        </td>
                        <td className="p-2 text-green-400 font-mono">
                          {product.price ? `${product.currency} ${product.price.toFixed(2)}` : 'N/A'}
                        </td>
                        <td className="p-2 text-gray-400">{product.brand || 'Unknown'}</td>
                        <td className="p-2">
                          <Badge variant={product.in_stock ? 'default' : 'destructive'} className="text-xs">
                            {product.in_stock ? 'In Stock' : 'Out of Stock'}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {results.length > 50 && (
                <div className="text-center mt-4 text-gray-400 text-sm">
                  Showing first 50 results. Total: {results.length} products
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default ScrapingDashboard;