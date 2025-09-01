import { lazy, type ReactNode, Suspense } from "react";
import { createBrowserRouter, Outlet } from "react-router-dom";
import { AppProvider } from "../frontend/src/components/AppProvider";

export const SuspenseWrapper = ({ children }: { children: ReactNode }) => {
  return <Suspense>{children}</Suspense>;
};

const App = lazy(() => import("./pages/App"));
const CompetitiveAnalysis = lazy(() => import("./pages/CompetitiveAnalysis"));
const PricingRecommendations = lazy(() => import("./pages/PricingRecommendations"));
const Scraping = lazy(() => import("./pages/Scraping"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));
const SomethingWentWrongPage = lazy(() => import("./pages/SomethingWentWrongPage"));

export const router = createBrowserRouter([
  {
    element: (
      <AppProvider>
        <SuspenseWrapper>
          <Outlet />
        </SuspenseWrapper>
      </AppProvider>
    ),
    children: [
      { path: "/", element: <App /> },
      { path: "/competitive-analysis", element: <CompetitiveAnalysis /> },
      { path: "/pricing-recommendations", element: <PricingRecommendations /> },
      { path: "/scraping", element: <Scraping /> }
    ]
  },
  {
    path: "*",
    element: (
      <SuspenseWrapper>
        <NotFoundPage />
      </SuspenseWrapper>
    ),
    errorElement: (
      <SuspenseWrapper>
        <SomethingWentWrongPage />
      </SuspenseWrapper>
    ),
  },
]);