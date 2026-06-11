export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  intent?: string;
  sqlResult?: SQLResult | null;
  processingTimeMs?: number;
  isStreaming?: boolean;
}

export interface SQLResult {
  success: boolean;
  sql: string;
  columns: string[];
  rows: (string | null)[][];
  row_count: number;
  execution_time_ms: number;
  explanation: string;
  error: string;
}

export interface TableMeta {
  description: string;
  row_count: number;
  column_count: number;
  columns: Record<string, ColumnMeta>;
}

export interface ColumnMeta {
  type: string;
  nullable: boolean;
  primary_key: boolean;
  description: string;
  sample_values: string[];
  distinct_count: number;
}

export interface UploadResult {
  upload_id: string;
  filename: string;
  status: string;
  tables: {
    table_name: string;
    sheet_name: string;
    row_count: number;
    column_count: number;
    columns: string[];
    primary_key: string[];
  }[];
  relationships: any[];
  semantic_groups: Record<string, any>;
  error?: string | null;
}
