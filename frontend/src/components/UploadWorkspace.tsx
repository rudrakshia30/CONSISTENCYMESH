import React, { useRef, useState } from 'react';
import { api } from '../services/api';

interface UploadWorkspaceProps {
  onAnalyze: (documentIds: string[]) => void;
}

interface UploadItem {
  id: string;
  file: File;
  status: 'pending' | 'uploading' | 'done' | 'error';
  documentId?: string;
  error?: string;
}

export const UploadWorkspace: React.FC<UploadWorkspaceProps> = ({ onAnalyze }) => {
  const [items, setItems] = useState<UploadItem[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processUpload = async (itemToUpload: UploadItem) => {
    // Set status uploading
    setItems((prev) =>
      prev.map((it) => (it.id === itemToUpload.id ? { ...it, status: 'uploading', error: undefined } : it))
    );

    try {
      const resp = await api.uploadDocument(itemToUpload.file);
      setItems((prev) =>
        prev.map((it) =>
          it.id === itemToUpload.id
            ? { ...it, status: 'done', documentId: resp.document_id }
            : it
        )
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Upload failed. Is backend running at port 8000?';
      setItems((prev) =>
        prev.map((it) => (it.id === itemToUpload.id ? { ...it, status: 'error', error: msg } : it))
      );
    }
  };

  const addFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const newItems: UploadItem[] = Array.from(files).map((file) => ({
      id: `${file.name}_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      file,
      status: 'pending',
    }));

    setItems((prev) => [...prev, ...newItems]);

    // Immediately upload each new file
    newItems.forEach((item) => {
      processUpload(item);
    });

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleRetryFailed = () => {
    const failedOrPending = items.filter((it) => it.status === 'error' || it.status === 'pending');
    failedOrPending.forEach((item) => processUpload(item));
  };

  const handleRemoveItem = (id: string) => {
    setItems((prev) => prev.filter((it) => it.id !== id));
  };

  const uploadedDocIds = items
    .filter((item) => item.status === 'done' && item.documentId)
    .map((item) => item.documentId as string);

  return (
    <div className="card-glass">
      <h2 style={{ marginBottom: 'var(--space-md)' }}>Upload Document Stack</h2>
      <p style={{ marginBottom: 'var(--space-lg)', color: 'var(--text-secondary)' }}>
        Upload 2 to 6 related legal or business documents (e.g. MSA + SOW + Amendment).
      </p>

      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={(e) => addFiles(e.target.files)}
        multiple
        accept=".pdf,.docx,.txt"
        style={{ display: 'none' }}
      />

      {/* Upload Drop Zone */}
      <div
        className={`upload-zone ${isDragOver ? 'drag-over' : ''}`}
        aria-label="Upload zone for document files"
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          setIsDragOver(false);
        }}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragOver(false);
          addFiles(e.dataTransfer.files);
        }}
        onClick={() => fileInputRef.current?.click()}
        style={{ cursor: 'pointer' }}
      >
        <div className="upload-zone-icon">📁</div>
        <div className="upload-zone-text" style={{ fontWeight: 600, fontSize: '1.1rem' }}>
          Drag & Drop Document Files Here
        </div>
        <div className="upload-zone-hint" style={{ marginTop: 'var(--space-xs)' }}>
          Supports <strong>.pdf</strong>, <strong>.docx</strong>, and <strong>.txt</strong> files
        </div>

        <button
          type="button"
          className="btn btn-secondary"
          style={{ marginTop: 'var(--space-md)' }}
          onClick={(e) => {
            e.stopPropagation();
            fileInputRef.current?.click();
          }}
        >
          📂 Browse Files from Computer
        </button>
      </div>

      {/* Selected File List */}
      {items.length > 0 && (
        <div style={{ marginTop: 'var(--space-xl)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
            <h3>Selected Documents ({items.length})</h3>
            {items.some((i) => i.status === 'error') && (
              <button type="button" className="btn btn-ghost btn-sm" onClick={handleRetryFailed} style={{ color: 'var(--color-warning)' }}>
                ↻ Retry Failed Uploads
              </button>
            )}
          </div>

          <ul className="file-list" aria-label="Selected document list">
            {items.map((item) => (
              <li
                key={item.id}
                className="file-item"
                style={{
                  flexDirection: 'column',
                  alignItems: 'stretch',
                  gap: 'var(--space-xs)',
                  borderColor: item.status === 'error' ? 'var(--color-error)' : 'var(--border-color)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div className="file-item-info">
                    <span className="file-item-icon">📄</span>
                    <div>
                      <div className="file-item-name">{item.file.name}</div>
                      <div className="file-item-meta">{(item.file.size / 1024).toFixed(1)} KB</div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
                    {item.status === 'pending' && <span className="status-badge">Pending</span>}
                    {item.status === 'uploading' && (
                      <span className="status-badge pulse" style={{ color: 'var(--accent-primary)' }}>
                        <span className="spinner" style={{ width: 12, height: 12, borderWidth: 2, marginRight: 6 }} />
                        Uploading...
                      </span>
                    )}
                    {item.status === 'done' && (
                      <span className="status-badge" style={{ color: 'var(--color-success)', background: 'rgba(34, 197, 94, 0.1)' }}>
                        ✓ Uploaded
                      </span>
                    )}
                    {item.status === 'error' && (
                      <span className="status-badge" style={{ color: 'var(--color-error)', background: 'rgba(239, 68, 68, 0.1)' }}>
                        ✕ Failed
                      </span>
                    )}

                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => handleRemoveItem(item.id)}
                      title="Remove file"
                      aria-label={`Remove ${item.file.name}`}
                    >
                      ✕
                    </button>
                  </div>
                </div>

                {item.error && (
                  <div style={{ color: 'var(--color-error)', fontSize: '0.8rem', background: 'rgba(239, 68, 68, 0.08)', padding: 'var(--space-xs) var(--space-sm)', borderRadius: 'var(--radius-sm)' }}>
                    ⚠️ {item.error}
                  </div>
                )}
              </li>
            ))}
          </ul>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'var(--space-xl)' }}>
            <button
              className="btn btn-primary btn-lg"
              onClick={() => onAnalyze(uploadedDocIds)}
              disabled={uploadedDocIds.length < 2}
              type="button"
            >
              Analyze Consistency ({uploadedDocIds.length} uploaded)
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
