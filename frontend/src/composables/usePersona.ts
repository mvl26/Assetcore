// Copyright (c) 2026, AssetCore Team
//
// usePersona — nav derive TRỰC TIẾP từ ROLE THẬT (Phase 1.2).
// Spec: docs/architecture/FE_Persona_Navigation.md §7.ter
//
// Phase 1.2 (2026-06-01): GỠ persona switcher. KHÔNG còn "persona đang chọn"
// do user tự đổi — không setPersona/canSwitch/currentPersona/localStorage.
//
// - personas: tập persona role THẬT (frappe.get_roles) mở khoá (union, sort rank desc).
// - primaryPersona: persona rank cao nhất — chỉ để hiển thị header + default dashboard.
//
// Persona KHÔNG cấp quyền — chỉ là cách dịch role thật → tập module hiển thị.
// Mọi action vẫn gate ở BE DocPerm + route-guard capability + useCapabilities.

import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import {
  derivePersonas,
  derivePrimaryPersona,
  type Persona,
} from '@/constants/personas'

export function usePersona() {
  const auth = useAuthStore()
  const { roles } = storeToRefs(auth)

  // imm_roles legacy (prefix "IMM ") rỗng — nguồn chính là roles thật.
  const personas = computed<Persona[]>(() => derivePersonas(roles.value, []))
  const primaryPersona = computed<Persona | null>(() => derivePrimaryPersona(personas.value))

  return { personas, primaryPersona }
}
