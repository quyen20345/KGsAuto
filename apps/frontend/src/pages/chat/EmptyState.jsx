export default function EmptyState({ onStarterClick }) {
  const starters = [
    { text: 'Hiệu trưởng là ai?', desc: 'Tìm thông tin lãnh đạo trường' },
    { text: 'Trường Đại học Công nghệ có những khoa nào?', desc: 'Khám phá cấu trúc tổ chức' },
    { text: 'Cho tôi biết thông tin tuyển sinh mới nhất.', desc: 'Tra cứu dữ liệu tuyển sinh' },
  ];

  return (
    <div className="chat-empty">
      <div className="chat-empty-logo">KGsAuto</div>
      <p className="chat-empty-tagline">Hỏi đáp về tri thức UET dựa trên Knowledge Graph</p>
      <div className="chat-empty-grid">
        {starters.map((item) => (
          <button key={item.text} className="chat-empty-card" onClick={() => onStarterClick(item.text)}>
            <span className="chat-empty-card-text">{item.text}</span>
            <span className="chat-empty-card-desc">{item.desc}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
