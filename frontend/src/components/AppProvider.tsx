
import type { ReactNode } from "react";
import { Toaster } from "@/components/ui/sonner";

interface Props {
  children: ReactNode;
}

/**
 * A provider wrapping the whole app.
 *
 * You can add multiple providers here by nesting them,
 * and they will all be applied to the app.
 *
 * Note: ThemeProvider is already included in AppWrapper.tsx and does not need to be added here.
 */
export const AppProvider = ({ children }: Props) => {
  return (
    <>
      {children}
      <Toaster 
        theme="dark"
        position="bottom-right"
        toastOptions={{
          style: {
            background: 'rgb(30 41 59 / 0.9)',
            border: '1px solid rgb(52 211 153 / 0.3)',
            color: 'rgb(226 232 240)',
          },
        }}
      />
    </>
  );
};
