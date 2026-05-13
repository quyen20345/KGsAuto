import { useState } from 'react';
import MarkdownContent from './MarkdownContent';
import ReasoningPanel from './ReasoningPanel';
import EvidencePanel from './EvidencePanel';
import { CopyIcon, CheckIcon, RefreshIcon } from './Icons';

function formatTime(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
}

const modeLabels = {
  semantic_search: 'Semantic',
  graph_search: 'Graph',
  naive_grag: 'Naive GRAG',
  hybrid: 'Hybrid',
};

export default function ChatMessage({ message, onRegenerate }) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';
  const isStreaming = message.role === 'assistant' && !message.content && message.status;
  const isError = message.error;
  const showActions = message.role === 'assistant' && message.content && !message.status;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`chat-message ${message.role}${isError ? ' chat-message-error' : ''}`}>
      <div className="chat-avatar">{isUser ? 'U' : 'KG'}</div>
      <div className="chat-bubble">
        <div className="chat-message-meta">
          <span>{isUser ? 'Bạn' : 'KGsAuto'}{message.mode ? ` · ${modeLabels[message.mode] || message.mode}` : ''}</span>
          <span>{formatTime(message.createdAt)}</span>
        </div>

        {isStreaming && (
          <div className="chat-thinking-dots">
            <span /><span /><span />
          </div>
        )}

        {message.status && !isStreaming && (
          <div className="chat-stream-status">{message.status}</div>
        )}

        {message.role === 'assistant' && message.metadata && <ReasoningPanel metadata={message.metadata} />}

        {message.content && (
          <div className="chat-message-text">
            {isUser ? message.content : <MarkdownContent>{message.content}</MarkdownContent>}
          </div>
        )}

        {message.citations?.length > 0 && (
          <div className="chat-citations">Trích dẫn: {message.citations.join(', ')}</div>
        )}

        <EvidencePanel evidence={message.evidence} />

        {isError && (
          <button className="chat-retry-btn" onClick={() => onRegenerate(message.id)}>Thử lại</button>
        )}

        {showActions && (
          <div className="chat-message-actions">
            <button onClick={handleCopy} title={copied ? 'Đã sao chép' : 'Sao chép'}>
              {copied ? <CheckIcon /> : <CopyIcon />}
            </button>
            {onRegenerate && (
              <button onClick={() => onRegenerate(message.id)} title="Tạo lại">
                <RefreshIcon />
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
