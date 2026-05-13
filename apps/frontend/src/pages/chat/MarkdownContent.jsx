import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function MarkdownContent({ children }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        a: (props) => <a {...props} target="_blank" rel="noreferrer" />,
        code: ({ inline, children: codeChildren, ...props }) =>
          inline
            ? <code className="chat-code-inline" {...props}>{codeChildren}</code>
            : <pre className="chat-code-block"><code {...props}>{codeChildren}</code></pre>,
        table: (props) => <div className="chat-table-wrap"><table {...props} /></div>,
      }}
    >
      {children || ''}
    </ReactMarkdown>
  );
}
