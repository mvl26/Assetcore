// Copyright (c) 2026, AssetCore Team
//
// Persona catalog + RBAC inference — Single Source of Truth:
//   docs/architecture/FE_Persona_Navigation.md
//
// QUAN TRỌNG (production-safe): persona KHÔNG phải security boundary. Nó chỉ
// LỌC nav hiển thị ở sidebar. Mọi action vẫn gate bằng DocPerm (BE) +
// useCapabilities (FE). Đổi persona là client preference, không sinh audit.
//
// Nguồn inference là `roles` (frappe.get_roles) — danh sách role THẬT đầy đủ
// trả bởi api/layout.get_user_context. `imm_roles` (prefix "IMM ") hiện rỗng
// với role hiện tại nên chỉ gộp thêm cho khớp chữ ký, không phải nguồn chính.

/** moduleId hợp lệ — phải khớp key trong MODULE_NAV (AppSidebar.vue). */
export type ModuleId =
  | 'master' | 'system'
  | 'imm01' | 'imm02' | 'imm03' | 'imm04' | 'imm05' | 'imm06'
  | 'imm08' | 'imm09' | 'imm11' | 'imm12' | 'imm13' | 'imm14'
  | 'imm15' | 'imm16'

export type PersonaCode =
  | 'admin' | 'opsmgr' | 'workshop' | 'tech'
  | 'clinical' | 'doc' | 'store' | 'qa'

export interface Persona {
  /** Mã persona — khớp prototype docs/fe/index.html + localStorage 'ac_persona'. */
  code: PersonaCode
  /** Nhãn tiếng Việt hiển thị cho user (không leak mã hệ thống). */
  label: string
  /** Màu avatar (hex) — khớp prototype. */
  color: string
  /** User có ≥1 role trong set này → persona khả dụng. Tên role THẬT (fixtures/role.json). */
  inferenceRoles: readonly string[]
  /** moduleId sidebar hiển thị cho persona này (tra MODULE_NAV để build nav). */
  modules: readonly ModuleId[]
  /** Thứ hạng — chọn default + fallback (rank cao nhất hợp lệ). */
  rank: number
}

/** Role bypass — thấy mọi persona. Frappe-native + AssetCore super admin. */
export const SUPERUSER_ROLES: readonly string[] = [
  'Administrator',
  'System Manager',
  'AssetCore Super Admin',
] as const

// ─── 8 Persona (Core Doc §2) ────────────────────────────────────────────────
export const PERSONAS: readonly Persona[] = [
  {
    code: 'admin',
    label: 'Quản trị viên IT',
    color: '#0F172A',
    inferenceRoles: ['AssetCore Super Admin', 'System Manager', 'Administrator'],
    modules: [
      'system', 'master',
      'imm01', 'imm02', 'imm03', 'imm04', 'imm05', 'imm06',
      'imm08', 'imm09', 'imm11', 'imm12', 'imm13', 'imm15', 'imm16',
    ],
    rank: 100,
  },
  {
    code: 'opsmgr',
    label: 'Trưởng phòng VT-TTBYT',
    color: '#0E6FFF',
    inferenceRoles: [
      'Commissioning Manager', 'Needs Manager', 'Procurement Manager', 'Spec Manager',
    ],
    modules: ['master', 'imm01', 'imm02', 'imm03', 'imm04', 'system'],
    rank: 70,
  },
  {
    code: 'workshop',
    label: 'Trưởng xưởng kỹ thuật',
    color: '#0891B2',
    inferenceRoles: [
      'PM Manager', 'Repair Manager', 'Calibration Manager', 'Corrective Manager',
    ],
    modules: ['imm08', 'imm09', 'imm11', 'imm12', 'master', 'imm15'],
    rank: 60,
  },
  {
    code: 'qa',
    label: 'Cán bộ QA / Kiểm toán',
    color: '#DC2626',
    inferenceRoles: ['Compliance Manager', 'Compliance User', 'AssetCore Auditor'],
    modules: ['imm16', 'system'],
    rank: 50,
  },
  {
    code: 'tech',
    label: 'Kỹ thuật viên',
    color: '#16A34A',
    inferenceRoles: [
      'PM User', 'Repair User', 'Calibration User', 'Corrective User',
    ],
    modules: ['imm08', 'imm09', 'imm11', 'master'],
    rank: 40,
  },
  {
    code: 'doc',
    label: 'Cán bộ hồ sơ',
    color: '#475569',
    inferenceRoles: ['Document Manager', 'Document User', 'Training Manager'],
    modules: ['imm05', 'imm06', 'master'],
    rank: 35,
  },
  {
    code: 'store',
    label: 'Thủ kho phụ tùng',
    color: '#B45309',
    inferenceRoles: ['Inventory Manager', 'Inventory User'],
    modules: ['imm15', 'imm13'],
    rank: 35,
  },
  {
    code: 'clinical',
    label: 'Trưởng khoa lâm sàng',
    color: '#7C3AED',
    inferenceRoles: ['Corrective User', 'Corrective Manager'],
    modules: ['imm12', 'master'],
    rank: 30,
  },
] as const

const PERSONA_BY_CODE: Record<string, Persona> = Object.fromEntries(
  PERSONAS.map((p) => [p.code, p]),
)

export function getPersona(code: string | null | undefined): Persona | null {
  if (!code) return null
  return PERSONA_BY_CODE[code] ?? null
}

/**
 * derivePersonas — Core Doc §3.
 * Trả danh sách persona user đủ quyền, sort theo rank giảm dần.
 * - Superuser (Administrator/System Manager/AssetCore Super Admin) → cả 8.
 * - Còn lại: persona khả dụng nếu (roles ∪ imm_roles) ∩ inferenceRoles ≠ ∅.
 * - Không role khớp → [].
 */
export function derivePersonas(
  roles: readonly string[] = [],
  immRoles: readonly string[] = [],
): Persona[] {
  const all = new Set<string>([...roles, ...immRoles])

  const isSuperuser = SUPERUSER_ROLES.some((r) => all.has(r))
  const sorted = [...PERSONAS].sort((a, b) => b.rank - a.rank)

  if (isSuperuser) return sorted

  return sorted.filter((p) => p.inferenceRoles.some((r) => all.has(r)))
}

/**
 * Chọn persona hiện tại hợp lệ từ giá trị persisted.
 * - persisted hợp lệ (nằm trong available) → giữ.
 * - không hợp lệ / null → fallback persona rank cao nhất; null nếu available rỗng.
 */
export function resolveCurrentPersona(
  persisted: string | null | undefined,
  available: readonly Persona[],
): Persona | null {
  if (available.length === 0) return null
  const match = available.find((p) => p.code === persisted)
  if (match) return match
  // available đã sort rank desc trong derivePersonas → phần tử đầu là cao nhất.
  return [...available].sort((a, b) => b.rank - a.rank)[0] ?? null
}
