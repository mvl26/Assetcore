// Copyright (c) 2026, AssetCore Team
//
// usePersona — persona-scoped navigation state (shared singleton).
// Spec: docs/architecture/FE_Persona_Navigation.md
//
// - availablePersonas: derive từ auth store roles (RBAC THẬT).
// - currentPersona: persisted 'ac_persona' nếu hợp lệ, else fallback rank cao nhất.
// - canSwitch: >1 persona → topbar hiện dropdown; =1 → label tĩnh; =0 → ẩn.
// - setPersona: chỉ chấp nhận persona đủ quyền (production-safe anti-leak).
//
// Persona KHÔNG cấp quyền — chỉ lọc nav. Mọi action vẫn gate ở BE + capability.

import { computed, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import {
  derivePersonas,
  resolveCurrentPersona,
  type Persona,
  type PersonaCode,
} from '@/constants/personas'

const STORAGE_KEY = 'ac_persona'

function readPersisted(): string | null {
  try { return localStorage.getItem(STORAGE_KEY) }
  catch { return null }
}
function writePersisted(code: string): void {
  try { localStorage.setItem(STORAGE_KEY, code) }
  catch { /* private mode / quota — bỏ qua, state vẫn chạy in-memory */ }
}

// Singleton state — chia sẻ giữa AppSidebar + AppTopBar (giống useSidebar.ts).
const persistedCode = ref<string | null>(readPersisted())

export function usePersona() {
  const auth = useAuthStore()
  const { roles } = storeToRefs(auth)

  // imm_roles legacy (prefix "IMM ") — nguồn chính là roles. Truyền để khớp spec.
  const availablePersonas = computed<Persona[]>(() => derivePersonas(roles.value, []))

  const currentPersona = computed<Persona | null>(() =>
    resolveCurrentPersona(persistedCode.value, availablePersonas.value),
  )

  const canSwitch = computed<boolean>(() => availablePersonas.value.length > 1)

  // Nếu persona persisted không hợp lệ → tự ghi lại giá trị fallback hợp lệ,
  // để lần load sau ổn định và localStorage không giữ rác/giá trị mất quyền.
  watch(
    [currentPersona, availablePersonas],
    ([cur]) => {
      if (cur && cur.code !== persistedCode.value) {
        persistedCode.value = cur.code
        writePersisted(cur.code)
      }
    },
    { immediate: true },
  )

  /** Đổi persona — chỉ chấp nhận persona user đủ quyền. */
  function setPersona(code: PersonaCode | string): boolean {
    const allowed = availablePersonas.value.some((p) => p.code === code)
    if (!allowed) return false
    persistedCode.value = code
    writePersisted(code)
    return true
  }

  return { availablePersonas, currentPersona, canSwitch, setPersona }
}
