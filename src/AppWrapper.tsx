import { RouterProvider } from "react-router-dom";
import { Head } from "../frontend/src/internal-components/Head";
import { OuterErrorBoundary } from "../frontend/src/prod-components/OuterErrorBoundary";
import { router } from "./router";
import { ThemeProvider } from "../frontend/src/internal-components/ThemeProvider";
import { DEFAULT_THEME } from "../frontend/src/constants/default-theme";

export const AppWrapper = () => {
  return (
    <OuterErrorBoundary>
      <ThemeProvider defaultTheme={DEFAULT_THEME}>
        <RouterProvider router={router} />
        <Head />
      </ThemeProvider>
    </OuterErrorBoundary>
  );
};

