'use client';

import React, { useState, useEffect } from 'react';
import { TableMeta } from '@/types';
import { api } from '@/services/api';

interface SidebarProps {
  onTableSelect?: (tableName: string) => void;
  refreshTrigger?: number;
}

export default function Sidebar({ onTableSelect, refreshTrigger }: SidebarProps) {
  const [tables, setTables] = useState<Record<string, TableMeta>>({});
  const [expandedTable, setExpandedTable] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTables();
  }, [refreshTrigger]);

  const loadTables = async () => {
    try {
      setLoading(true);
      const data = await api.getTables();
      setTables(data.tables || {});
    } catch {
      // Tables will be empty if backend isn't running yet
    } finally {
      setLoading(false);
    }
  };

  const tableNames = Object.keys(tables);

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">⚡</div>
          <span className="sidebar-logo-text">Excel Intel</span>
        </div>
      </div>

      <div className="sidebar-content">
        <div className="sidebar-section">
          <div className="sidebar-section-title">Data Tables</div>
          {loading ? (
            <div className="empty-state" style={{ padding: '1rem' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Loading...</div>
            </div>
          ) : tableNames.length === 0 ? (
            <div className="empty-state" style={{ padding: '1rem' }}>
              <span className="empty-state-icon">📁</span>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                No tables yet. Upload a file to get started.
              </div>
            </div>
          ) : (
            tableNames.map((name) => {
              const meta = tables[name];
              const isExpanded = expandedTable === name;
              return (
                <div key={name}>
                  <div
                    className="sidebar-item"
                    onClick={() => {
                      setExpandedTable(isExpanded ? null : name);
                      onTableSelect?.(name);
                    }}
                  >
                    <span className="sidebar-item-icon">📋</span>
                    <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {name}
                    </span>
                    <span className="sidebar-item-meta">{meta.row_count}</span>
                  </div>
                  {isExpanded && meta.columns && (
                    <div style={{ paddingLeft: '2.2rem', marginBottom: '0.5rem' }}>
                      {Object.entries(meta.columns).map(([colName, colMeta]) => (
                        <div
                          key={colName}
                          style={{
                            fontSize: 'var(--text-xs)',
                            color: 'var(--text-muted)',
                            padding: '2px 0',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.4rem',
                          }}
                        >
                          <span style={{ color: colMeta.primary_key ? 'var(--warning)' : 'var(--text-tertiary)' }}>
                            {colMeta.primary_key ? '🔑' : '·'}
                          </span>
                          <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                            {colName}
                          </span>
                          <span className="badge badge-info" style={{ marginLeft: 'auto' }}>
                            {colMeta.type}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </aside>
  );
}
