import React from 'react';

export const StackHandler: React.FC = () => null;
export const StackProvider: React.FC<{ children?: React.ReactNode }> = ({ children }) => <>{children}</>;
export const StackTheme = {} as const;
export const useStackApp = () => ({ navigate: () => {} });
export const useUser = () => ({ user: null });
export class StackClientApp {}
