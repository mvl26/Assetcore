// Copyright (c) 2026, AssetCore Team
// CR-75 — thẻ "Trạng thái hồ sơ pháp lý" (consumer IMM-04) phải NÓI THẬT.
//
// RED trước fix (2026-07-25): `CommissioningForm.vue` quyết định tông màu bằng
// `imm05IsCompliant` suy ra từ SO CHUỖI `document_status === 'Compliant'` ở
// `CommissioningDetailView.vue:101-104`, in THẲNG enum tiếng Anh ra badge
// (`{{ imm05DocStatus ?? 'Chưa có dữ liệu' }}`) và vẽ thanh % từ
// `completeness_pct` — hằng `0` phía BE ⇒ hồ sơ đủ vẫn hiện "0% đầy đủ" + đỏ.
//
// Hợp đồng sau CR-75 (docs/imm-05/06_Frontend_Design.md §4.4):
//  - quyết định tuân thủ = khoá SỐ `is_compliant`, KHÔNG so chuỗi;
//  - nhãn hiển thị = tiếng Việt qua `dossierStatusLabel()` (LL-FE-53);
//  - % là số thật kèm mẫu số `required_satisfied/required_total`;
//  - `expired_required[]` (gia hạn) tách khỏi `missing_required[]` (bổ sung mới).
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import DocumentDossierCard from '@/components/commissioning/DocumentDossierCard.vue'

type Props = InstanceType<typeof DocumentDossierCard>['$props']

function mountCard(props: Partial<Props> = {}) {
  return mount(DocumentDossierCard, {
    props: {
      documentStatus: 'Compliant',
      isCompliant: true,
      completenessPct: 100,
      requiredTotal: 4,
      requiredSatisfied: 4,
      missingRequired: [],
      expiredRequired: [],
      expiringRequired: [],
      hiddenCount: 0,
      ...props,
    } as Props,
  })
}

/** Mọi khoá enum SSoT — KHÔNG được rò ra UI ở bất kỳ nhánh nào. */
const EN_ENUMS = ['Compliant', 'Compliant (Exempt)', 'Expiring_Soon', 'Non-Compliant', 'Incomplete', 'Complete']

