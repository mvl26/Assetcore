// Copyright (c) 2026, AssetCore Team
//
// Core Doc §9.7 + §9.9 — row→source-record drill cho persona dashboard sections.
// Mỗi loại section row (PM WO / CM WO / Document / Commissioning / Incident /
// Needs / Spare Part) → route DETAIL record nguồn (CLAUDE.md §5, §10 root_record).
// Gate canAccessDrill: thiếu cap route đích → trả null (row tĩnh, KHÔNG dead-end).
import type { RouteLocationRaw } from 'vue-router'
import { canAccessDrill } from '@/router/routeAccess'
import { useCapabilities } from '@/composables/useCapabilities'

type Row = Record<string, unknown>
type RowTo = (row: Row) => RouteLocationRaw | null

function str(v: unknown): string {
  return v === null || v === undefined ? '' : String(v)
}

/** Factory: trả rowTo cho 1 base-route detail dùng field id (mặc định 'name').
 *  null nếu id rỗng hoặc thiếu quyền route. */
function detailDrill(
  base: string,
  can: (cap: string) => boolean,
  idField = 'name',
  gateRoute?: string,
): RowTo {
  return (row: Row) => {
    const id = str(row[idField])
    if (!id) return null
    if (!canAccessDrill(gateRoute ?? base, can)) return null
    return { path: `${base}/${encodeURIComponent(id)}` }
  }
}

export function useSectionDrill() {
  const { can } = useCapabilities()
  return {
    /** PM Work Order row → /pm/work-orders/:name */
    pmWo: detailDrill('/pm/work-orders', can),
    /** CM Work Order row → /cm/work-orders/:name */
    cmWo: detailDrill('/cm/work-orders', can),
    /** Document row → /documents/view/:name (gate /documents) */
    document: detailDrill('/documents/view', can, 'name', '/documents'),
    /** Commissioning row → /commissioning/:name */
    commissioning: detailDrill('/commissioning', can),
    /** Incident row → /incidents/:name (gate /incidents/list) */
    incident: detailDrill('/incidents', can, 'name', '/incidents/list'),
    /** Spare Part row → /spare-parts/:spare_part (id ở field spare_part) */
    sparePart: detailDrill('/spare-parts', can, 'spare_part'),
    /** Needs Request row → /needs-requests/:name */
    needs: detailDrill('/needs-requests', can),
    /** CAPA row → /capas/:name (gate /capas = compliance.read) */
    capa: detailDrill('/capas', can, 'name', '/capas'),
    /** Internal Audit row → /compliance/audits/:name (gate /compliance) */
    audit: detailDrill('/compliance/audits', can, 'name', '/compliance'),
    /** Tự do: detail theo base + field tuỳ chọn. */
    custom: (base: string, idField = 'name', gateRoute?: string) =>
      detailDrill(base, can, idField, gateRoute),
  }
}
