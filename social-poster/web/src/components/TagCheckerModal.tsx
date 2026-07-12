import { useMemo, useRef, useState } from 'react';
import { useCheckTags } from '../hooks/useTagging';
import type { TagCheckFile } from '../api/types';

/** Human-readable form of a `A|B|C` hierarchy tag: `A > B > C`, matching the
 * `Place > USA > Alaska > State` convention used in the tag TODO. */
function prettyTag(tag: string): string {
  return tag.split('|').join(' > ');
}

/**
 * Tag Checker: drop a batch of Lightroom exports and see which
 * `cameracoffeewander|...` keywords aren't registered in the tag tree yet —
 * the tags that still need adding to `config/tags.json`. Nothing is staged or
 * scheduled; it's a read-only check. Dropped batches accumulate so you can
 * feed exports in waves.
 */
export function TagCheckerModal({ onClose }: { onClose: () => void }) {
  const check = useCheckTags();
  const [files, setFiles] = useState<TagCheckFile[]>([]);

  const fileInput = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const onFilesChosen = (chosen: FileList | null) => {
    const images = Array.from(chosen ?? []).filter(
      (f) => f.type.startsWith('image/') || /\.avif$/i.test(f.name)
    );
    if (images.length > 0) {
      check.mutate(images, {
        onSuccess: (res) => setFiles((prev) => [...prev, ...res.files]),
      });
    }
    if (fileInput.current) {
      fileInput.current.value = '';
    }
  };

  // The worklist: every unregistered tag across all dropped photos, once each.
  const aggregate = useMemo(() => {
    const seen: string[] = [];
    for (const file of files) {
      for (const tag of file.unregistered) {
        if (!seen.includes(tag)) {
          seen.push(tag);
        }
      }
    }
    return seen;
  }, [files]);

  const copyAggregate = () => {
    void navigator.clipboard?.writeText(aggregate.map(prettyTag).join('\n'));
  };

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="modal modal--bulk"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Tag checker"
      >
        <div className="modal-header">
          <h2>Tag Checker</h2>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div
          className={`bulk-review ${dragOver ? 'bulk-review--dragover' : ''}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={(e) => {
            if (!e.currentTarget.contains(e.relatedTarget as Node)) {
              setDragOver(false);
            }
          }}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            onFilesChosen(e.dataTransfer.files);
          }}
        >
          <input
            ref={fileInput}
            type="file"
            accept="image/*,.avif"
            multiple
            hidden
            onChange={(e) => onFilesChosen(e.target.files)}
          />

          <p className="muted field-help">
            Drop photos to see which <code>cameracoffeewander</code> keywords
            aren't registered in the tag tree yet. Nothing is scheduled — this
            just lists the tags to add to <code>config/tags.json</code>.
          </p>

          {aggregate.length > 0 && (
            <div className="tagcheck-summary">
              <div className="field-label-row">
                <span className="field-label">
                  {aggregate.length} tag{aggregate.length === 1 ? '' : 's'} to
                  register
                </span>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={copyAggregate}
                >
                  Copy
                </button>
              </div>
              <ul className="tagcheck-list">
                {aggregate.map((tag) => (
                  <li key={tag}>
                    <code>{prettyTag(tag)}</code>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {files.length > 0 && aggregate.length === 0 && (
            <span className="state-success">
              All keywords are registered — nothing to add. ✓
            </span>
          )}

          {files.map((file, index) => (
            <div key={`${file.filename}:${index}`} className="tagcheck-file">
              <span className="tagcheck-file-name">{file.filename}</span>
              {file.error ? (
                <span className="muted">{file.error}</span>
              ) : file.unregistered.length === 0 ? (
                <span className="state-success">All registered ✓</span>
              ) : (
                <span className="field-error">
                  {file.unregistered.map(prettyTag).join(', ')}
                </span>
              )}
            </div>
          ))}

          <div
            className="bulk-dropzone"
            role="button"
            tabIndex={0}
            onClick={() => fileInput.current?.click()}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                fileInput.current?.click();
              }
            }}
          >
            {check.isPending
              ? 'Checking…'
              : files.length === 0
                ? 'Drop photos here, or click to browse'
                : 'Drop more photos, or click to browse'}
          </div>

          {check.isError && (
            <span className="field-error">{check.error.message}</span>
          )}
        </div>

        <div className="modal-actions">
          {files.length > 0 && (
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => setFiles([])}
            >
              Clear
            </button>
          )}
          <button type="button" className="btn btn-primary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
