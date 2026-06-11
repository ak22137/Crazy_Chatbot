'use client';

import React, { useState } from 'react';
import { Message, SQLResult } from '@/types';

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const [sqlExpanded, setSqlExpanded] = useState(false);
  const isUser = message.role === 'user';

  return (
    <div className="message">
      <div className={`message-avatar ${message.role}`}>
        {isUser ? '👤' : '⚡'}
      </div>
      <div className="message-body">
        <div className="message-content">
          {message.isStreaming && !message.content ? (
            <div className="typing-indicator">
              <div className="typing-dot" />
              <div className="typing-dot" />
              <div className="typing-dot" />
            </div>
          ) : (
            <MessageText text={message.content} />
          )}
        </div>

        {/* SQL Result Card */}
        {message.sqlResult && message.sqlResult.success && (
          <div className="sql-card">
            <div className="sql-card-header" onClick={() => setSqlExpanded(!sqlExpanded)}>
              <span className="sql-card-label">
                SQL Query • {message.sqlResult.row_count} row{message.sqlResult.row_count !== 1 ? 's' : ''} • {message.sqlResult.execution_time_ms}ms
              </span>
              <span className={`sql-card-toggle ${sqlExpanded ? 'open' : ''}`}>▼</span>
            </div>
            {sqlExpanded && (
              <div className="sql-card-body">
                <pre className="sql-code">{message.sqlResult.sql}</pre>
              </div>
            )}
            {message.sqlResult.columns.length > 0 && message.sqlResult.rows.length > 0 && (
              <div className="data-table-wrapper">
                <ResultTable result={message.sqlResult} />
              </div>
            )}
          </div>
        )}

        {/* Metadata */}
        {!isUser && (
          <div className="message-meta">
            {message.intent && (
              <span className={`badge ${
                message.intent === 'SQL_ANALYTICS' ? 'badge-info' :
                message.intent === 'METADATA' ? 'badge-warning' : 'badge-success'
              }`}>
                {message.intent}
              </span>
            )}
            {message.processingTimeMs && (
              <span>{Math.round(message.processingTimeMs)}ms</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function MessageText({ text }: { text: string }) {
  // Very basic markdown-like rendering
  const paragraphs = text.split('\n\n');
  return (
    <>
      {paragraphs.map((p, i) => {
        if (p.startsWith('- ') || p.startsWith('* ')) {
          const items = p.split('\n').filter(Boolean);
          return (
            <ul key={i}>
              {items.map((item, j) => (
                <li key={j}>{formatInline(item.replace(/^[-*]\s*/, ''))}</li>
              ))}
            </ul>
          );
        }
        const lines = p.split('\n');
        return (
          <p key={i}>
            {lines.map((line, j) => (
              <React.Fragment key={j}>
                {j > 0 && <br />}
                {formatInline(line)}
              </React.Fragment>
            ))}
          </p>
        );
      })}
    </>
  );
}

function formatInline(text: string): React.ReactNode {
  // Bold
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('*') && part.endsWith('*')) {
      return <em key={i}>{part.slice(1, -1)}</em>;
    }
    return part;
  });
}

function ResultTable({ result }: { result: SQLResult }) {
  const maxRows = 20;
  const displayRows = result.rows.slice(0, maxRows);

  return (
    <table className="data-table">
      <thead>
        <tr>
          {result.columns.map((col, i) => (
            <th key={i}>{col}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {displayRows.map((row, i) => (
          <tr key={i}>
            {row.map((cell, j) => (
              <td key={j}>{cell ?? '—'}</td>
            ))}
          </tr>
        ))}
        {result.row_count > maxRows && (
          <tr>
            <td colSpan={result.columns.length} style={{ textAlign: 'center', color: 'var(--text-muted)', fontFamily: 'var(--font-sans)' }}>
              ... {result.row_count - maxRows} more rows
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
