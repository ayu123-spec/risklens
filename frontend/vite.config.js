import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite is the build tool / dev server. This config does two things:
//  1. Enables React (JSX) support.
//  2. Proxies any request starting with /api to your backend on port 8000.
//     This means the frontend can call "/api/credit-risk" and Vite forwards it
//     to http://127.0.0.1:8000/api/credit-risk behind the scenes. It avoids
//     browser CORS headaches during development.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
