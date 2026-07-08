import { useEffect, useMemo, useRef, useState } from 'react';
import { useAccounts } from '../hooks/useAccounts';
import {
  useApproveIngest,
  useDeleteIngestItem,
  useIngestItems,
  useUpdateIngestItem,
  useUploadIngestImages,
} from '../hooks/useIngest';
import { usePosts } from '../hooks/usePosts';
import { useSettings, useUpdateSettings } from '../hooks/useSettings';
import { WeeklyScheduleModal } from './WeeklyScheduleModal';
import { formatDateTime, formatHHMM, toApiISO } from '../utils/datetime';
import { DAY_SHORT, generateSlots, timesByDay } from '../utils/schedule';
import type {
  BulkSchedule,
  Captions,
  IngestItem,
  Platform,
} from '../api/types';

const PLATFORM_LABEL: Record<Platform, string> = {
  instagram: 'Instagram',
  bluesky: 'Bluesky',
};

const ALL_PLATFORMS: Platform[] = ['instagram', 'bluesky'];

// Remembers the last-checked target accounts across sessions.
const ACCOUNTS_STORAGE_KEY = 'social-poster:bulk-account-ids';

function loadSavedAccountIds(): number[] | null {
  try {
    const parsed: unknown = JSON.parse(
      localStorage.getItem(ACCOUNTS_STORAGE_KEY) ?? ''
    );
    return Array.isArray(parsed) &&
      parsed.length > 0 &&
      parsed.every((x) => typeof x === 'number')
      ? parsed
      : null;
  } catch {
    return null;
  }
}

