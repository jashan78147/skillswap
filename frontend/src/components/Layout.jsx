/* ==========================================================================
   Layout.jsx -- the navigation shell wrapped around every signed-in page.
   ========================================================================== */

import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../auth';
import { Avatar } from './ui';

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [pending, setPending] = useState(0);

  /* Live count of requests waiting on a reply, shown on the Requests tab.
     Re-checked whenever you change page, so it stays current.            */
  useEffect(() => {
    let cancelled = false;
    api
      .get('/api/swaps?box=incoming&status=pending')
      .then((rows) => { if (!cancelled) setPending(rows.length); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [location.pathname]);

  return (
    <>
      <nav className="nav">
        <div className="nav-inner">
          <Link to="/dashboard" className="brand">
            <span className="brand-mark">⇄</span>
            SkillSwap
          </Link>

          <div className="nav-links">
            <NavLink to="/dashboard" className="nav-link">Dashboard</NavLink>
            <NavLink to="/browse" className="nav-link">Browse</NavLink>
            <NavLink to="/matches" className="nav-link">Matches</NavLink>
            <NavLink to="/requests" className="nav-link">
              Requests
              {pending > 0 && <span className="nav-count">{pending}</span>}
            </NavLink>
            <NavLink to="/ratings" className="nav-link">Ratings</NavLink>
            {/* Only rendered for admins. The server enforces this too --
                hiding the link is a convenience, not the security.      */}
            {user?.is_admin && <NavLink to="/admin" className="nav-link">Admin</NavLink>}
          </div>

          <div className="row">
            <Link to="/profile" className="row" style={{ color: 'inherit' }}>
              <Avatar name={user?.name} url={user?.avatar_url} size="avatar-sm" />
            </Link>
            <button className="btn btn-ghost btn-sm" onClick={logout}>Sign out</button>
          </div>
        </div>
      </nav>

      {/* <Outlet /> is where react-router drops the current page. */}
      <Outlet />
    </>
  );
}
