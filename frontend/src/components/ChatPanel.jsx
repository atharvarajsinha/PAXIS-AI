import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { APP_NAME } from './BrandMark.jsx';
import { AssistantIcon, PlusIcon, ProfileIcon, SendIcon } from './icons.jsx';

function CodeBlock({ language, children }) {
  const code = String(children).replace(/\n$/, '');

  return (
    <div className="codeBlock">
      <SyntaxHighlighter
        style={oneDark}
        language={language || 'text'}
        PreTag="div"
        customStyle={{
          margin: 0,
          borderRadius: 0,
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}

const markdownComponents = {
  code({ inline, className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || '');

    if (!inline) {
      return <CodeBlock language={match?.[1]}>{children}</CodeBlock>;
    }

    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  },
};

function TypingDots() {
  return (
    <span className="typingDots" aria-hidden="true">
      <span />
      <span />
      <span />
    </span>
  );
}

export default function ChatPanel({ messages, onSend, onClear, loading, statusText, error }) {
  const [text, setText] = useState('');
  const endRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading, statusText]);

  // Put the cursor back in the composer the moment the assistant is done.
  useEffect(() => {
    if (!loading) inputRef.current?.focus();
  }, [loading]);

  const submit = (event) => {
    event.preventDefault();

    if (text.trim() && !loading) {
      onSend(text.trim());
      setText('');
    }
  };

  const asText = (content) => (typeof content === 'string' ? content : JSON.stringify(content));

  return (
    <section className="chatCard">
      <div className="panelHeader">
        <div>
          <h2>{APP_NAME}</h2>
          <p>
            <span className={`onlineDot ${loading ? 'busy' : ''}`} />
            {loading ? 'Replying...' : 'Online'}
          </p>
        </div>

        <button
          className="ghostBtn hide-on-print"
          onClick={onClear}
          disabled={loading}
          title={loading ? 'Wait for the current reply to finish' : 'Start a new chat'}
        >
          <PlusIcon size={18} strokeWidth={2} />
          <span>New chat</span>
        </button>
      </div>

      <div className="messages">
        {messages.map((m) => (
          <div className={`messageRow ${m.role}`} key={m.id}>
            <div className="bubbleAvatar">
              {m.role === 'assistant' ? (
                <AssistantIcon size={20} strokeWidth={2} />
              ) : (
                <ProfileIcon size={20} strokeWidth={2} />
              )}
            </div>

            <div className="bubble">
              {m.role === 'assistant' ? (
                <ReactMarkdown components={markdownComponents}>{asText(m.content)}</ReactMarkdown>
              ) : (
                <div className="userMessage">{asText(m.content)}</div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="messageRow assistant">
            <div className="bubbleAvatar">
              <AssistantIcon size={20} strokeWidth={2} />
            </div>

            <div className="bubble typingBubble" role="status" aria-live="polite">
              <TypingDots />
              <span>{statusText || 'Creating your roadmap...'}</span>
            </div>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {error && <div className="errorBox">{error}</div>}

      <form className="composer" onSubmit={submit}>
        <input
          ref={inputRef}
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={loading}
          placeholder={loading ? `${APP_NAME} is replying...` : 'Type your message...'}
          aria-label="Message"
        />

        <button disabled={loading || !text.trim()} aria-label="Send message">
          <SendIcon size={16} />
          <span>Send</span>
        </button>
      </form>
    </section>
  );
}
