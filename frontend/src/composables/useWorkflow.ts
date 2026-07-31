// Copyright (c) 2026, AssetCore Team
// Composable: workflow transitions, state colors, permission checks

import { computed } from 'vue'
import type { WorkflowState, WorkflowTransition } from '@/types/imm04'

// ─────────────────────────────────────────────────────────────────────────────
// STATE CONFIG
// ─────────────────────────────────────────────────────────────────────────────

export interface StateConfig {
  label: string
  color: 'gray' | 'blue' | 'yellow' | 'red' | 'green' | 'purple' | 'orange'
  /** Tailwind bg + text classes */
  badgeClass: string
  /** Icon name (for display) */
  icon: string
  /** State cuối cùng trong quy trình */
  isTerminal: boolean
}

const STATE_CONFIG: Record<WorkflowState, StateConfig> = {
  Draft: {
    label: 'Nháp',
    color: 'gray',
    badgeClass: 'bg-gray-100 text-gray-800',
    icon: 'pencil',
    isTerminal: false,
  },
  'Pending Doc Verify': {
    label: 'Chờ kiểm tra tài liệu',
    color: 'purple',
    badgeClass: 'bg-purple-100 text-purple-800',
    icon: 'file-text',
    isTerminal: false,
  },
  'To Be Installed': {
    label: 'Chờ lắp đặt',
    color: 'blue',
    badgeClass: 'bg-blue-100 text-blue-800',
    icon: 'calendar',
    isTerminal: false,
  },
  Installing: {
    label: 'Đang lắp đặt',
    color: 'yellow',
    badgeClass: 'bg-yellow-100 text-yellow-800',
    icon: 'wrench',
    isTerminal: false,
  },
  Identification: {
    label: 'Nhận dạng',
    color: 'blue',
    badgeClass: 'bg-blue-100 text-blue-800',
    icon: 'qr-code',
    isTerminal: false,
  },
  'Initial Inspection': {
    label: 'Kiểm tra lần đầu',
    color: 'blue',
    badgeClass: 'bg-indigo-100 text-indigo-800',
    icon: 'clipboard-check',
    isTerminal: false,
  },
  'Non Conformance': {
    label: 'Không phù hợp',
    color: 'orange',
    badgeClass: 'bg-orange-100 text-orange-800',
    icon: 'alert-triangle',
    isTerminal: false,
  },
  'Clinical Hold': {
    label: 'Tạm giữ lâm sàng',
    color: 'red',
    badgeClass: 'bg-red-100 text-red-800',
    icon: 'pause-circle',
    isTerminal: false,
  },
  'Re Inspection': {
    label: 'Kiểm tra lại',
    color: 'orange',
    badgeClass: 'bg-orange-100 text-orange-800',
    icon: 'refresh',
    isTerminal: false,
  },
  'Clinical Release': {
    label: 'Phát hành lâm sàng',
    color: 'green',
    badgeClass: 'bg-green-100 text-green-800',
    icon: 'check-circle',
    isTerminal: true,
  },
  'Return To Vendor': {
    label: 'Trả lại nhà cung cấp',
    color: 'red',
    badgeClass: 'bg-red-200 text-red-900',
    icon: 'arrow-left',
    isTerminal: true,
  },
}

// ─────────────────────────────────────────────────────────────────────────────
// ACTION CONFIG — màu nút action
// ─────────────────────────────────────────────────────────────────────────────

export interface ActionConfig {
  label: string
  variant: 'primary' | 'secondary' | 'success' | 'warning' | 'danger'
  icon: string
  /** Cần confirm dialog trước khi thực hiện */
  requiresConfirm?: boolean
  requireConfirm?: boolean
  confirmMessage?: string
  buttonClass?: string
}

const ACTION_CONFIG: Record<string, ActionConfig> = {
  'Gửi kiểm tra tài liệu': {
    label: 'Gửi kiểm tra tài liệu',
    variant: 'secondary',
    icon: 'file-text',
  },
  'Xác nhận đủ tài liệu': {
    label: 'Xác nhận đủ tài liệu',
    variant: 'primary',
    icon: 'check-circle',
  },
  'Bắt đầu lắp đặt': {
    label: 'Bắt đầu lắp đặt',
    variant: 'primary',
    icon: 'tool',
    requiresConfirm: false,
  },
  'Lắp đặt hoàn thành': {
    label: 'Lắp đặt hoàn thành',
    variant: 'success',
    icon: 'check',
  },
  'Bắt đầu kiểm tra': {
    label: 'Bắt đầu kiểm tra',
    variant: 'primary',
    icon: 'clipboard',
  },
  'Báo cáo lỗi baseline': {
    label: 'Báo cáo lỗi baseline',
    variant: 'warning',
    icon: 'alert-triangle',
  },
  'Phê duyệt phát hành': {
    label: 'Phê duyệt phát hành',
    variant: 'success',
    icon: 'check-circle',
    requiresConfirm: true,
    confirmMessage: 'Xác nhận phát hành thiết bị vào sử dụng?',
  },
  'Giữ lâm sàng': {
    label: 'Giữ lâm sàng',
    variant: 'warning',
    icon: 'pause-circle',
    requiresConfirm: true,
    confirmMessage: 'Xác nhận giữ thiết bị chờ giấy phép?',
  },
  'Gỡ giữ lâm sàng': {
    label: 'Gỡ giữ lâm sàng',
    variant: 'primary',
    icon: 'unlock',
  },
  'Báo cáo DOA': {
    label: 'Báo cáo DOA',
    variant: 'danger',
    icon: 'alert-circle',
    requiresConfirm: true,
    confirmMessage: 'Xác nhận thiết bị DOA (Dead on Arrival)?',
  },
  'Trả lại nhà cung cấp': {
    label: 'Trả lại nhà cung cấp',
    variant: 'danger',
    icon: 'x-circle',
    requiresConfirm: true,
    confirmMessage: 'Xác nhận trả thiết bị về nhà cung cấp? Hành động này không thể hoàn tác.',
  },
  'Khắc phục xong': {
    label: 'Khắc phục xong',
    variant: 'success',
    icon: 'check',
  },
  'Phê duyệt sau tái kiểm': {
    label: 'Phê duyệt sau tái kiểm',
    variant: 'success',
    icon: 'check-circle',
    requiresConfirm: true,
  },
  'Báo cáo sự cố': {
    label: 'Báo cáo sự cố',
    variant: 'danger',
    icon: 'alert-triangle',
  },
  'Gửi lại': {
    label: 'Gửi lại',
    variant: 'secondary',
    icon: 'refresh-cw',
  },
  'Yêu cầu bổ sung tài liệu': {
    label: 'Yêu cầu bổ sung tài liệu',
    variant: 'warning',
    icon: 'file-minus',
  },
}

