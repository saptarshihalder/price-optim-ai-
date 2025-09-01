import React, { useState, useEffect } from 'react';
import { brain } from 'brain';
import { ScrapingProgress, ScrapingResults } from 'types';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Search, CheckCircle, XCircle, Clock, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';

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
      setProgress(null);
      
      // Make actual API call to backend
      const response = await brain.start_scraping({
        target_products: targetProducts,
        max_products_per_store: 15
      });

      const data = response.data;
      setTaskId(data.task_id);
      
      // Store task ID in localStorage for later retrieval
      StorageUtils.setLatestScrapingTaskId(data.task_id);
      StorageUtils.addTaskToHistory({
        taskId: data.task_id,
        startedAt: new Date().toISOString(),
        status: data.status
      });
      
      toast.success('Scraping started successfully!');
      
    } catch (error) {
      console.error('Error starting scraping:', error);
      toast.error('Failed to start scraping');
      setIsLoading(false);
    }
  };

  // Poll for progress updates
  useEffect(() => {
    if (!taskId || !isLoading) return;

    const pollProgress = async () => {
      try {
        const response = await brain.get_scraping_progress(taskId);
        const progressData = response.data;
        setProgress(progressData);

        // Update task history
        StorageUtils.updateTaskInHistory(taskId, {
          status: progressData.status,
          productCount: progressData.products_found
        });

        if (progressData.status === ScrapingStatus.Completed) {
          // Fetch results
          try {
            const resultsResponse = await brain.get_scraping_results(taskId);
            const resultsData = resultsResponse.data;
            setResults(resultsData);
            setIsLoading(false);
            toast.success(`Scraping completed! Found ${resultsData.length} products.`);
          } catch (resultsError) {
            console.error('Error fetching results:', resultsError);
            toast.error('Scraping completed but failed to fetch results');
            setIsLoading(false);
          }
        } else if (progressData.status === ScrapingStatus.Failed) {
          setIsLoading(false);
          toast.error('Scraping failed. Check the error logs.');
        }
      } catch (error) {
        console.error('Error polling progress:', error);
        // Don't show error toast for polling failures as they're frequent
      }
    };

    // Poll immediately, then every 3 seconds
    pollProgress();
    const interval = setInterval(pollProgress, 3000);
    return () => clearInterval(interval);
  }, [taskId, isLoading]);

  // Load existing task on component mount
  useEffect(() => {
    const existingTaskId = StorageUtils.getLatestScrapingTaskId();
    if (existingTaskId) {
      setTaskId(existingTaskId);
      // Try to get the current status
      brain.get_scraping_progress(existingTaskId)
        .then(response => {
          const progressData = response.data;
          setProgress(progressData);
          
          if (progressData.status === ScrapingStatus.Completed) {
            // Also fetch results if completed
            brain.get_scraping_results(existingTaskId)
              .then(resultsResponse => {
                setResults(resultsResponse.data);
              })
              .catch(error => {
                console.error('Error loading existing results:', error);
              });
          } else if (progressData.status === ScrapingStatus.Running) {
            setIsLoading(true);
          }
        })
        .catch(error => {
          console.error('Error loading existing task progress:', error);
          // Clear invalid task ID
          StorageUtils.clearLatestScrapingTaskId();
        });
    }
  }, []);

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

            {/* Task History */}
            {StorageUtils.getTaskHistory().length > 0 && (
              <div className="border-t border-gray-700 pt-4">
                <div className="text-sm font-medium text-gray-300 mb-2">Recent Tasks</div>
                <div className="space-y-2">
                  {StorageUtils.getTaskHistory().slice(0, 3).map((task) => (
                    <div key={task.taskId} className="flex items-center justify-between text-xs text-gray-400 bg-gray-700/30 p-2 rounded">
                      <span>{task.taskId}</span>
                      <div className="flex items-center gap-2">
                        <Badge className={getStatusColor(task.status)}>
                          {task.status}
                        </Badge>
                        {task.productCount && <span>{task.productCount} products</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
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
                      <th className="text-left p-2 text-gray-300">Match Score</th>
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
                        <td className="p-2">
                          {product.match_score && (
                            <div className="flex items-center gap-2">
                              <Progress value={product.match_score * 100} className="w-16 h-2" />
                              <span className="text-xs text-blue-400">{(product.match_score * 100).toFixed(0)}%</span>
                            </div>
                          )}
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