// Copyright (c) 2026, AssetCore Team
// AC-CR-81 — mỗi dòng hồ sơ phải phơi TỆP THẬT.
//
// RED trước fix (2026-07-27): `DocumentDossierCard.vue` chỉ vẽ phần TỔNG HỢP
// (%, thiếu/hết hạn) — người dùng thấy "đủ hồ sơ" nhưng KHÔNG có đường nào mở
// tệp, và cũng không biết dòng nào chưa đính kèm ⇒ state chết y hệt bẫy CR-69.
//
// Hợp đồng BE (`services/imm05.py::get_asset_documents`): mỗi dòng LUÔN có đủ 5
// khoá `file_url`/`file_name`/`file_size`/`is_private`/`has_file`; link mồ côi ⇒
// `has_file=0` ∧ `file_url=''` (BE KHÔNG phát link chết).
//
// Hợp đồng FE ở đây:
//  - `has_file === 1`  ⇒ link «Mở tệp» (`href` = `file_url`, `_blank`+`noopener`)
//                        + tên tệp + kích thước đọc-được (KHÔNG in URL thô);
//  - `has_file === 0`  ⇒ nút DISABLED + nhãn «Chưa đính kèm tệp» (có tooltip);
//  - `has_file` VẮNG   ⇒ "Chưa có thông tin tệp" (BE chưa deploy) — KHÔNG được
//                        vu cho hồ sơ là "chưa đính kèm" (LL-FE-42: không im lặng,
//                        cũng không kết luận sai).
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import DocumentDossierCard from '@/components/commissioning/DocumentDossierCard.vue'
import type { AssetDossierDocItem } from '@/api/imm05'

type Props = InstanceType<typeof DocumentDossierCard>['$props']

function row(over: Partial<AssetDossierDocItem> = {}): AssetDossierDocItem {
  return {
    name: 'DOC-2026-0001',
    doc_category: 'Legal',
    doc_type_detail: 'Giấy phép nhập khẩu',
    doc_number: 'GPNK-123',
    workflow_state: 'Active',
    expiry_date: '2027-01-01',
    days_until_expiry: 180,
    is_expired: 0,
    ...over,
  }
}

function mountCard(documents: Record<string, AssetDossierDocItem[]>, props: Partial<Props> = {}) {
  return mount(DocumentDossierCard, {
    props: {
      documentStatus: 'Compliant',
      isCompliant: true,
      completenessPct: 100,
      requiredTotal: 2,
      requiredSatisfied: 2,
      documents,
      ...props,
    } as Props,
  })
}

/** Chuỗi tiếng Anh tuyệt đối KHÔNG được xuất hiện trong khối tệp (LL-FE-53). */
const EN_LEAKS = ['Open file', 'No attachment', 'bytes', 'Download', 'Private', 'File not found']

