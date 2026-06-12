/**
 * ============================================================================
 * File: main.jsx
 * Project: Lead Contact Generator
 * Description: 
 * The primary React entry point. This file bridges the React application 
 * to the raw HTML DOM. 
 * * Key Responsibilities:
 * - Mounts the <App /> component into the 'root' HTML div.
 * - Wraps the application in <React.StrictMode> to highlight potential 
 * problems and deprecations during local development.
 * - Imports the global CSS stylesheets (like Tailwind directives).
 * ============================================================================
 */
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)