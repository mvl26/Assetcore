import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function usePermissions() {
  const auth = useAuthStore()

  const roles = computed<string[]>(() => auth.user?.roles ?? [])

  const isAdmin = computed(() => roles.value.includes('System Manager') || roles.value.includes('Administrator'))
  const isQA = computed(() => roles.value.includes('Workshop Head') || roles.value.includes('VP Block2'))
  const isClinicalHead = computed(() => roles.value.includes('Clinical Head'))
  const isTechnician = computed(() => roles.value.includes('HTM Technician') || roles.value.includes('Biomed Engineer'))

  const canApproveRelease = computed(() => isAdmin.value || isQA.value)
  const canViewFinancials = computed(() => isAdmin.value || roles.value.includes('VP Block2'))

  return { roles, isAdmin, isQA, isClinicalHead, isTechnician, canApproveRelease, canViewFinancials }
}
