import { PlusIcon } from './Icons';

const modeDescriptions = {
  semantic_search: 'Tìm kiếm ngữ nghĩa trong tài liệu markdown',
  graph_search: 'Truy vấn đa bước trên đồ thị tri thức',
  naive_grag: 'Truy vấn đồ thị một bước (nhanh)',
  hybrid: 'Kết hợp tìm kiếm ngữ nghĩa + đồ thị',
};

const modeLabels = {
  semantic_search: 'Semantic',
  graph_search: 'Graph',
  naive_grag: 'Naive GRAG',
  hybrid: 'Hybrid',
};

function formatMode(mode) {
  return modeLabels[mode] || mode;
}

export default function ChatSidebar({ mode, setMode, topK, setTopK, modes, isLoading, onStarterClick, onReset }) {
  const handleTopKChange = (e) => {
    const val = Number(e.target.value);
    if (!Number.isNaN(val)) {
      setTopK(Math.max(1, Math.min(20, val)));
    }
  };

  const handleTopKBlur = (e) => {
    const val = Number(e.target.value);
    if (Number.isNaN(val) || val < 1) setTopK(5);
  };

  const starterPrompts = [
    'Hiệu trưởng là ai?',
    'Trường Đại học Công nghệ có những khoa nào?',
    'Cho tôi biết thông tin tuyển sinh mới nhất.',
  ];

  return (
    <aside className="chat-sidebar">
      <div className="chat-sidebar-header">
        <div className="chat-sidebar-title">KGsAuto Chat</div>
        <button className="chat-new-btn" onClick={onReset} disabled={isLoading} title="Cuộc trò chuyện mới">
          <PlusIcon /> Mới
        </button>
      </div>

      <label className="chat-control">
        <span className="chat-control-label">Chế độ</span>
        <select value={mode} onChange={(e) => setMode(e.target.value)} disabled={isLoading}>
          {modes.map((item) => (
            <option key={item} value={item}>{formatMode(item)}</option>
          ))}
        </select>
        {modeDescriptions[mode] && <span className="chat-control-hint">{modeDescriptions[mode]}</span>}
      </label>

      <label className="chat-control">
        <span className="chat-control-label">Số kết quả</span>
        <input
          type="number"
          min="1"
          max="20"
          value={topK}
          onChange={handleTopKChange}
          onBlur={handleTopKBlur}
          disabled={isLoading}
        />
        <span className="chat-control-hint">Từ 1 đến 20</span>
      </label>

      <div className="chat-starters">
        <div className="chat-control-label">Gợi ý</div>
        {starterPrompts.map((prompt) => (
          <button key={prompt} type="button" onClick={() => onStarterClick(prompt)} disabled={isLoading}>
            {prompt}
          </button>
        ))}
      </div>
    </aside>
  );
}
