import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';

export default function Header() {
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();
  const location = useLocation();
  const isChat = location.pathname === '/chat';

  const doSearch = () => {
    if (searchQuery.trim()) {
      navigate(`/search/${encodeURIComponent(searchQuery)}`);
      setSearchQuery('');
    }
  };

  return (
    <header>
      <Link to="/" className="logo">UETKB</Link>
      <nav>
        <Link to="/">Home</Link>
        <Link to="/search">Search</Link>
        <Link to="/chat">Chat</Link>
        <Link to="/pipeline">Pipeline</Link>
        <Link to="/merge">Merge</Link>
      </nav>
      {!isChat && (
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search entity..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && doSearch()}
          />
          <button onClick={doSearch}>🔍</button>
        </div>
      )}
    </header>
  );
}
