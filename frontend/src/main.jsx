/* ==========================================================================
   main.jsx -- the very first file the browser runs.
   --------------------------------------------------------------------------
   It finds the <div id="root"> in index.html and tells React to render the
   whole app inside it. Everything else hangs off this.
   ========================================================================== */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import App from './App';
import { AuthProvider } from './auth';
import './index.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {/* BrowserRouter enables URL-based pages.
        AuthProvider makes the signed-in user available everywhere. */}
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);
