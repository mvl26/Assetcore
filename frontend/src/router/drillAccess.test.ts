// Copyright (c) 2026, AssetCore Team
//
// TDD (Core Doc §9.5 #9): drill chỉ render clickable khi user THỰC SỰ vào được
// route đích. Nếu thiếu capability → KHÔNG render link tới /unauthorized (bug
// opsmgr 2026-06-02: KPI "PM/CM/Sự cố" drill về route opsmgr không có quyền →
// click rớt /unauthorized). canAccessDrill mirror route-guard moduleIdToCap.
import { describe, it, expect } from 'vitest'
import { canAccessDrill } from './routeAccess'

// ctx.can stub theo capability set opsmgr THẬT (live session 2026-06-02, SAU khi
// cấp read-only oversight): data.read + commissioning/needs/spec/procurement.read
// = true, VÀ pm.read + repair.read + corrective.read = TRUE (read-only oversight
// imm08/09/12 — DocPerm read trên PM/CM/Incident). Vẫn THIẾU: calibration.read,
// inventory.read, compliance.read.
const opsmgrCan = (cap: string): boolean =>
  [
    'data.read',
    'needs.read',
    'spec.read',
    'procurement.read',
    'commissioning.read',
    'pm.read',
    'repair.read',
    'corrective.read',
  ].includes(cap)

const adminCan = (): boolean => true

describe('canAccessDrill', () => {
  it('cho phép drill /assets (master → không cần cap đặc thù) với opsmgr', () => {
    expect(canAccessDrill('/assets', opsmgrCan)).toBe(true)
  })

  it('CHO PHÉP drill /pm/work-orders (imm08 pm.read) — opsmgr nay có read-only oversight', () => {
    expect(canAccessDrill('/pm/work-orders', opsmgrCan)).toBe(true)
  })

  it('CHO PHÉP drill /cm/work-orders (imm09 repair.read) — opsmgr nay có read-only oversight', () => {
    expect(canAccessDrill('/cm/work-orders', opsmgrCan)).toBe(true)
  })

  it('CHO PHÉP drill /incidents/list (imm12 corrective.read) — opsmgr nay có read-only oversight', () => {
    expect(canAccessDrill('/incidents/list', opsmgrCan)).toBe(true)
  })

  it('VẪN CHẶN drill /spare-parts (imm15 inventory.read) và /capas (imm16) — ngoài phạm vi opsmgr', () => {
    expect(canAccessDrill('/spare-parts', opsmgrCan)).toBe(false)
    expect(canAccessDrill('/capas', opsmgrCan)).toBe(false)
  })

  it('VẪN CHẶN drill /calibration (imm11) — opsmgr không có calibration.read', () => {
    expect(canAccessDrill('/calibration/schedules', opsmgrCan)).toBe(false)
  })

  it('admin (super) vào được mọi drill', () => {
    expect(canAccessDrill('/pm/work-orders', adminCan)).toBe(true)
    expect(canAccessDrill('/incidents/list', adminCan)).toBe(true)
    expect(canAccessDrill('/cm/work-orders', adminCan)).toBe(true)
  })

  it('route ngoài map module → mặc định cho phép (không chặn nhầm)', () => {
    expect(canAccessDrill('/some/unknown/path', opsmgrCan)).toBe(true)
  })

  it('path rỗng → cho phép (không vỡ)', () => {
    expect(canAccessDrill('', opsmgrCan)).toBe(true)
  })

  // ─── R1 §9.4.9: admin dashboard drill (user-profiles / admin-roles / audit) ──
  it('admin (super) drill /user-profiles + /admin/roles + /audit-trail đều cho phép', () => {
    expect(canAccessDrill('/user-profiles', adminCan)).toBe(true)
    expect(canAccessDrill('/admin/roles', adminCan)).toBe(true)
    expect(canAccessDrill('/audit-trail', adminCan)).toBe(true)
  })

  it('/audit-trail gate đúng audit.read (KHÔNG phải compliance.read — sửa drift §9.4.9)', () => {
    // qa có audit.read nhưng giả định KHÔNG có compliance.read → vẫn drill được.
    const qaAuditOnly = (cap: string): boolean => cap === 'audit.read'
    expect(canAccessDrill('/audit-trail', qaAuditOnly)).toBe(true)
    // user KHÔNG có audit.read → chặn (fail-closed).
    const noAudit = (cap: string): boolean => cap === 'data.read'
    expect(canAccessDrill('/audit-trail', noAudit)).toBe(false)
  })

  it('/user-profiles + /admin/roles gate đúng data.admin (system, không module cap)', () => {
    const dataAdmin = (cap: string): boolean => cap === 'data.admin'
    expect(canAccessDrill('/user-profiles', dataAdmin)).toBe(true)
    expect(canAccessDrill('/admin/roles', dataAdmin)).toBe(true)
    const noAdmin = (cap: string): boolean => cap === 'data.read'
    expect(canAccessDrill('/user-profiles', noAdmin)).toBe(false)
    expect(canAccessDrill('/admin/roles', noAdmin)).toBe(false)
  })
})
