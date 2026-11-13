// Static fallback version (overridden at runtime by /health.version). The
// `__APP_VERSION__` define is injected by Vite; it is undefined under test.
export const APP_VERSION: string =
  typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '0.1.0'
