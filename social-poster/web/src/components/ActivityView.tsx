import { useMemo, useState } from 'react';
import { usePosts, useSendTargetNow, useDeleteTarget } from '../hooks/usePosts';
import { useAccounts } from '../hooks/useAccounts';
import type { Post, Target } from '../api/types';
import { PlatformBadge } from './Badges';
import {
  ROW_STATUS_LABEL,
  ROW_STATUS_RANK,
  rowActions,
  rowStatus,
  type RowStatus,
} from '../utils/posts';
import { formatDateTime, parseISO } from '../utils/datetime';

interface ActivityViewProps {
  onEditPost: (post: Post) => void;
}

/** One table row: a single photo×account record. */
interface Row {
  post: Post;
  target: Target;
  status: RowStatus;
}

type SortKey = 'caption' | 'scheduled' | 'account' | 'status';
type SortDir = 'asc' | 'desc';

const COMPARATORS: Record<SortKey, (a: Row, b: Row) => number> = {
  caption: (a, b) => a.post.caption.localeCompare(b.post.caption),
  scheduled: (a, b) => a.post.scheduled_at.localeCompare(b.post.scheduled_at),
  account: (a, b) => a.target.username.localeCompare(b.target.username),
  status: (a, b) => ROW_STATUS_RANK[a.status] - ROW_STATUS_RANK[b.status],
};

const ALL_STATUSES: RowStatus[] = [
  'queued',
  'sending',
  'missed',
  'errored',
  'posted',
];

function truncate(text: string, max = 80): string {
  return text.length <= max ? text : `${text.slice(0, max - 1)}…`;
}

/**
 * Activity: one row per photo×account record (queued / sending / missed /
 * posted / errored), filterable by account and status, sortable by column.
 * Actions are gated by each record's status.
 */
export function ActivityView({ onEditPost }: ActivityViewProps) {
  const { data: posts, isLoading, isError, error } = usePosts();
  const { data: accounts } = useAccounts();
  const sendTarget = useSendTargetNow();
  const deleteTarget = useDeleteTarget();

  const [accountFilter, setAccountFilter] = useState<'all' | number>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | RowStatus>('all');
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDir }>({
    key: 'status',
    dir: 'asc',
  });

  const rows = useMemo<Row[]>(() => {
    const all = (posts ?? []).flatMap((post) =>
      post.targets.map((target) => ({
        post,
        target,
        status: rowStatus(post.scheduled_at, target.status),
      })),
    );
    const filtered = all.filter(
      (r) =>
        (accountFilter === 'all' || r.target.account_id === accountFilter) &&
        (statusFilter === 'all' || r.status === statusFilter),
    );
    const cmp = COMPARATORS[sort.key];
    const factor = sort.dir === 'asc' ? 1 : -1;
    return filtered.sort(
      (a, b) =>
        factor * cmp(a, b) ||
        a.post.scheduled_at.localeCompare(b.post.scheduled_at),
    );
  }, [posts, accountFilter, statusFilter, sort]);

  const toggleSort = (key: SortKey) =>
    setSort((prev) =>
      prev.key === key
        ? { key, dir: prev.dir === 'asc' ? 'desc' : 'asc' }
        : { key, dir: 'asc' },
    );

  const sortableHeader = (key: SortKey, label: string) => (
    <th>
      <button type="button" className="th-sort" onClick={() => toggleSort(key)}>
        {label}
        {sort.key === key ? (sort.dir === 'asc' ? ' ▲' : ' ▼') : ''}
      </button>
    </th>
  );

  if (isLoading) {
    return <div className="state-msg">Loading…</div>;
  }
  if (isError) {
    return (
      <div className="state-msg state-error">
        Failed to load posts: {error.message}
      </div>
    );
  }

  return (
    <div className="activity">
      <div className="activity-filters">
        <label className="filter">
          <span className="filter-label">Account</span>
          <select
            value={accountFilter === 'all' ? 'all' : String(accountFilter)}
            onChange={(e) =>
              setAccountFilter(
                e.target.value === 'all' ? 'all' : Number(e.target.value),
              )
            }
          >
            <option value="all">All accounts</option>
            {accounts?.map((a) => (
              <option key={a.id} value={a.id}>
                @{a.username} ({a.platform})
              </option>
            ))}
          </select>
        </label>

        <label className="filter">
          <span className="filter-label">Status</span>
          <select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value as 'all' | RowStatus)
            }
          >
            <option value="all">All statuses</option>
            {ALL_STATUSES.map((s) => (
              <option key={s} value={s}>
                {ROW_STATUS_LABEL[s]}
              </option>
            ))}
          </select>
        </label>
      </div>

      {rows.length === 0 ? (
        <div className="state-msg">No records match.</div>
      ) : (
        <table className="queue-table">
          <thead>
            <tr>
              <th>Image</th>
              {sortableHeader('caption', 'Caption')}
              {sortableHeader('scheduled', 'Scheduled')}
              {sortableHeader('account', 'Account')}
              {sortableHeader('status', 'Status')}
              <th>Details</th>
              <th aria-label="actions" />
            </tr>
          </thead>
          <tbody>
            {rows.map(({ post, target, status }) => {
              const actions = rowActions(status);
              return (
                <tr
                  key={target.id}
                  className={
                    status === 'errored' || status === 'missed'
                      ? 'queue-row--overdue'
                      : undefined
                  }
                >
                  <td>
                    <img className="queue-thumb" src={post.image_url} alt="" />
                  </td>
                  <td className="queue-caption">
                    {target.caption ? (
                      truncate(target.caption)
                    ) : (
                      <span className="muted">(no caption)</span>
                    )}
                  </td>
                  <td className="queue-when">
                    {formatDateTime(parseISO(post.scheduled_at))}
                  </td>
                  <td>
                    @{target.username}{' '}
                    <PlatformBadge platform={target.platform} />
                  </td>
                  <td>
                    <span className={`status-badge row-status-${status}`}>
                      {ROW_STATUS_LABEL[status]}
                    </span>
                  </td>
                  <td className="queue-caption">
                    {target.error ? (
                      <span className="state-error">{target.error}</span>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td>
                    <div className="queue-actions">
                      {actions.canEdit && (
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm"
                          onClick={() => onEditPost(post)}
                        >
                          Edit
                        </button>
                      )}
                      {actions.canSend && (
                        <button
                          type="button"
                          className="btn btn-sm"
                          disabled={sendTarget.isPending}
                          onClick={() => {
                            if (
                              window.confirm(
                                `${actions.isRetry ? 'Retry' : 'Publish'} @${target.username} now?`,
                              )
                            ) {
                              sendTarget.mutate(target.id);
                            }
                          }}
                        >
                          {actions.isRetry ? 'Retry' : 'Send now'}
                        </button>
                      )}
                      {actions.canDelete && (
                        <button
                          type="button"
                          className="btn btn-danger btn-sm"
                          disabled={deleteTarget.isPending}
                          onClick={() => {
                            if (
                              window.confirm(
                                `Delete the @${target.username} record for this photo?`,
                              )
                            ) {
                              deleteTarget.mutate(target.id);
                            }
                          }}
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {sendTarget.isError && (
        <div className="state-msg state-error">
          Send failed: {sendTarget.error.message}
        </div>
      )}
      {deleteTarget.isError && (
        <div className="state-msg state-error">
          Delete failed: {deleteTarget.error.message}
        </div>
      )}
    </div>
  );
}