describe('DocumentDossierCard — AC-CR-81 dòng hồ sơ phơi tệp thật', () => {
  // ── TC-FE-DOSSIER-01 ──────────────────────────────────────────────────────
  it('TC-FE-DOSSIER-01: has_file=1 ⇒ link «Mở tệp» href == file_url + hiện tên tệp', () => {
    const w = mountCard({
      Legal: [
        row({
          file_url: '/private/files/gpnk-123.pdf',
          file_name: 'gpnk-123.pdf',
          file_size: 1_258_291,
          is_private: 1,
          has_file: 1,
        }),
      ],
    })

    const link = w.get('[data-testid="dossier-file-open"]')
    expect(link.element.tagName).toBe('A')
    expect(link.attributes('href')).toBe('/private/files/gpnk-123.pdf')
    expect(link.text()).toContain('Mở tệp')
    // Mở tab mới an toàn (chống tabnabbing)
    expect(link.attributes('target')).toBe('_blank')
    expect(link.attributes('rel')).toContain('noopener')
    // a11y: link phải tự mô tả được khi đọc rời ngữ cảnh
    expect(link.attributes('aria-label')).toContain('Giấy phép nhập khẩu')

    // Tên tệp hiện ra; URL thô thì KHÔNG (đường dẫn nội bộ không phải nội dung UI)
    expect(w.get('[data-testid="dossier-file-name"]').text()).toContain('gpnk-123.pdf')
    expect(w.text()).not.toContain('/private/files/')

    // Không có nhánh "chưa đính kèm" ở dòng đã có tệp
    expect(w.find('[data-testid="dossier-file-none"]').exists()).toBe(false)
  })

  // ── TC-FE-DOSSIER-02 ──────────────────────────────────────────────────────
  it('TC-FE-DOSSIER-02: has_file=0 ⇒ KHÔNG có link, có nhãn «Chưa đính kèm tệp» + nút disabled', () => {
    const w = mountCard({
      Legal: [row({ file_url: '', file_name: '', file_size: 0, is_private: 0, has_file: 0 })],
    })

    expect(w.find('[data-testid="dossier-file-open"]').exists()).toBe(false)
    expect(w.findAll('a[href]')).toHaveLength(0)

    const none = w.get('[data-testid="dossier-file-none"]')
    expect(none.text()).toContain('Chưa đính kèm tệp')
    expect(none.attributes('disabled')).toBeDefined()
    expect(none.attributes('aria-disabled')).toBe('true')
    // Tooltip giải thích vì sao nút không bấm được
    expect(none.attributes('title')).toBeTruthy()
  })

  it('TC-FE-DOSSIER-02b (link mồ côi — phòng thủ 2 lớp): has_file=0 mà file_url còn sót ⇒ VẪN không phát link', () => {
    // BE đã hứa `has_file=0 ⇒ file_url=''`; FE không được phụ thuộc lời hứa đó —
    // `has_file` là khoá quyết định DUY NHẤT.
    const w = mountCard({
      Legal: [row({ file_url: '/files/da-xoa.pdf', file_name: 'da-xoa.pdf', file_size: 999, has_file: 0 })],
    })
    expect(w.find('[data-testid="dossier-file-open"]').exists()).toBe(false)
    expect(w.findAll('a[href]')).toHaveLength(0)
    expect(w.text()).not.toContain('da-xoa.pdf')
    expect(w.get('[data-testid="dossier-file-none"]').text()).toContain('Chưa đính kèm tệp')
  })

  // ── TC-FE-DOSSIER-03 ──────────────────────────────────────────────────────
  it('TC-FE-DOSSIER-03: kích thước tệp format VI ("1,2 MB") và không rò chuỗi tiếng Anh', () => {
    const w = mountCard({
      Legal: [
        row({ name: 'D1', file_url: '/files/a.pdf', file_name: 'a.pdf', file_size: 1_258_291, has_file: 1 }),
        row({ name: 'D2', doc_type_detail: 'Hợp đồng bảo trì', file_url: '', file_name: '', file_size: 0, has_file: 0 }),
      ],
    })

    expect(w.get('[data-testid="dossier-file-name"]').text()).toContain('1,2 MB')
    expect(w.text()).not.toContain('1.2 MB')
    for (const en of EN_LEAKS) expect(w.text()).not.toContain(en)
    // GATE-1: workflow_state phải qua bảng nhãn VI, không rò 'Active'
    expect(w.text()).not.toContain('Active')
    expect(w.text()).toContain('Hiệu lực')
  })

  it('has_file VẮNG (BE chưa deploy AC-CR-81) ⇒ nói "chưa có thông tin", KHÔNG vu "chưa đính kèm"', () => {
    const w = mountCard({ Legal: [row()] })
    expect(w.find('[data-testid="dossier-file-open"]').exists()).toBe(false)
    expect(w.find('[data-testid="dossier-file-none"]').exists()).toBe(false)
    const unk = w.get('[data-testid="dossier-file-unknown"]')
    expect(unk.text()).toContain('Chưa có thông tin tệp')
  })

  it('nhóm hồ sơ hiển thị nhãn tiếng Việt, mỗi dòng có tên loại + số hiệu', () => {
    const w = mountCard({
      Legal: [row({ file_url: '/files/a.pdf', file_name: 'a.pdf', file_size: 2048, has_file: 1 })],
      Certification: [
        row({ name: 'D9', doc_category: 'Certification', doc_type_detail: 'Phiếu kiểm định', doc_number: 'KD-9', has_file: 0 }),
      ],
    })
    const text = w.text()
    expect(text).toContain('Pháp lý')
    expect(text).toContain('Kiểm định')
    expect(text).not.toContain('Legal')
    expect(text).not.toContain('Certification')
    expect(text).toContain('GPNK-123')
    expect(w.findAll('[data-testid="dossier-doc-row"]')).toHaveLength(2)
  })

  it('không có dòng nào (rỗng/ẩn hết) ⇒ KHÔNG vẽ danh sách rỗng vô nghĩa', () => {
    const w = mountCard({})
    expect(w.find('[data-testid="dossier-doc-list"]').exists()).toBe(false)
    // phần tổng hợp cũ vẫn nguyên (0 regress)
    expect(w.get('[data-testid="dossier-status"]').text()).toBe('Đầy đủ')
  })

  it('0 REGRESS: thẻ vẫn chạy khi KHÔNG truyền prop documents (consumer cũ)', () => {
    const w = mount(DocumentDossierCard, {
      props: { documentStatus: 'Compliant', isCompliant: true, completenessPct: 100 } as Props,
    })
    expect(w.get('[data-testid="dossier-card"]').exists()).toBe(true)
    expect(w.find('[data-testid="dossier-doc-list"]').exists()).toBe(false)
  })
})
