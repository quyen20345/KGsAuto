import { Link, useLocation } from 'react-router-dom';

export default function Sidebar() {
  const location = useLocation();

  const menuItems = [
    { path: '/', label: 'Home', icon: '🏠' },
    { path: '/search', label: 'Entities', icon: '📄' }, // Temporarily points to search
    { path: '/duplicates', label: 'Duplicates', icon: '👯' },
    { path: '/pipeline', label: 'Pipeline', icon: '⚙️' },
    { path: '/developer', label: 'Developer', icon: '🛠️' },
  ];

  return (
    <aside className="app-sidebar">
      <div className="sidebar-header">
        <Link to="/" className="logo">KGsAuto</Link>
      </div>
      <nav className="sidebar-nav">
        {menuItems.map((item, index) => {
          // Special case for Entities pointing to /search: we check if the label matches to distinguish from the real Search menu item.
          // Or we can just use simple active matching if path exactly matches.
          // Since both Search and Entities point to /search, both might highlight. Let's just use simple exact match for now.
          const isActive = location.pathname === item.path || (location.pathname.startsWith('/search') && item.path === '/search');
          
          return (
            <Link 
              key={`${item.path}-${index}`} 
              to={item.path} 
              className={`sidebar-link ${isActive ? 'active' : ''}`}
            >
              <span className="sidebar-icon">{item.icon}</span>
              <span className="sidebar-label">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
