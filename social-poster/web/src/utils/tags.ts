import type { Platform, TagPool } from '../api/types';

// Mirrors of the backend caption rules (scripts/tagging.py), so the pill editor
// can show which tags will actually post and rebuild the caption client-side.
const IG_HASHTAG_CAP = 5;
const BSKY_CHAR_LIMIT = 300;

/**
 * The set of tag texts that will actually post for a platform, given the pool's
 * current order — the "active" (highlighted) pills.
 *
 * Instagram: @mentions always post; hashtags post until the 5-hashtag cap, in
 * order. Bluesky: keep the longest leading run of tags whose caption still fits
 * the 300-char limit (tags trim from the end).
 */
export function activeTagTexts(platform: Platform, pool: TagPool): Set<string> {
  const active = new Set<string>();
  if (platform === 'instagram') {
    let hashtags = 0;
    for (const tag of pool.tags) {
      if (tag.text.startsWith('#')) {
        if (hashtags >= IG_HASHTAG_CAP) {
          continue;
        }
        hashtags += 1;
      }
      active.add(tag.text);
    }
  } else {
    for (let n = pool.tags.length; n >= 0; n--) {
      const kept = pool.tags.slice(0, n);
      if (captionText(pool.prefix, kept.map((t) => t.text)).length <= BSKY_CHAR_LIMIT) {
        for (const tag of kept) {
          active.add(tag.text);
        }
        break;
      }
    }
  }
  return active;
}

/** Join a caption prefix with a tag line, dropping either if empty. */
function captionText(prefix: string, tagTexts: string[]): string {
  return [prefix, tagTexts.join(' ')].filter(Boolean).join('\n');
}

/** Rebuild the platform caption from the pool's current order + active rules. */
export function captionFromPool(platform: Platform, pool: TagPool): string {
  const active = activeTagTexts(platform, pool);
  const line = pool.tags.filter((t) => active.has(t.text)).map((t) => t.text);
  return captionText(pool.prefix, line);
}
