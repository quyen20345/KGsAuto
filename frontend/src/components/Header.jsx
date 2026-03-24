// src/components/Header.jsx
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

export default function Header() {
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  const doSearch = () => {
    if (searchQuery.trim()) {
      navigate(`/search/${encodeURIComponent(searchQuery)}`);
      setSearchQuery(''); // Xóa ô search sau khi tìm
    }
  };

  return (
    <header>
      <Link to="/" className="logo">KGsAuto KB</Link>
      <nav>
        <Link to="/">Browse</Link>
        <Link to="/visualize">Visualize Graph</Link>
        <Link to="/query">Query Cypher</Link>
      </nav>
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
    </header>
  );
}