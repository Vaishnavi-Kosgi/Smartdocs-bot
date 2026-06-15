import SourcePanel from './SourcePanel'

const INTENT_LABELS = {
  qa:        'Q&A',
  summarize: 'Summarize',
  explain:   'Explain'
}

function parseMarkdown(text) {
  if (!text) return null;

  const lines = text.split('\n');
  let inList = false;
  const listItems = [];
  const renderedElements = [];

  const parseInline = (str) => {
    const parts = [];
    let lastIndex = 0;
    const regex = /(\*\*.*?\*\*|`.*?`)/g;
    let match;
    
    while ((match = regex.exec(str)) !== null) {
      const matchIndex = match.index;
      const matchText = match[0];
      
      if (matchIndex > lastIndex) {
        parts.push(str.substring(lastIndex, matchIndex));
      }
      
      if (matchText.startsWith('**') && matchText.endsWith('**')) {
        parts.push(<strong key={matchIndex}>{matchText.slice(2, -2)}</strong>);
      } else if (matchText.startsWith('`') && matchText.endsWith('`')) {
        parts.push(<code key={matchIndex}>{matchText.slice(1, -1)}</code>);
      }
      
      lastIndex = regex.lastIndex;
    }
    
    if (lastIndex < str.length) {
      parts.push(str.substring(lastIndex));
    }
    
    return parts.length > 0 ? parts : str;
  };

  lines.forEach((line, index) => {
    const trimmedLine = line.trim();
    
    if (trimmedLine.startsWith('- ') || trimmedLine.startsWith('* ')) {
      if (!inList) {
        inList = true;
      }
      listItems.push(
        <li key={`li-${index}`} className="md-list-item">
          {parseInline(trimmedLine.substring(2))}
        </li>
      );
    } else {
      if (inList) {
        renderedElements.push(
          <ul key={`ul-${index}`} className="md-list">
            {[...listItems]}
          </ul>
        );
        listItems.length = 0;
        inList = false;
      }
      
      if (trimmedLine.startsWith('### ')) {
        renderedElements.push(
          <h3 key={`h3-${index}`} className="md-h3">
            {parseInline(trimmedLine.substring(4))}
          </h3>
        );
      } else if (trimmedLine.startsWith('## ')) {
        renderedElements.push(
          <h2 key={`h2-${index}`} className="md-h2">
            {parseInline(trimmedLine.substring(3))}
          </h2>
        );
      } else if (trimmedLine) {
        renderedElements.push(
          <p key={`p-${index}`} className="md-paragraph">
            {parseInline(line)}
          </p>
        );
      } else {
        renderedElements.push(<div key={`spacer-${index}`} className="md-spacer" />);
      }
    }
  });

  if (inList) {
    renderedElements.push(
      <ul key="ul-end" className="md-list">
        {[...listItems]}
      </ul>
    );
  }

  return renderedElements;
}

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`message-row ${isUser ? 'user' : 'ai'}`} id={`message-${message.id}`}>
      <div className={`message-avatar ${isUser ? 'user' : 'ai'}`}>
        {isUser ? '👤' : '🤖'}
      </div>

      <div className="message-body">
        <div className="message-meta">
          <span className="message-sender">{isUser ? 'You' : 'SmartDocs AI'}</span>
          {!isUser && message.intent && (
            <span className={`intent-badge ${message.intent}`}>
              {INTENT_LABELS[message.intent] || message.intent}
            </span>
          )}
        </div>

        {message.isTyping ? (
          <div className="typing-indicator">
            <div className="typing-dot" />
            <div className="typing-dot" />
            <div className="typing-dot" />
          </div>
        ) : (
          <>
            <div className={`bubble ${isUser ? 'user' : 'ai'}`}>
              {isUser ? message.content : parseMarkdown(message.content)}
            </div>

            {!isUser && message.sources && (
              <SourcePanel sources={message.sources} />
            )}
          </>
        )}
      </div>
    </div>
  )
}
