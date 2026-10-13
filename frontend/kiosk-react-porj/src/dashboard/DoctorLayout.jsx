import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from './AuthContext.jsx';
import './doctor.css';

export default function DoctorLayout() {
  const { doctor, logout } = useAuth();

  const linkClass = ({ isActive }) => `dr-nav-link${isActive ? ' dr-nav-link--active' : ''}`;

  return (
    <div className="dr-shell">
      <aside className="dr-sidebar">
        <div className="dr-sidebar-head">
          <p className="dr-sidebar-name">{doctor.name}</p>
          {doctor.department && <p className="dr-sidebar-dept">{doctor.department}</p>}
        </div>

        <nav className="dr-nav">
          <NavLink to="/dr" end className={linkClass}>
            Current tokens
          </NavLink>
          <NavLink to="/dr/history" className={linkClass}>
            History
          </NavLink>
          <NavLink to="/dr/profile" className={linkClass}>
            Profile
          </NavLink>
        </nav>

        <button type="button" className="dr-logout" onClick={logout}>
          Log out
        </button>
      </aside>

      <main className="dr-main">
        <Outlet />
      </main>
    </div>
  );
}