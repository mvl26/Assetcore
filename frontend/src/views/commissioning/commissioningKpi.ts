// IMM-04 list-page KPI strip mapping.
// Core Doc: docs/imm-04/06_Frontend_Design.md §3.1 · ref docs/fe/04-commissioning/commissioning-list.html
// Pure (no Vue/store deps) → unit-testable. Source: get_dashboard_stats → DashboardStats.kpis.
import type { WoKpiItem } from '@/components/common/WorkOrderKpiStrip.vue'
import type { KpiStats, WorkflowState } from '@/types/imm04'

/** KPI item + optional quick-filter target. `filterState === ''` → clear state filter. */
export interface CommissioningKpiItem extends WoKpiItem {
  /** workflow_state to quick-filter on click; '' clears filter; undefined = display-only. */
  filterState?: WorkflowState | ''
}

/**
 * Map BE KPI stats to the list-page KPI strip items (VI labels, semantic colors).
 * Clickable KPIs carry `filterState`; "Quá hạn SLA" is display-only because the list
 * endpoint has no `overdue` filter param yet (see Core Doc §3.1).
 */
export function commissioningKpiItems(kpis: KpiStats | null | undefined): CommissioningKpiItem[] {
  if (!kpis) return []
  return [
    // Nhãn hiển thị tiếng Việt (Core Doc §3.1 + bảng i18n). filterState giữ
    // workflow_state gốc tiếng Anh làm khoá lọc — KHÔNG để raw English ra UI.
    { label: 'Phiếu đang mở', value: kpis.pending_count, color: 'primary', filterState: '' },
    { label: 'Tạm giữ lâm sàng', value: kpis.hold_count, color: 'warning', filterState: 'Clinical Hold' },
    { label: 'NC mở', value: kpis.open_nc_count, color: 'danger', filterState: 'Non Conformance' },
    { label: 'Bàn giao tháng này', value: kpis.released_this_month, color: 'success', filterState: 'Clinical Release' },
    { label: 'Quá hạn SLA', value: kpis.overdue_sla, color: 'neutral' },
  ]
}
