import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function usePermissions() {
  const auth = useAuthStore()

  const roles = computed<string[]>(() => auth.user?.roles ?? [])

  const isAdmin = computed(() => roles.value.includes('System Manager') || roles.value.includes('Administrator'))
  const isQA = computed(() => roles.value.includes('IMM Workshop Lead') || roles.value.includes('IMM Operations Manager'))
  const isClinicalHead = computed(() => roles.value.includes('IMM Department Head'))
  const isTechnician = computed(() => roles.value.includes('IMM Technician') || roles.value.includes('IMM Biomed Technician'))

  const canApproveRelease = computed(() => isAdmin.value || isQA.value)
  const canViewFinancials = computed(() => isAdmin.value || roles.value.includes('IMM Operations Manager'))

  return { roles, isAdmin, isQA, isClinicalHead, isTechnician, canApproveRelease, canViewFinancials }
}
