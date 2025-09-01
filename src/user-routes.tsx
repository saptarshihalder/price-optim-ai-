@@ .. @@
 import { lazy } from "react";
 import type { RouteObject } from "react-router-dom";
-import { UserGuard } from "app/auth";
+import { UserGuard } from "../frontend/src/app/auth";
 
-const App = lazy(() => import("./pages/App"));
+const App = lazy(() => import("../frontend/src/pages/App"));
 const PricingRecommendations = lazy(() => import("./pages/PricingRecommendations"));
 const CompetitiveAnalysis = lazy(() => import("./pages/CompetitiveAnalysis"));
 const Scraping = lazy(() => import("./pages/Scraping"));