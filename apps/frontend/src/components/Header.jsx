import { Link } from 'react-router-dom';
import { useBreadcrumb } from '../context/BreadcrumbContext';
import { useTheme } from '../context/ThemeContext';
import Breadcrumb from './Breadcrumb';

export default function Header() {
  const { breadcrumbs, headerExtra } = useBreadcrumb();
  const { theme, setTheme } = useTheme();

  return (
    <header className="app-header">
      <div style={{ minWidth: '200px' }} />
      <div className="header-center" style={{ display: 'flex', alignItems: 'center', gap: '16px', position: 'relative' }}>
        {breadcrumbs && breadcrumbs.length > 0 ? (
          <Breadcrumb items={breadcrumbs} />
        ) : (
          <Breadcrumb items={[{ label: 'Home', link: '/' }]} />
        )}
        {headerExtra && (
          <>
            <span className="breadcrumb-separator" style={{ margin: 0 }}>|</span>
            <div className="header-extra-action">
              {headerExtra}
            </div>
          </>
        )}
      </div>

      <div className="header-right" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <button 
          onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
          style={{
            background: 'none',
            border: 'none',
            fontSize: '1.2rem',
            cursor: 'pointer',
            padding: '6px',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'var(--transition)',
            outline: 'none',
          }}
          onMouseOver={(e) => e.currentTarget.style.background = 'var(--border)'}
          onMouseOut={(e) => e.currentTarget.style.background = 'none'}
          title={theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
        >
          {theme === 'light' ? '🌙' : '☀️'}
        </button>
        <div className="user-profile">
          <div className="avatar">👤</div>
          <span className="user-name">Admin</span>
        </div>
      </div>
    </header>
  );
}
