import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './context/AuthContext';
import { initializeFuelColors } from './utils/fuelColors';
import HomePage from './pages/HomePage';
import CountryDashboard from './pages/CountryDashboard';
import LoginPage from './pages/LoginPage';
import DocumentationPage from './pages/DocumentationPage';


// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  // Initialize fuel colors when app starts
  useEffect(() => {
    const initColors = async () => {
      try {
        await initializeFuelColors();
        console.log('✅ Fuel colors initialized successfully');
      } catch (error) {
        console.error('❌ Failed to initialize fuel colors:', error);
        // Don't throw error - app should still work with default colors
      }
    };
    
    initColors();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router>
          <div className="App">
            <main>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/country/:isoCode" element={<CountryDashboard />} />
                <Route path="/docs" element={<DocumentationPage />} />

                
                {/* Placeholder routes */}
                <Route path="/explore" element={<HomePage />} />
                <Route path="/about" element={<PlaceholderPage title="About" />} />
                <Route path="/register" element={<PlaceholderPage title="Register" />} />
                
                {/* 404 Route */}
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </main>
            
            {/* Toast notifications */}
            <Toaster
              position="top-right"
              toastOptions={{
                duration: 4000,
                style: {
                  background: '#363636',
                  color: '#fff',
                },
                success: {
                  style: {
                    background: '#00D4AA',
                  },
                },
                error: {
                  style: {
                    background: '#EF4444',
                  },
                },
              }}
            />
          </div>
        </Router>
      </AuthProvider>
    </QueryClientProvider>
  );
}

// Placeholder page component for unimplemented routes
const PlaceholderPage = ({ title }) => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50">
    <div className="text-center">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">{title}</h1>
      <p className="text-xl text-gray-600 mb-8">This page is coming soon!</p>
      <a
        href="/"
        className="btn-primary"
      >
        Return Home
      </a>
    </div>
  </div>
);

// 404 page component
const NotFoundPage = () => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50">
    <div className="text-center">
      <h1 className="text-6xl font-bold text-gray-900 mb-4">404</h1>
      <h2 className="text-2xl font-semibold text-gray-700 mb-4">Page Not Found</h2>
      <p className="text-xl text-gray-600 mb-8">
        The page you're looking for doesn't exist.
      </p>
      <a
        href="/"
        className="btn-primary"
      >
        Return Home
      </a>
    </div>
  </div>
);

export default App;
