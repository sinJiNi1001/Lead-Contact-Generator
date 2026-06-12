/**
 * ============================================================================
 * File: vite.config.js
 * Project: Lead Contact Generator
 * Description: 
 * The configuration file for Vite, the frontend build tool and development 
 * server. It optimizes how the React code is compiled for production and 
 * served during local development.
 * * Key Responsibilities:
 * - Registers the @vitejs/plugin-react to enable JSX and Fast Refresh.
 * - Configures the local development server (e.g., setting the host/port).
 * - Manages the build process, outputting the optimized, minified static 
 * assets into the `dist/` directory for Nginx to serve in production.
 * ============================================================================
 */
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})