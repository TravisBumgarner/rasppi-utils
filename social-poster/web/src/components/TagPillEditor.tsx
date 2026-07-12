import { useMemo, useState } from 'react';
import type { Platform, TagPill, TagPool } from '../api/types';
import { activeTagTexts } from '../utils/tags';

/**
 * Draggable tag pills for one platform. Tags that will actually post are
 * highlighted (active); the rest are grayscale. Priority hubs show a ★.
 * Dragging a pill onto another moves it to that position, so you drag tags up
 * to promote them into the posted set (top-5 hashtags on Instagram, whatever
 * fits 300 chars on Bluesky).
 */
export function TagPillEditor({
  platform,
  pool,
  onReorder,
}: {
  platform: Platform;
  pool: TagPool;
  onReorder: (tags: TagPill[]) => void;
}) {
  const active = useMemo(() => activeTagTexts(platform, pool), [platform, pool]);
  const [dragText, setDragText] = useState<string | null>(null);
  const [overText, setOverText] = useState<string | null>(null);

  const move = (fromText: string, toText: string) => {
    if (fromText === toText) {
      return;
    }
    const tags = [...pool.tags];
    const from = tags.findIndex((t) => t.text === fromText);
    const to = tags.findIndex((t) => t.text === toText);
    if (from < 0 || to < 0) {
      return;
    }
    const [moved] = tags.splice(from, 1);
    tags.splice(to, 0, moved);
    onReorder(tags);
  };

  if (pool.tags.length === 0) {
    return <span className="muted pill-empty">No tags for this photo.</span>;
  }

  return (
    <div className="pillrow">
      {pool.tags.map((tag) => {
        const isActive = active.has(tag.text);
        return (
          <span
            key={tag.text}
            draggable
            onDragStart={() => setDragText(tag.text)}
            onDragEnd={() => {
              setDragText(null);
              setOverText(null);
            }}
            onDragOver={(e) => {
              e.preventDefault();
              if (overText !== tag.text) {
                setOverText(tag.text);
              }
            }}
            onDrop={(e) => {
              e.preventDefault();
              if (dragText) {
                move(dragText, tag.text);
              }
              setDragText(null);
              setOverText(null);
            }}
            className={[
              'pill',
              isActive ? 'pill--active' : 'pill--muted',
              dragText === tag.text ? 'pill--dragging' : '',
              overText === tag.text && dragText ? 'pill--over' : '',
            ]
              .filter(Boolean)
              .join(' ')}
            title={isActive ? 'Will post' : 'Not posting — drag up to include'}
          >
            <span className="pill-icon" aria-hidden="true">
              {tag.priority ? '★' : ''}
            </span>
            {tag.text}
          </span>
        );
      })}
    </div>
  );
}