describe('DocumentDossierCard — CR-75 mức đầy đủ hồ sơ pháp lý', () => {
  // ── TC-FE-DOSSIER-01 ──────────────────────────────────────────────────────
  it('TC-FE-DOSSIER-01: is_compliant=0 + Non-Compliant ⇒ thẻ đỏ, nhãn VI, % thật, dòng "Hết hạn:"', () => {
    const w = mountCard({
      documentStatus: 'Non-Compliant',
      isCompliant: false,
      completenessPct: 50,
      requiredTotal: 4,
      requiredSatisfied: 2,
      missingRequired: ['Hợp đồng bảo trì'],
      expiredRequired: ['Chứng nhận đăng ký lưu hành'],
    })

    const root = w.get('[data-testid="dossier-card"]')
    expect(root.classes().join(' ')).toContain('red')
    expect(w.get('[data-testid="dossier-status"]').text()).toBe('Hết hiệu lực')

    // % THẬT + mẫu số minh bạch (KHÔNG còn "0% đầy đủ")
    const pct = w.get('[data-testid="dossier-pct"]').text()
    expect(pct).toContain('50%')
    expect(pct).toContain('2/4')
    // "0% đầy đủ" của hợp đồng stub cũ phải biến mất (regex biên: 50% KHÔNG tính)
    expect(/(^|\D)0%/.test(w.text()), 'không được còn "0%" stub').toBe(false)

    // Hai loại vi phạm — hai khối riêng, hai hành động khác nhau
    const expired = w.get('[data-testid="dossier-expired"]').text()
    expect(expired).toContain('Hết hạn')
    expect(expired).toContain('Chứng nhận đăng ký lưu hành')
    expect(w.get('[data-testid="dossier-missing"]').text()).toContain('Hợp đồng bảo trì')

    // KHÔNG rò enum tiếng Anh (LL-FE-53 / GATE-1)
    for (const en of EN_ENUMS) expect(w.text()).not.toContain(en)
  })

  // ── TC-FE-DOSSIER-02 ──────────────────────────────────────────────────────
  it('TC-FE-DOSSIER-02: is_compliant=1 + Expiring_Soon ⇒ thẻ vàng, KHÔNG chặn', () => {
    const w = mountCard({
      documentStatus: 'Expiring_Soon',
      isCompliant: true,
      completenessPct: 100,
      requiredTotal: 3,
      requiredSatisfied: 3,
      expiringRequired: ['Giấy phép nhập khẩu'],
    })

    const cls = w.get('[data-testid="dossier-card"]').classes().join(' ')
    expect(cls).toContain('amber')
    expect(cls).not.toContain('red')
    expect(w.get('[data-testid="dossier-status"]').text()).toBe('Sắp hết hạn')
    // Cảnh báo ≠ chặn: KHÔNG hiện câu "Cần bổ sung hồ sơ trước khi..."
    expect(w.find('[data-testid="dossier-block-warning"]').exists()).toBe(false)
    expect(w.get('[data-testid="dossier-expiring"]').text()).toContain('Giấy phép nhập khẩu')
  })

  it('TC-FE-DOSSIER-02b (dead-branch): document_status legacy "Complete" KHÔNG còn quyết định tông màu', () => {
    // BE cũ phát "Complete" — giá trị KHÔNG nằm trong enum SSoT. Component chỉ
    // được nghe `is_compliant`; nếu còn so chuỗi thì đây là ca vỡ.
    const ok = mountCard({ documentStatus: 'Complete', isCompliant: true, completenessPct: 100 })
    expect(ok.get('[data-testid="dossier-card"]').classes().join(' ')).toContain('emerald')

    const bad = mountCard({ documentStatus: 'Complete', isCompliant: false, completenessPct: 40, requiredSatisfied: 2, requiredTotal: 5 })
    expect(bad.get('[data-testid="dossier-card"]').classes().join(' ')).toContain('red')

    // Giá trị lạ ⇒ degrade an toàn, tuyệt đối KHÔNG in chuỗi lạ ra UI
    expect(ok.get('[data-testid="dossier-status"]').text()).toBe('Chưa có dữ liệu')
    expect(ok.text()).not.toContain('Complete')
  })

  it('is_compliant vắng mặt (BE chưa deploy CR-75) ⇒ trung tính: KHÔNG đỏ giả, cũng KHÔNG khoe xanh', () => {
    const w = mountCard({ isCompliant: null, documentStatus: null, completenessPct: 0, requiredTotal: null, requiredSatisfied: null })
    const cls = w.get('[data-testid="dossier-card"]').classes().join(' ')
    expect(cls).not.toContain('red')
    expect(cls).not.toContain('emerald')
    expect(cls).toContain('slate')
    expect(w.get('[data-testid="dossier-status"]').text()).toBe('Chưa có dữ liệu')
    // Không đáng tin ⇒ KHÔNG vẽ thanh "0% đầy đủ" (chính là lời nói dối CR-75 khử)
    expect(w.find('[role="progressbar"]').exists()).toBe(false)
    expect(w.get('[data-testid="dossier-unknown"]').text()).toContain('Chưa lấy được số liệu')
  })

  it('required_total = 0 ⇒ KHÔNG khoe "100% đầy đủ" mà giải thích mẫu số rỗng (BR-05-17)', () => {
    const w = mountCard({
      documentStatus: 'Compliant',
      isCompliant: true,
      completenessPct: 100,
      requiredTotal: 0,
      requiredSatisfied: 0,
    })
    expect(w.find('[data-testid="dossier-no-required"]').exists()).toBe(true)
    expect(w.get('[data-testid="dossier-no-required"]').text()).toContain('Không có loại hồ sơ bắt buộc')
    expect(w.find('[data-testid="dossier-pct"]').exists()).toBe(false)
  })

  it('5 giá trị enum SSoT đều có nhãn tiếng Việt riêng biệt (không trùng, không rỗng)', () => {
    const labels = ['Compliant', 'Compliant (Exempt)', 'Expiring_Soon', 'Non-Compliant', 'Incomplete'].map(
      (s) => mountCard({ documentStatus: s, isCompliant: s !== 'Non-Compliant' && s !== 'Incomplete' })
        .get('[data-testid="dossier-status"]').text(),
    )
    expect(new Set(labels).size).toBe(5)
    for (const l of labels) {
      expect(l.length).toBeGreaterThan(0)
      expect(l).not.toBe('Chưa có dữ liệu')
      expect(/[A-Za-z]{4,}/.test(l), `nhãn "${l}" còn chuỗi tiếng Anh`).toBe(false)
    }
  })

  it('hidden_count > 0 ⇒ chú thích minh bạch phân quyền (BR-05-20)', () => {
    const w = mountCard({ hiddenCount: 2 })
    expect(w.get('[data-testid="dossier-hidden"]').text()).toContain('2')
  })

  it('a11y: thanh tiến độ có role/aria-valuenow, nút làm mới có aria-label, trạng thái có nhãn chữ', () => {
    const w = mountCard({ completenessPct: 75, requiredSatisfied: 3, requiredTotal: 4 })
    const bar = w.get('[role="progressbar"]')
    expect(bar.attributes('aria-valuenow')).toBe('75')
    expect(bar.attributes('aria-valuemin')).toBe('0')
    expect(bar.attributes('aria-valuemax')).toBe('100')
    expect(bar.attributes('aria-label')).toBeTruthy()
    expect(w.get('[data-testid="dossier-refresh"]').attributes('aria-label')).toBeTruthy()
  })

  it('nút "Làm mới" phát emit refresh (control KHÔNG chết — GATE-6c)', async () => {
    const w = mountCard()
    await w.get('[data-testid="dossier-refresh"]').trigger('click')
    expect(w.emitted('refresh')).toHaveLength(1)
  })

  it('% ngoài biên bị kẹp về 0..100 (không vẽ thanh tràn)', () => {
    expect(mountCard({ completenessPct: 140 }).get('[role="progressbar"]').attributes('aria-valuenow')).toBe('100')
    expect(mountCard({ completenessPct: -5 }).get('[role="progressbar"]').attributes('aria-valuenow')).toBe('0')
  })
})