function saveAccountIds(ids: number[]) {
  try {
    localStorage.setItem(ACCOUNTS_STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // Storage full/unavailable — remembering the selection is best-effort.
  }
}

/**
 * Bulk ingestion: pick a weekly schedule template and target accounts, drop a
 * batch of photos, review the captions the tagging script generated (photos
 * are matched to the next free slots in upload order), then approve to
 * schedule everything at once.
 */
export function BulkAddModal({ onClose }: { onClose: () => void }) {
  const { data: accounts } = useAccounts();
  const { data: settings } = useSettings();
  const { data: posts } = usePosts();
  const { data: items = [], isLoading: itemsLoading } = useIngestItems();
  const updateSettings = useUpdateSettings();
  const upload = useUploadIngestImages();
  const updateItem = useUpdateIngestItem();
  const deleteItem = useDeleteIngestItem();
  const approve = useApproveIngest();

  // Schedule template — seeded from the saved setting once it loads, then
  // edited locally and persisted on every change.
  const [schedule, setSchedule] = useState<BulkSchedule | null>(null);
  useEffect(() => {
    if (schedule === null && settings) {
      setSchedule(settings.bulk_schedule);
    }
  }, [settings, schedule]);
  const effectiveSchedule = useMemo(
    () => schedule ?? { slots: [] },
    [schedule]
  );

  const saveSchedule = (next: BulkSchedule) => {
    setSchedule(next);
    updateSettings.mutate({ bulk_schedule: next });
  };

  const [showSchedule, setShowSchedule] = useState(false);

  // Target accounts — the last-used selection (localStorage), else all.
  const [accountIds, setAccountIds] = useState<number[] | null>(null);
  useEffect(() => {
    if (accountIds === null && accounts) {
      const saved = loadSavedAccountIds()?.filter((id) =>
        accounts.some((a) => a.id === id)
      );
      setAccountIds(
        saved && saved.length > 0 ? saved : accounts.map((a) => a.id)
      );
    }
  }, [accounts, accountIds]);
  const selectedIds = useMemo(() => accountIds ?? [], [accountIds]);

  const toggleAccount = (id: number) => {
    const next = selectedIds.includes(id)
      ? selectedIds.filter((x) => x !== id)
      : [...selectedIds, id];
    setAccountIds(next);
    saveAccountIds(next);
  };

  const selectedPlatforms = useMemo(() => {
    const set = new Set<Platform>();
    for (const id of selectedIds) {
      const account = accounts?.find((a) => a.id === id);
      if (account) {
        set.add(account.platform);
      }
    }
    return ALL_PLATFORMS.filter((p) => set.has(p));
  }, [selectedIds, accounts]);

  // Caption edits keyed by `${itemId}:${platform}`; the server value is the
  // fallback, so freshly-tagged captions appear until the user types.
  const [edits, setEdits] = useState<Record<string, string>>({});
  const captionValue = (item: IngestItem, platform: Platform) =>
    edits[`${item.id}:${platform}`] ?? item.captions[platform] ?? '';

  const captionsFor = (item: IngestItem): Captions => {
    const captions: Captions = {};
    for (const platform of selectedPlatforms) {
      captions[platform] = captionValue(item, platform);
    }
    return captions;
  };

  // Persist an edited caption when the user leaves the field, so a closed
  // modal doesn't lose review work (items live server-side).
  const persistCaption = (item: IngestItem) => {
    updateItem.mutate({
      id: item.id,
      captions: { ...item.captions, ...captionsFor(item) },
    });
  };

  const fileInput = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const onFilesChosen = (files: FileList | null) => {
    const images = Array.from(files ?? []).filter(
      (f) => f.type.startsWith('image/') || /\.avif$/i.test(f.name)
    );
    if (images.length > 0) {
      upload.mutate(images);
    }
    if (fileInput.current) {
      fileInput.current.value = '';
    }
  };

  // Slot assignment: photos fill the next free slots in upload order.
  // Occupied = already-scheduled posts, so bulk batches never double-book.
  const occupied = useMemo(
    () => new Set((posts ?? []).map((p) => p.scheduled_at)),
    [posts]
  );
  const slots = useMemo(
    () => generateSlots(effectiveSchedule, items.length, occupied),
    [effectiveSchedule, items.length, occupied]
  );

  const anyPending = items.some((i) => i.tag_status === 'pending');
  const scheduleEmpty = effectiveSchedule.slots.length === 0;
  const scheduleByDay = useMemo(
    () => timesByDay(effectiveSchedule),
    [effectiveSchedule]
  );
  const canApprove =
    items.length > 0 &&
    selectedIds.length > 0 &&
    slots.length === items.length &&
    !anyPending &&
    !approve.isPending;

  const onApprove = () => {
    approve.mutate(
      {
        account_ids: selectedIds,
        items: items.map((item, index) => ({
          id: item.id,
          scheduled_at: toApiISO(slots[index]),
          captions: captionsFor(item),
        })),
      },
      { onSuccess: () => onClose() }
    );
  };

  return (
    <>
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="modal modal--bulk"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Bulk add posts"
      >
        <div className="modal-header">
          <h2>Bulk add posts</h2>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="bulk-body">
          {/* LEFT: schedule template + accounts + upload */}
          <div className="bulk-config">
            <div className="field">
              <div className="field-label-row">
                <span className="field-label">Weekly schedule</span>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => setShowSchedule(true)}
                >
                  Edit
                </button>
              </div>
              {scheduleEmpty ? (
                <span className="muted">
                  No posting times yet — click Edit to set up the weekly
                  schedule.
                </span>
              ) : (
                <div className="schedule-summary">
                  {[...scheduleByDay.entries()]
                    .sort(([a], [b]) => a - b)
                    .map(([day, times]) => (
                      <div key={day} className="schedule-summary-row">
                        <span className="schedule-summary-day">
                          {DAY_SHORT[day]}
                        </span>
                        <span>{times.map(formatHHMM).join(', ')}</span>
                      </div>
                    ))}
                </div>
              )}
              {!scheduleEmpty && (
                <span className="muted field-help">
                  Photos fill these slots in order, week after week.
                </span>
              )}
            </div>

            <div className="field">
              <span className="field-label">Accounts</span>
              <div className="checkbox-list">
                {accounts?.map((account) => (
                  <label key={account.id} className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(account.id)}
                      onChange={() => toggleAccount(account.id)}
                    />
                    <span>
                      {account.username}{' '}
                      <span className="muted">({account.platform})</span>
                    </span>
                  </label>
                ))}
              </div>
            </div>

          </div>

          {/* RIGHT: photo drop target + review list. The whole column
              accepts drops; click-to-browse is the empty state and the
              "add more" strip so clicks never fight the caption fields. */}
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
            {itemsLoading && <span className="muted">Loading…</span>}
            {!itemsLoading && items.length === 0 && (
              <div
                className="bulk-dropzone bulk-dropzone--fill"
                role="button"
                tabIndex={0}
                onClick={() => fileInput.current?.click()}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    fileInput.current?.click();
                  }
                }}
              >
                {upload.isPending
                  ? 'Uploading…'
                  : 'Drop photos here, or click to browse'}
              </div>
            )}
            {items.map((item, index) => (
              <div key={item.id} className="bulk-item">
                <img className="bulk-item-thumb" src={item.image_url} alt="" />
                <div className="bulk-item-main">
                  <div className="bulk-item-header">
                    <span className="bulk-item-slot">
                      {slots[index]
                        ? formatDateTime(slots[index])
                        : 'No slot — set the schedule'}
                    </span>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => deleteItem.mutate(item.id)}
                      aria-label="Discard photo"
                    >
                      ✕
                    </button>
                  </div>
                  {item.tag_status === 'pending' && (
                    <span className="muted">Generating captions…</span>
                  )}
                  {item.tag_status === 'failed' && (
                    <span className="field-error">
                      Tagging failed: {item.tag_error} — write the captions
                      below.
                    </span>
                  )}
                  {item.tag_status !== 'pending' &&
                    selectedPlatforms.map((platform) => (
                      <label key={platform} className="field">
                        <span className="field-label">
                          {PLATFORM_LABEL[platform]} caption
                        </span>
                        <textarea
                          rows={6}
                          value={captionValue(item, platform)}
                          onChange={(e) =>
                            setEdits((prev) => ({
                              ...prev,
                              [`${item.id}:${platform}`]: e.target.value,
                            }))
                          }
                          onBlur={() => persistCaption(item)}
                        />
                      </label>
                    ))}
                </div>
              </div>
            ))}
            {items.length > 0 && (
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
                {upload.isPending
                  ? 'Uploading…'
                  : 'Drop more photos, or click to browse'}
              </div>
            )}
            {upload.isError && (
              <span className="field-error">{upload.error.message}</span>
            )}
          </div>
        </div>

        <div className="form-error-slot">
          {approve.isError && (
            <span className="state-error">{approve.error.message}</span>
          )}
          {!approve.isError && anyPending && (
            <span className="muted">Waiting for captions to generate…</span>
          )}
        </div>

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Close
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!canApprove}
            onClick={onApprove}
          >
            {approve.isPending
              ? 'Scheduling…'
              : `Schedule ${items.length} post${items.length === 1 ? '' : 's'}`}
          </button>
        </div>
      </div>
    </div>

    {showSchedule && (
      <WeeklyScheduleModal
        schedule={effectiveSchedule}
        onChange={saveSchedule}
        onClose={() => setShowSchedule(false)}
      />
    )}
    </>
  );
}
