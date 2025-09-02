import React from 'react';

export const auth = {
  getAuthHeaderValue: async (): Promise<string> => "",
};

export const StackHandlerRoutes: React.FC = () => null;
export const LoginRedirect: React.FC = () => null;
export const UserGuard: React.FC<{ children?: React.ReactNode }> = ({ children }) => <>{children}</>;

