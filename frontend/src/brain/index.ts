import { API_HOST, API_PATH, API_PREFIX_PATH, API_URL, mode, Mode } from "../constants";
import { Brain } from "./Brain";
import type { RequestParams } from "./http-client";

const isLocalhost = /localhost:\d{4}/i.test(window.location.origin);

const constructBaseUrl = (): string => {
  // During vite dev server we proxy /routes -> backend, so use dev origin
  if (mode === Mode.DEV) {
    return `${window.location.origin}`;
  }

  // Prefer explicit API_URL when set to a real remote URL
  if (API_URL && /^https?:\/\//i.test(API_URL) && !/localhost|127\.0\.0\.1/.test(API_URL)) {
    return API_URL;
  }

  // If running from a built app served by the backend, use current origin
  if (typeof window !== 'undefined' && window.location && window.location.origin) {
    return window.location.origin;
  }

  if (API_HOST && API_PREFIX_PATH) {
    return `https://${API_HOST}${API_PREFIX_PATH}`;
  }

  // Final fallback (unused in our deployment)
  return '';
};

type BaseApiParams = Omit<RequestParams, "signal" | "baseUrl" | "cancelToken">;

const constructBaseApiParams = (): BaseApiParams => {
  return {
    credentials: "include",
    secure: true,
  };
};

const constructClient = () => {
  const baseUrl = constructBaseUrl();
  const baseApiParams = constructBaseApiParams();

  return new Brain({
    baseUrl,
    baseApiParams,
    customFetch: (url, options) => {
      return fetch(url, options);
    },
    securityWorker: async () => {
      // No auth header in this environment
      return {};
    },
  });
};

const brain = constructClient();

export default brain;
