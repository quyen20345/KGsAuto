import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../../services/api';
import ChatSidebar from './ChatSidebar';
import ChatComposer from './ChatComposer';
import ChatMessage from './ChatMessage';
import EmptyState from './EmptyState';
import { ScrollDownIcon } from './Icons';
import { useBreadcrumb } from '../../context/BreadcrumbContext';
import './chat.css';

const modeLabels = {
  semantic_search: 'Semantic',
  graph_search: 'Graph',
  naive_grag: 'Naive GRAG',
  hybrid: 'Hybrid',
};

export default function Chat() {
  const { setBreadcrumbs } = useBreadcrumb();

  useEffect(() => {
    setBreadcrumbs([
      { label: 'Home', link: '/' },
      { label: 'Chat RAG', link: null }
    ]);
  }, [setBreadcrumbs]);

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [mode, setMode] = useState('semantic_search');
  const [topK, setTopK] = useState(5);
  const [modes, setModes] = useState(['semantic_search', 'graph_search', 'naive_grag', 'hybrid']);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  const listRef = useRef(null);
  const abortRef = useRef(null);
  const [conversationId] = useState(() => `web-${Date.now()}`);
  const conversationIdRef = useRef(conversationId);
  const isAtBottomRef = useRef(true);

  useEffect(() => {
    api.getChatModes()
      .then((data) => {
        if (data.modes) setModes(data.modes);
        if (data.default_mode) setMode(data.default_mode);
      })
      .catch(() => {});
  }, []);

  const scrollToBottom = useCallback(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, []);

  useEffect(() => {
    if (isAtBottomRef.current) scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  const handleScroll = () => {
    const el = listRef.current;
    if (!el) return;
    const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 80;
    isAtBottomRef.current = atBottom;
    setShowScrollBtn(!atBottom);
  };

  const sendMessage = async (text = input) => {
    const content = text.trim();
    if (!content || isLoading) return;

    setError('');
    setInput('');
    const userMessage = { id: crypto.randomUUID(), role: 'user', content, createdAt: Date.now() };
    const assistantId = crypto.randomUUID();
    const placeholder = {
      id: assistantId,
      role: 'assistant',
      content: '',
      mode,
      citations: [],
      evidence: null,
      metadata: { reasoning_steps: [] },
      status: 'Đang chuẩn bị...',
      createdAt: Date.now(),
    };

    setMessages((prev) => [...prev, userMessage, placeholder]);
    setIsLoading(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await api.streamChatMessage({
        message: content,
        mode,
        topK: Number(topK),
        includeEvidence: true,
        conversationId: conversationIdRef.current,
        signal: controller.signal,
        onEvent: (event) => {
          const token = event.choices?.[0]?.delta?.content || '';
          const reasoningStep = event.kgsauto?.reasoning_step;
          const finalMetadata = event.kgsauto?.metadata;
          const status = event.kgsauto?.status?.message;

          setMessages((prev) => prev.map((item) => {
            if (item.id !== assistantId) return item;
            const reasoningSteps = item.metadata?.reasoning_steps || [];
            return {
              ...item,
              content: token ? item.content + token : item.content,
              status: status || (token ? '' : item.status),
              citations: event.kgsauto?.citations || item.citations,
              evidence: event.kgsauto?.evidence || item.evidence,
              metadata: finalMetadata || {
                ...item.metadata,
                reasoning_steps: reasoningStep === undefined ? reasoningSteps : [...reasoningSteps, reasoningStep],
              },
            };
          }));
        },
      });

      setMessages((prev) => prev.map((item) => (
        item.id === assistantId
          ? { ...item, status: '', content: item.content || 'Không có câu trả lời.' }
          : item
      )));
    } catch (err) {
      if (err.name === 'AbortError') {
        setMessages((prev) => prev.map((item) => (
          item.id === assistantId ? { ...item, status: '' } : item
        )));
      } else {
        setError(err.message || 'Lỗi kết nối.');
        setMessages((prev) => prev.map((item) => (
          item.id === assistantId
            ? { ...item, status: '', error: true, content: item.content || 'Lỗi kết nối hoặc backend chưa sẵn sàng.' }
            : item
        )));
      }
    } finally {
      abortRef.current = null;
      setIsLoading(false);
    }
  };

  const handleAbort = () => {
    abortRef.current?.abort();
  };

  const regenerate = (messageId) => {
    const idx = messages.findIndex((m) => m.id === messageId);
    if (idx < 1) return;
    const userMsg = messages.slice(0, idx).reverse().find((m) => m.role === 'user');
    if (!userMsg) return;
    setMessages((prev) => prev.filter((m) => m.id !== messageId));
    sendMessage(userMsg.content);
  };

  const resetConversation = () => {
    setMessages([]);
    setError('');
    conversationIdRef.current = `web-${Date.now()}`;
  };

  const statusText = isLoading
    ? `Đang xử lý · ${modeLabels[mode] || mode}`
    : 'Sẵn sàng';

  return (
    <main className="chat-shell">
      <ChatSidebar
        mode={mode}
        setMode={setMode}
        topK={topK}
        setTopK={setTopK}
        modes={modes}
        isLoading={isLoading}
        onStarterClick={sendMessage}
        onReset={resetConversation}
      />

      <section className="chat-panel">
        <div className="chat-panel-header">
          <div>
            <h2 className="chat-panel-title">Chat với Knowledge Graph</h2>
            <p className="chat-panel-subtitle">Hỏi đáp đa chế độ: semantic, graph, GRAG, hybrid.</p>
          </div>
          <span className={`chat-status${isLoading ? ' chat-status-active' : ''}`}>{statusText}</span>
        </div>

        <div ref={listRef} className="chat-messages" onScroll={handleScroll}>
          {messages.length === 0 ? (
            <EmptyState onStarterClick={sendMessage} />
          ) : (
            messages.map((message) => (
              <ChatMessage key={message.id} message={message} onRegenerate={regenerate} />
            ))
          )}
        </div>

        {showScrollBtn && (
          <button className="chat-scroll-btn" onClick={scrollToBottom} title="Cuộn xuống">
            <ScrollDownIcon />
          </button>
        )}

        {error && <div className="chat-error">{error}</div>}

        <ChatComposer
          input={input}
          setInput={setInput}
          isLoading={isLoading}
          onSend={() => sendMessage()}
          onAbort={handleAbort}
        />
      </section>
    </main>
  );
}