// ─────────────────────────────────────────────────────────────────────────────
// COMPOSABLE
// ─────────────────────────────────────────────────────────────────────────────

export function useWorkflow(
  currentState: () => WorkflowState | undefined,
  allowedTransitions: () => WorkflowTransition[],
) {
  /** Config của state hiện tại */
  const stateConfig = computed<StateConfig | null>(() => {
    const state = currentState()
    if (!state) return null
    return STATE_CONFIG[state] ?? null
  })

  /** Badge class của state hiện tại */
  const badgeClass = computed(() => stateConfig.value?.badgeClass ?? 'bg-gray-100 text-gray-700')

  /** Label tiếng Việt của state hiện tại */
  const stateLabel = computed(() => stateConfig.value?.label ?? currentState() ?? '')

  /** State có phải terminal (cuối workflow) không */
  const isTerminalState = computed(() => stateConfig.value?.isTerminal ?? false)

  /**
   * Danh sách hành động workflow render ra nút — SERVER-DRIVEN (GATE-8 / LL-FE-51).
   *
   * BE `services/imm04._get_workflow_transitions()` ĐÃ lọc `t.allowed in frappe.get_roles(user)`
   * ⇒ `allowed_transitions` là SSoT: mọi phần tử trả về đều là hành động user hiện tại
   * được phép. TUYỆT ĐỐI KHÔNG lọc lại bằng TÊN ROLE ở client (`auth.roles.includes(...)`):
   * bộ lọc đó chỉ có thể TRỪ BỚT, và `auth.roles` là bản CACHE trong localStorage
   * (persona "thiu" khi quản trị đổi role/role-profile giữa phiên) — nguồn khác với
   * `frappe.get_roles()` mà BE vừa dùng. Lệch một mắt xích ⇒ nút biến mất ÂM THẦM
   * (anti-pattern RBAC dead-gate: gate bằng role-name → fail không thông báo), đúng ca
   * CTA "Báo cáo lỗi baseline" (CR-54 §2) — hành động DUY NHẤT thoát baseline không đạt.
   * Quyền thật vẫn do BE chặn ở `transition_state`; FE chỉ render đúng cái BE đã cho.
   *
   * Chỉ giữ de-dup theo `action` (1 action có nhiều dòng transition cho nhiều role).
   */
  const filteredActions = computed<WorkflowTransition[]>(() => {
    const seen = new Set<string>()
    return allowedTransitions().filter((t) => {
      if (seen.has(t.action)) return false
      seen.add(t.action)
      return true
    })
  })

  /** Lấy config của một action */
  function getActionConfig(action: string): ActionConfig {
    return ACTION_CONFIG[action] ?? { label: action, variant: 'secondary', icon: 'arrow-right', requiresConfirm: false }
  }

  /** Kiểm tra user có thể transition sang state chỉ định không */
  function canTransitionTo(nextState: WorkflowState): boolean {
    return filteredActions.value.some((t) => t.next_state === nextState)
  }

  /** Kiểm tra user có thể thực hiện action chỉ định không */
  function canPerformAction(action: string): boolean {
    return filteredActions.value.some((t) => t.action === action)
  }

  /** Lấy config state bất kỳ */
  function getStateConfig(state: WorkflowState): StateConfig {
    return (
      STATE_CONFIG[state] ?? {
        label: state,
        color: 'gray',
        badgeClass: 'bg-gray-100 text-gray-700',
        icon: 'circle',
        isTerminal: false,
      }
    )
  }

  return {
    stateConfig,
    badgeClass,
    stateLabel,
    isTerminalState,
    filteredActions,
    getActionConfig,
    canTransitionTo,
    canPerformAction,
    getStateConfig,
    STATE_CONFIG,
  }
}

/** Standalone helper để lấy state config ngoài composable */
export function getStateConfig(state: WorkflowState): StateConfig {
  const found = STATE_CONFIG[state]
  if (found) return found
  return { label: `[${state}]`, color: 'gray', badgeClass: 'bg-gray-100 text-gray-700', icon: 'circle', isTerminal: false }
}
