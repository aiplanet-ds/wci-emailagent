import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { Inbox } from './pages/Inbox';
import { Dashboard } from './pages/Dashboard';
import { useCurrentUser } from './hooks/useEmails';

function App() {
  const { data: user } = useCurrentUser();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (user && !user.authenticated) {
      window.location.href = 'http://localhost:8000/login';
    }
  }, [user]);

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (!user.authenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Not Authenticated</h2>
          <p className="text-gray-600 mb-4">Please log in to continue</p>
          <a
            href="http://localhost:8000/login"
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Log In
          </a>
        </div>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <DashboardLayout>
        <Routes>
          <Route path="/" element={<Navigate to="/inbox" replace />} />
          <Route path="/inbox" element={<Inbox />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </DashboardLayout>
    </BrowserRouter>
  );
}

export default App;
