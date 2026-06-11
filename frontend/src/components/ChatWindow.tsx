'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Message, UploadResult } from '@/types';
import { api } from '@/services/api';
import MessageBubble from '@/components/MessageBubble';
import FileUploader from '@/components/FileUploader';
import Sidebar from '@/components/Sidebar';

const SUGGESTIONS = [
  'How many rows are in my data?',
  'Show me the first 10 records',
  'What tables do I have?',
  'What are the column names?',
];

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [refreshSidebar, setRefreshSidebar] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = useCallback(async (question: string) => {
    if (!question.trim() || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: question.trim(),
      timestamp: new Date(),
    };

    const assistantMsg: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput('');
    setIsLoading(true);

    try {
      // Use SSE streaming
      let fullContent = '';
      let sqlResult: any = null;
      let intent = '';

      const abort = api.chatStream(
        question,
        (event) => {
          if (event.type === 'intent') {
            intent = event.data;
          } else if (event.type === 'sql') {
            sqlResult = event.data;
          } else if (event.type === 'token') {
            fullContent += event.data;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? { ...m, content: fullContent, isStreaming: true }
                  : m
              )
            );
          } else if (event.type === 'done') {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? {
                      ...m,
                      content: fullContent,
                      isStreaming: false,
                      intent,
                      sqlResult,
                      processingTimeMs: event.data?.processing_time_ms,
                    }
                  : m
              )
            );
          } else if (event.type === 'error') {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsg.id
                  ? { ...m, content: `Error: ${event.data}`, isStreaming: false }
                  : m
              )
            );
          }
        },
        (error) => {
          // Fallback to sync if SSE fails
          handleSyncFallback(question, assistantMsg.id);
        },
        () => {
          setIsLoading(false);
        }
      );
    } catch {
      setIsLoading(false);
    }
  }, [isLoading]);

  const handleSyncFallback = async (question: string, msgId: string) => {
    try {
      const result = await api.chat(question);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === msgId
            ? {
                ...m,
                content: result.answer,
                isStreaming: false,
                intent: result.intent,
                sqlResult: result.sql_result,
                processingTimeMs: result.processing_time_ms,
              }
            : m
        )
      );
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === msgId
            ? { ...m, content: `Error: ${err.message}`, isStreaming: false }
            : m
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const handleUploadComplete = (results: UploadResult[]) => {
    setRefreshSidebar((n) => n + 1);
    setShowUpload(false);

    const successTables = results
      .filter((r) => r.status !== 'error')
      .flatMap((r) => r.tables);

    if (successTables.length > 0) {
      const summary = successTables
        .map((t) => `**${t.table_name}** (${t.row_count} rows, ${t.column_count} columns)`)
        .join('\n- ');

      const sysMsg: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `📊 Successfully loaded your data!\n\n- ${summary}\n\nYou can now ask me questions about your data. Try something like:\n- *How many rows are in ${successTables[0].table_name}?*\n- *Show me the first 10 records*\n- *What's the average of [column]?*`,
        timestamp: new Date(),
        intent: 'SYSTEM',
      };
      setMessages((prev) => [...prev, sysMsg]);
    }
  };

  const hasMessages = messages.length > 0;

  return (
    <div className="app-layout">
      <Sidebar refreshTrigger={refreshSidebar} />
      <div className="main-content">
        <header className="header">
          <span className="header-title">
            {hasMessages ? 'Chat' : 'Welcome'}
          </span>
          <div className="header-actions">
            <button
              className="btn"
              onClick={() => setShowUpload(!showUpload)}
            >
              {showUpload ? '✕ Close' : '📁 Upload'}
            </button>
            {hasMessages && (
              <button
                className="btn"
                onClick={() => {
                  setMessages([]);
                }}
              >
                🗑️ Clear
              </button>
            )}
          </div>
        </header>

        <div className="chat-container">
          {showUpload && (
            <div style={{ maxWidth: 'var(--chat-max-width)', margin: '0 auto var(--space-6)', width: '100%' }}>
              <FileUploader onUploadComplete={handleUploadComplete} />
            </div>
          )}

          <div className="chat-messages">
            {!hasMessages && !showUpload ? (
              <div className="welcome">
                <span className="welcome-icon">⚡</span>
                <h1 className="welcome-title">Excel Intelligence</h1>
                <p className="welcome-subtitle">
                  Upload your Excel or CSV files and ask questions in plain English.
                  I use SQL to give you precise, deterministic answers — no guessing.
                </p>
                <div className="welcome-suggestions">
                  {SUGGESTIONS.map((s, i) => (
                    <div
                      key={i}
                      className="welcome-suggestion"
                      onClick={() => sendMessage(s)}
                    >
                      {s}
                    </div>
                  ))}
                </div>
                <button
                  className="btn btn-primary"
                  style={{ marginTop: 'var(--space-4)' }}
                  onClick={() => setShowUpload(true)}
                >
                  📊 Upload your first file
                </button>
              </div>
            ) : (
              messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="chat-input-container">
          <div className="chat-input-wrapper">
            <textarea
              ref={inputRef}
              className="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your data..."
              rows={1}
              disabled={isLoading}
            />
            <button
              className="chat-send-btn"
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || isLoading}
              aria-label="Send message"
            >
              {isLoading ? '⏳' : '→'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
