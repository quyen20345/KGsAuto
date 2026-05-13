import { useRef, useEffect } from 'react';
import { SendIcon, StopIcon } from './Icons';

export default function ChatComposer({ input, setInput, isLoading, onSend, onAbort }) {
  const textareaRef = useRef(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 160) + 'px';
    }
  }, [input]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="chat-composer">
      <form
        className="chat-composer-form"
        onSubmit={(e) => {
          e.preventDefault();
          onSend();
        }}
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Hỏi về UET, entity, quan hệ, hoặc thông tin trong tài liệu..."
          rows={1}
          disabled={isLoading}
        />
        {isLoading ? (
          <button type="button" className="chat-composer-btn chat-composer-stop" onClick={onAbort} title="Dừng">
            <StopIcon />
          </button>
        ) : (
          <button type="submit" className="chat-composer-btn" disabled={!input.trim()} title="Gửi">
            <SendIcon />
          </button>
        )}
      </form>
      <div className="chat-composer-hint">Enter để gửi · Shift+Enter để xuống dòng</div>
    </div>
  );
}
