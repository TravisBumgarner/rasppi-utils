export type Platform = 'instagram' | 'bluesky';

export type TargetStatus = 'scheduled' | 'posted' | 'failed';

export interface Account {
  id: number;
  platform: Platform;
  username: string;
  display_name: string | null;
}

/** Returned by POST /api/accounts — the saved account plus a profile receipt. */
export interface AddAccountResult extends Account {
  avatar_url: string | null;
  follower_count: number | null;
  post_count: number | null;
}

export interface Target {
  /** The post_target row id — the unit of a photo×account record. */
  id: number;
  account_id: number;
  platform: Platform;
  username: string;
  caption: string;
  status: TargetStatus;
  error: string | null;
  posted_at: string | null;
}

/** Per-platform captions, e.g. `{ instagram: '…', bluesky: '…' }`. */
export type Captions = Partial<Record<Platform, string>>;

export interface Post {
  id: number;
  /** Representative caption (first non-empty) for compact display. */
  caption: string;
  captions: Captions;
  scheduled_at: string;
  image_url: string;
  created_at: string;
  targets: Target[];
}

/** One row of the append-only publish audit log. */
export interface LogEntry {
  id: number;
  post_id: number | null;
  platform: Platform;
  username: string;
  status: 'posted' | 'failed';
  error: string | null;
  image_url: string | null;
  caption: string | null;
  attempted_at: string;
}

export interface CreateAccountInput {
  platform: Platform;
  ig_user_id?: string;
  access_token?: string;
  handle?: string;
  app_password?: string;
}

export interface CreatePostInput {
  image: File;
  captions: Captions;
  scheduled_at: string;
  account_ids: number[];
}

/** Full edit of an existing post. Image is optional (omit to keep current). */
export interface EditPostInput {
  image?: File;
  captions: Captions;
  scheduled_at: string;
  account_ids: number[];
}

export interface UpdatePostInput {
  scheduled_at?: string;
  caption?: string;
}

/** App settings. `common_times` are 'HH:MM' presets for the schedule dropdown. */
export interface Settings {
  common_times: string[];
}
