function formatReasoningStep(step) {
  if (typeof step === 'string') return { title: 'Lập luận', summary: step };
  if (!step || typeof step !== 'object') return { title: 'Lập luận', summary: String(step ?? '') };
  return {
    title: step.title || 'Lập luận',
    summary: step.summary || step.message || '',
    details: step.details || step.items || null,
  };
}

function ReasoningStep({ step }) {
  const formatted = formatReasoningStep(step);
  const details = Array.isArray(formatted.details) ? formatted.details : formatted.details ? [formatted.details] : [];

  return (
    <li className="chat-reasoning-step">
      <div className="chat-reasoning-title">{formatted.title}</div>
      {formatted.summary && <div>{formatted.summary}</div>}
      {details.length > 0 && (
        <ul className="chat-reasoning-details">
          {details.map((item, index) => <li key={index}>{item}</li>)}
        </ul>
      )}
    </li>
  );
}

export default function ReasoningPanel({ metadata }) {
  const reasoning = metadata?.reasoning_steps;
  const steps = Array.isArray(reasoning) ? reasoning : reasoning ? [reasoning] : [];

  if (steps.length === 0) return null;

  return (
    <details className="chat-reasoning">
      <summary>
        <span>Lập luận</span>
        <span>{steps.length} bước</span>
      </summary>
      <ol className="chat-reasoning-list">
        {steps.map((step, index) => <ReasoningStep key={index} step={step} />)}
      </ol>
    </details>
  );
}
