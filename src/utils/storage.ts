// Local storage utilities for task management
export const STORAGE_KEYS = {
  LATEST_SCRAPING_TASK_ID: 'priceOptim_latestScrapingTaskId',
  SCRAPING_TASK_HISTORY: 'priceOptim_scrapingTaskHistory'
} as const;

export interface TaskHistory {
  taskId: string;
  startedAt: string;
  status: string;
  productCount?: number;
}

export const StorageUtils = {
  // Task ID management
  setLatestScrapingTaskId: (taskId: string) => {
    localStorage.setItem(STORAGE_KEYS.LATEST_SCRAPING_TASK_ID, taskId);
  },

  getLatestScrapingTaskId: (): string | null => {
    return localStorage.getItem(STORAGE_KEYS.LATEST_SCRAPING_TASK_ID);
  },

  clearLatestScrapingTaskId: () => {
    localStorage.removeItem(STORAGE_KEYS.LATEST_SCRAPING_TASK_ID);
  },

  // Task history management
  addTaskToHistory: (task: TaskHistory) => {
    const existingHistory = StorageUtils.getTaskHistory();
    const updatedHistory = [task, ...existingHistory.slice(0, 9)]; // Keep last 10 tasks
    localStorage.setItem(STORAGE_KEYS.SCRAPING_TASK_HISTORY, JSON.stringify(updatedHistory));
  },

  getTaskHistory: (): TaskHistory[] => {
    const history = localStorage.getItem(STORAGE_KEYS.SCRAPING_TASK_HISTORY);
    return history ? JSON.parse(history) : [];
  },

  updateTaskInHistory: (taskId: string, updates: Partial<TaskHistory>) => {
    const history = StorageUtils.getTaskHistory();
    const updatedHistory = history.map(task => 
      task.taskId === taskId ? { ...task, ...updates } : task
    );
    localStorage.setItem(STORAGE_KEYS.SCRAPING_TASK_HISTORY, JSON.stringify(updatedHistory));
  }
};