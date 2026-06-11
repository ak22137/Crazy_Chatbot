'use client';

import React, { useState, useRef, useCallback } from 'react';
import { UploadResult } from '@/types';
import { api } from '@/services/api';

interface FileUploaderProps {
  onUploadComplete: (results: UploadResult[]) => void;
}

export default function FileUploader({ onUploadComplete }: FileUploaderProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadItems, setUploadItems] = useState<
    { name: string; status: 'uploading' | 'success' | 'error'; message?: string }[]
  >([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(async (files: FileList | File[]) => {
    if (!files.length) return;

    setIsUploading(true);
    const items = Array.from(files).map((f) => ({
      name: f.name,
      status: 'uploading' as const,
    }));
    setUploadItems(items);

    try {
      const results = await api.uploadFiles(files);

      setUploadItems(
        results.map((r: UploadResult) => ({
          name: r.filename,
          status: r.status === 'error' ? ('error' as const) : ('success' as const),
          message:
            r.status === 'error'
              ? r.error || 'Unknown error'
              : `${r.tables.length} table(s), ${r.tables.reduce((s: number, t: any) => s + t.row_count, 0)} rows`,
        }))
      );

      onUploadComplete(results);
    } catch (err: any) {
      setUploadItems(
        items.map((item) => ({
          ...item,
          status: 'error' as const,
          message: err.message,
        }))
      );
    } finally {
      setIsUploading(false);
    }
  }, [onUploadComplete]);

  return (
    <div>
      <div
        className={`upload-zone ${isDragOver ? 'drag-over' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
      >
        <span className="upload-zone-icon">📊</span>
        <div className="upload-zone-title">
          {isUploading ? 'Uploading...' : 'Drop Excel or CSV files here'}
        </div>
        <div className="upload-zone-subtitle">
          or click to browse • .xlsx, .xls, .csv supported
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls,.csv"
          multiple
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
        />
      </div>

      {uploadItems.length > 0 && (
        <div className="upload-progress">
          {uploadItems.map((item, i) => (
            <div key={i} className="upload-file-item">
              <span className="upload-file-icon">
                {item.status === 'uploading' ? '⏳' : item.status === 'success' ? '✅' : '❌'}
              </span>
              <div className="upload-file-info">
                <div className="upload-file-name">{item.name}</div>
                <div className={`upload-file-status ${item.status}`}>
                  {item.status === 'uploading'
                    ? 'Processing...'
                    : item.message || item.status}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
