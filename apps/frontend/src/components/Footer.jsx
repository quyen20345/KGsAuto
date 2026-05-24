import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="app-footer">
      <div className="footer-content">
        <div className="footer-section">
          <h4>UETKB</h4>
          <p>Hệ thống Cơ sở Tri thức & Hỏi đáp thông minh dành cho giáo dục, được xây dựng dựa trên công nghệ Đồ thị Tri thức (Knowledge Graph) và LLM.</p>
        </div>
        
        <div className="footer-section">
          <h4>Quick Links</h4>
          <ul>
            <li><Link to="/">Trang chủ</Link></li>
            <li><Link to="/search">Tìm kiếm</Link></li>
            <li><Link to="/chat">Trợ lý AI (Chat)</Link></li>
            <li><Link to="/pipeline">Quản lý Pipeline</Link></li>
          </ul>
        </div>
        
        <div className="footer-section">
          <h4>Developer Services</h4>
          <ul>
            <li><a href="http://localhost:7474/browser/" target="_blank" rel="noopener noreferrer">Neo4j Browser</a></li>
            <li><a href="http://localhost:6333/dashboard" target="_blank" rel="noopener noreferrer">Qdrant Dashboard</a></li>
            <li><a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">Graph API Docs</a></li>
            <li><a href="http://localhost:8001/docs" target="_blank" rel="noopener noreferrer">Pipeline API Docs</a></li>
          </ul>
        </div>
      </div>
      <div className="footer-bottom">
        <p>&copy; {new Date().getFullYear()} UET Knowledge Base. All rights reserved.</p>
      </div>
    </footer>
  );
}
