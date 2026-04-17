export const DOC_STATE_LABEL: Record<string, string> = {
  Draft: 'Draft',
  Pending_Review: 'Chờ duyệt',
  Active: 'Active',
  Expired: 'Hết hạn',
  Archived: 'Lưu trữ',
  Rejected: 'Từ chối',
}

export function stateLabel(state: string): string {
  return DOC_STATE_LABEL[state] ?? state
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return '—'
  return new Date(date).toLocaleDateString('vi-VN')
}

export function formatDatetime(dt: string | null | undefined): string {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('vi-VN')
}
