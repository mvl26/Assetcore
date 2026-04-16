// Copyright (c) 2026, AssetCore Team
// Composable: workflow transitions, state colors, permission checks

import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
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
  Identification: {
    label: 'Nhận dạng',
    color: 'blue',
    badgeClass: 'bg-blue-100 text-blue-800',
    icon: 'qr-code',
    isTerminal: false,
  },
  Installing: {
    label: 'Đang lắp đặt',
    color: 'yellow',
    badgeClass: 'bg-yellow-100 text-yellow-800',
    icon: 'wrench',
    isTerminal: false,
  },
  Initial_Inspection: {
    label: 'Kiểm tra lần đầu',
    color: 'blue',
    badgeClass: 'bg-indigo-100 text-indigo-800',
    icon: 'clipboard-check',
    isTerminal: false,
  },
  Clinical_Hold: {
    label: 'Tạm giữ lâm sàng',
    color: 'red',
    badgeClass: 'bg-red-100 text-red-800',
    icon: 'pause-circle',
    isTerminal: false,
  },
  Re_Inspection: {
    label: 'Kiểm tra lại',
    color: 'orange',
    badgeClass: 'bg-orange-100 text-orange-800',
    icon: 'refresh',
    isTerminal: false,
  },
  Pending_Release: {
    label: 'Chờ phê duyệt',
    color: 'purple',
    badgeClass: 'bg-purple-100 text-purple-800',
    icon: 'clock',
    isTerminal: false,
  },
  Clinical_Release: {
    label: 'Phát hành lâm sàng',
    color: 'green',
    badgeClass: 'bg-green-100 text-green-800',
    icon: 'check-circle',
    isTerminal: true,
  },
  Return_To_Vendor: {
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
  /** Tailwind button classes */
  buttonClass: string
  /** Cần confirm dialog trước khi thực hiện */
  requireConfirm: boolean
  confirmMessage?: string
}

const ACTION_CONFIG: Record<string, ActionConfig> = {
  'Bắt đầu Nhận dạng': {
    label: 'Bắt đầu Nhận dạng',
    buttonClass: 'bg-blue-600 hover:bg-blue-700 text-white',
    requireConfirm: false,
  },
  'Bắt đầu Lắp đặt': {
    label: 'Bắt đầu Lắp đặt',
    buttonClass: 'bg-yellow-500 hover:bg-yellow-600 text-white',
    requireConfirm: false,
  },
  'Gửi Kiểm tra': {
    label: 'Gửi Kiểm tra',
    buttonClass: 'bg-indigo-600 hover:bg-indigo-700 text-white',
    requireConfirm: false,
  },
  'Giữ lâm sàng': {
    label: 'Tạm giữ lâm sàng',
    buttonClass: 'bg-red-600 hover:bg-red-700 text-white',
    requireConfirm: true,
    confirmMessage:
      'Bạn có chắc muốn đặt phiếu vào trạng thái Clinical Hold? Thiết bị sẽ tạm thời không được phát hành.',
  },
  'Kiểm tra lại': {
    label: 'Yêu cầu Kiểm tra lại',
    buttonClass: 'bg-orange-500 hover:bg-orange-600 text-white',
    requireConfirm: false,
  },
  'Đề nghị Phát hành': {
    label: 'Đề nghị Phát hành',
    buttonClass: 'bg-purple-600 hover:bg-purple-700 text-white',
    requireConfirm: false,
  },
  'Phê duyệt Phát hành': {
    label: 'Phê duyệt Phát hành',
    buttonClass: 'bg-green-600 hover:bg-green-700 text-white',
    requireConfirm: true,
    confirmMessage:
      'Bạn có chắc muốn Phê duyệt Phát hành thiết bị này? Hành động này không thể hoàn tác và sẽ tạo tài sản trong hệ thống.',
  },
  'Trả lại hãng': {
    label: 'Trả lại nhà cung cấp',
    buttonClass: 'bg-red-700 hover:bg-red-800 text-white',
    requireConfirm: true,
    confirmMessage:
      'Bạn có chắc muốn trả lại thiết bị này cho nhà cung cấp? Phiếu sẽ bị đóng.',
  },
}

// ─────────────────────────────────────────────────────────────────────────────
// COMPOSABLE
// ─────────────────────────────────────────────────────────────────────────────

export function useWorkflow(
  currentState: () => WorkflowState | undefined,
  allowedTransitions: () => WorkflowTransition[],
) {
  const auth = useAuthStore()

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
   * Danh sách actions được phép (có filtered theo role user hiện tại).
   * Backend đã filter, nhưng composable filter lại cho an toàn UI.
   */
  const filteredActions = computed<WorkflowTransition[]>(() => {
    const userRoles = auth.roles
    return allowedTransitions().filter((t) => userRoles.includes(t.allowed_role))
  })

  /** Lấy config của một action */
  function getActionConfig(action: string): ActionConfig {
    return (
      ACTION_CONFIG[action] ?? {
        label: action,
        buttonClass: 'bg-gray-600 hover:bg-gray-700 text-white',
        requireConfirm: false,
      }
    )
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
