export default function EmptyState({ icon, title, description, action }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">{icon || '📦'}</div>
      <h3 className="empty-state-title">{title || 'Không có dữ liệu'}</h3>
      <p className="empty-state-description">{description || 'Không tìm thấy kết quả nào phù hợp với yêu cầu của bạn.'}</p>
      {action && <div className="empty-state-action">{action}</div>}
    </div>
  );
}
