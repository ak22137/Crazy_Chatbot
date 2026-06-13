const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = {
  /**
   * Upload files to the backend.
   */
  async uploadFiles(files: FileList | File[]): Promise<any[]> {
    const formData = new FormData();
    Array.from(files).forEach((file) => {
      formData.append('files', file);
    });

    const res = await fetch(`${API_BASE}/api/v1/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Upload failed');
    }

    return res.json();
  },

  /**
   * Send a chat question (synchronous).
   */
  async chat(question: string, history: { role: string; content: string }[] = []): Promise<{
    intent: string;
    answer: string;
    sql_result?: any;
    processing_time_ms: number;
  }> {
    const res = await fetch(`${API_BASE}/api/v1/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, history }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Chat request failed');
    }

    return res.json();
  },

  /**
   * Send a chat question with SSE streaming.
   * Returns a function to abort the stream.
   */
  chatStream(
    question: string,
    onEvent: (event: { type: string; data: any }) => void,
    onError: (error: Error) => void,
    onDone: () => void,
    history: { role: string; content: string }[] = [],
  ): () => void {
    const controller = new AbortController();

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/chat/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question, history }),
          signal: controller.signal,
        });

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }

        const reader = res.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('data: ')) {
              try {
                const data = JSON.parse(trimmed.slice(6));
                onEvent(data);
                if (data.type === 'done') {
                  onDone();
                  return;
                }
              } catch {
                // Ignore unparseable chunks
              }
            }
          }
        }
        onDone();
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          onError(err);
        }
      }
    })();

    return () => controller.abort();
  },

  /**
   * Get table metadata.
   */
  async getTables(): Promise<{ tables: Record<string, any> }> {
    const res = await fetch(`${API_BASE}/api/v1/metadata/tables`);
    if (!res.ok) throw new Error('Failed to fetch tables');
    return res.json();
  },

  /**
   * Preview table data.
   */
  async previewTable(tableName: string, limit = 20): Promise<any> {
    const res = await fetch(`${API_BASE}/api/v1/metadata/tables/${tableName}/preview?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to preview table');
    return res.json();
  },

  /**
   * Get relationships.
   */
  async getRelationships(): Promise<any> {
    const res = await fetch(`${API_BASE}/api/v1/metadata/relationships`);
    if (!res.ok) throw new Error('Failed to fetch relationships');
    return res.json();
  },

  /**
   * Health check.
   */
  async health(): Promise<{ status: string; model: string }> {
    const res = await fetch(`${API_BASE}/api/v1/health`);
    return res.json();
  },
};
