// Copyright (c) 2026, AssetCore Team
//
// Dashboard API client — persona-scoped dashboards (Phase 2).
// Spec: docs/architecture/FE_Persona_Dashboards.md
// Mirrors BE: assetcore.api.dashboard.get_persona_dashboard
import { frappeGet } from './helpers'
import type { PersonaCode } from '@/constants/personas'

const BASE = '/api/method/assetcore.api.dashboard'

/** KPI card chuẩn hoá — khớp BE _kpi(). tone drive màu nền card. */
export interface PersonaKpi {
  key: string
  label_vi: string
  value: number | string | null
  foot_vi: string
  tone: 'primary' | 'info' | 'ok' | 'warn' | 'danger'
}

/** Payload mỗi persona — sections shape khác nhau theo persona (Core Doc §5). */
export interface PersonaDashboard {
  persona: string
  generated_at: string
  kpis: PersonaKpi[]
  sections: Record<string, unknown>
}

/** GET get_persona_dashboard?persona=<code>. frappeGet đã unwrap envelope → trả T trực tiếp. */
export function getPersonaDashboard(persona: PersonaCode | string): Promise<PersonaDashboard> {
  return frappeGet(`${BASE}.get_persona_dashboard`, { persona })
}

/** Type guard helper — đọc một section dạng mảng row (an toàn, không dùng `any`). */
export function sectionRows(
  sections: Record<string, unknown> | undefined,
  key: string,
): Record<string, unknown>[] {
  const v = sections?.[key]
  return Array.isArray(v) ? (v as Record<string, unknown>[]) : []
}

/** Đọc một section dạng object (vd maintenance_kpi). */
export function sectionObject(
  sections: Record<string, unknown> | undefined,
  key: string,
): Record<string, unknown> {
  const v = sections?.[key]
  return v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : {}
}
