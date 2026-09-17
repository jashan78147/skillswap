/* ==========================================================================
   App.jsx -- the routing map.
   --------------------------------------------------------------------------
   Which URL shows which page, and which pages require a login.
   ========================================================================== */

import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth';
import Layout from './components/Layout';
import { Loading } from './components/ui';

import Admin from './pages/Admin';
import Browse from './pages/Browse';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Matches from './pages/Matches';
import Profile from './pages/Profile';
import ProfileSetup from './pages/ProfileSetup';
import Ratings from './pages/Ratings';
import Requests from './pages/Requests';
import Signup from './pages/Signup';
import UserProfile from './pages/UserProfile';

/**
 * Wraps any page that requires a login.
 *
 * NOTE: this is convenience, not security. The real protection is the
 * backend returning 401. Someone who edits this in their browser still
 * gets nothing back from the API.
 */
function ProtectedRoute({ children, adminOnly = false }) {
  const { user, loading } = useAuth();

  // Still checking the saved token -- show a spinner rather than flashing
  // the login screen at someone who is actually signed in.
  if (loading) return <Loading label="Checking your session…" />;
  if (!user) return <Navigate to="/login" replace />;
  if (adminOnly && !user.is_admin) return <Navigate to="/dashboard" replace />;

  return children;
}

/** If you are already signed in, the login page should not show. */
function PublicOnly({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  if (user) return <Navigate to="/dashboard" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      {/* --- signed-out pages --- */}
      <Route path="/login"  element={<PublicOnly><Login /></PublicOnly>} />
      <Route path="/signup" element={<PublicOnly><Signup /></PublicOnly>} />

      {/* Profile setup is signed-in but deliberately OUTSIDE the nav shell,
          matching the full-screen step in the reference design. */}
      <Route
        path="/profile-setup"
        element={<ProtectedRoute><ProfileSetup /></ProtectedRoute>}
      />

      {/* --- signed-in pages, all sharing the nav bar --- */}
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/dashboard"   element={<Dashboard />} />
        <Route path="/browse"      element={<Browse />} />
        <Route path="/matches"     element={<Matches />} />
        <Route path="/requests"    element={<Requests />} />
        <Route path="/ratings"     element={<Ratings />} />
        <Route path="/profile"     element={<Profile />} />
        <Route path="/users/:id"   element={<UserProfile />} />
        <Route path="/admin"       element={<ProtectedRoute adminOnly><Admin /></ProtectedRoute>} />
      </Route>

      {/* Anything unrecognised goes to the dashboard. */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
