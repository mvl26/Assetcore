<script setup lang="ts">
// Dashboard shell-router. Phase 1.2: render dashboard theo VAI TRÒ CHÍNH
// (primaryPersona = rank cao nhất từ role THẬT) — KHÔNG còn persona đang chọn.
// User nhiều role thấy dashboard của vai trò rank cao nhất. Một route /dashboard.
// Spec: docs/architecture/FE_Persona_Dashboards.md §2 + Navigation §7.ter.
import { computed } from 'vue'
import { usePersona } from '@/composables/usePersona'
import type { PersonaCode } from '@/constants/personas'

import AdminDashboardView from './personas/AdminDashboardView.vue'
import OpsmgrDashboardView from './personas/OpsmgrDashboardView.vue'
import WorkshopDashboardView from './personas/WorkshopDashboardView.vue'
import TechDashboardView from './personas/TechDashboardView.vue'
import ClinicalDashboardView from './personas/ClinicalDashboardView.vue'
import DocDashboardView from './personas/DocDashboardView.vue'
import StoreDashboardView from './personas/StoreDashboardView.vue'
import QaDashboardView from './personas/QaDashboardView.vue'

const { primaryPersona } = usePersona()

const PERSONA_VIEW: Record<PersonaCode, unknown> = {
  admin: AdminDashboardView,
  opsmgr: OpsmgrDashboardView,
  workshop: WorkshopDashboardView,
  tech: TechDashboardView,
  clinical: ClinicalDashboardView,
  doc: DocDashboardView,
  store: StoreDashboardView,
  qa: QaDashboardView,
}

// Component theo vai trò chính; fallback opsmgr (overview rộng nhất) nếu chưa xác định.
const activeView = computed(() => {
  const code = primaryPersona.value?.code as PersonaCode | undefined
  return (code && PERSONA_VIEW[code]) || OpsmgrDashboardView
})
</script>

<template>
  <component :is="activeView" />
</template>
