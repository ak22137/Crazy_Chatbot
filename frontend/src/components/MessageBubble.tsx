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
          </div>
        )}

        {/* Data Table — only when the answer text doesn't already contain a markdown table */}
        {message.sqlResult && message.sqlResult.success &&
          message.sqlResult.columns.length > 0 && message.sqlResult.rows.length > 0 &&
          !message.content.split('\n').some(line => /^\s*\|.+\|/.test(line)) && (
          <div className="data-table-wrapper">
            <ResultTable result={message.sqlResult} />
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

/** Render inline markdown: **bold**, *italic*, `code` */
function formatInline(text: string): React.ReactNode {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**'))
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith('*') && part.endsWith('*'))
      return <em key={i}>{part.slice(1, -1)}</em>;
    if (part.startsWith('`') && part.endsWith('`'))
      return <code key={i} className="inline-code">{part.slice(1, -1)}</code>;
    return part;
  });
}

/** Parse a markdown table block into a React table element */
function MarkdownTable({ lines }: { lines: string[] }) {
  const parseRow = (line: string) =>
    line.replace(/^\||\|$/g, '').split('|').map((c) => c.trim());

  const isseparator = (line: string) => /^\|?[\s\-|:]+\|?$/.test(line);

  const headerLine = lines[0];
  const bodyLines = lines.filter((l, i) => i > 0 && !isseparator(l));
  const headers = parseRow(headerLine);

  return (
    <div className="data-table-wrapper" style={{ marginTop: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
      <table className="data-table">
        <thead>
          <tr>{headers.map((h, i) => <th key={i}>{formatInline(h)}</th>)}</tr>
        </thead>
        <tbody>
          {bodyLines.map((row, i) => (
            <tr key={i}>
              {parseRow(row).map((cell, j) => <td key={j}>{formatInline(cell)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MessageText({ text }: { text: string }) {
  const lines = text.split('\n');
  const nodes: React.ReactNode[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Fenced code block
    if (line.startsWith('```')) {
      const lang = line.slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      nodes.push(
        <pre key={key++} className="sql-code" style={{ marginTop: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
          <code>{codeLines.join('\n')}</code>
        </pre>
      );
      i++; // skip closing ```
      continue;
    }

    // Markdown table block
    if (line.startsWith('|')) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].startsWith('|')) {
        tableLines.push(lines[i]);
        i++;
      }
      if (tableLines.length >= 2) {
        nodes.push(<MarkdownTable key={key++} lines={tableLines} />);
      } else {
        tableLines.forEach((l) => nodes.push(<p key={key++}>{formatInline(l)}</p>));
      }
      continue;
    }

    // Heading
    const headingMatch = line.match(/^(#{1,3})\s+(.*)/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const content = headingMatch[2];
      const Tag = `h${level + 2}` as keyof JSX.IntrinsicElements; // h3–h5 to stay subtle
      nodes.push(<Tag key={key++} className="md-heading">{formatInline(content)}</Tag>);
      i++;
      continue;
    }

    // Unordered list block
    if (/^[-*]\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s/.test(lines[i])) {
        items.push(lines[i].replace(/^[-*]\s+/, ''));
        i++;
      }
      nodes.push(
        <ul key={key++}>
          {items.map((item, j) => <li key={j}>{formatInline(item)}</li>)}
        </ul>
      );
      continue;
    }

    // Ordered list block
    if (/^\d+\.\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\.\s+/, ''));
        i++;
      }
      nodes.push(
        <ol key={key++}>
          {items.map((item, j) => <li key={j}>{formatInline(item)}</li>)}
        </ol>
      );
      continue;
    }

    // Blank line — skip
    if (line.trim() === '') {
      i++;
      continue;
    }

    // Normal paragraph line (accumulate until blank line or block marker)
    const paraLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !lines[i].startsWith('```') &&
      !lines[i].startsWith('|') &&
      !/^#{1,3}\s/.test(lines[i]) &&
      !/^[-*]\s/.test(lines[i]) &&
      !/^\d+\.\s/.test(lines[i])
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    if (paraLines.length) {
      nodes.push(
        <p key={key++}>
          {paraLines.map((l, j) => (
            <React.Fragment key={j}>
              {j > 0 && <br />}
              {formatInline(l)}
            </React.Fragment>
          ))}
        </p>
      );
    }
  }

  return <>{nodes}</>;
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
