// Copyright (c) 2026, AssetCore Team
// TC-UX4-46 (docs/ui-ux/03 §13.6) — VendorProfileDetailView áp khuôn `DetailPageShell` (lô 2, nhóm N3).
//
// RED trước fix: KHÔNG có lối nạp lại nào — lỗi nạp in ra `.alert-error` rồi hết, không nút «Thử
// lại», không lối về danh sách (ngõ cụt); `error` lại dùng CHUNG với lỗi lưu chứng chỉ nên một cú
// lưu hỏng cũng xoá trắng cả hồ sơ đang xem (bẫy 13.9.7). Kèm **2** lần `page-container` (view +
// `<style scoped>`) chồng lên lớp bao của shell ⇒ padding nhân đôi (bẫy 13.9.5).
//
// Đây là màn DUY NHẤT của lô 2 không có test cũ nào (§13.9.9) ⇒ file này là lưới an toàn đầu tiên.
import { vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { describeDetailStates } from '@/test/detailStatesHarness'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'SUP-2026-00012' } }),
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
}))

const getVendorProfileSpy = vi.fn()
vi.mock('@/api/imm03', () => ({
  getVendorProfile: (...a: unknown[]) => getVendorProfileSpy(...(a as [])),
  addVendorCert: vi.fn(),
}))

import VendorProfileDetailView from '@/views/procurement/VendorProfileDetailView.vue'

const stubs = { DateInput: true, FileUploadField: true, RouterLink: true }

function profileFixture() {
  return {
    name: 'SUP-2026-00012',
    supplier_name: 'Công ty TNHH Thiết bị Y tế Minh Anh',
    legal_name: 'Công ty TNHH Thiết bị Y tế Minh Anh',
    imm_avl_status: 'Approved',
    imm_overall_score: 4.2,
    imm_certifications: [],
    avl_entries: [],
    scorecard_history: [],
  }
}

describeDetailStates({
  view: 'VendorProfileDetailView',
  tc: 'TC-UX4-46',
  mount: () => mount(VendorProfileDetailView, { props: { id: 'SUP-2026-00012' }, global: { stubs } }) as never,
  pending: () => getVendorProfileSpy.mockReturnValue(new Promise(() => {})),
  fail: (e) => getVendorProfileSpy.mockRejectedValue(e),
  empty: () => getVendorProfileSpy.mockResolvedValue(null),
  ok: () => getVendorProfileSpy.mockResolvedValue(profileFixture()),
  loadCalls: () => getVendorProfileSpy.mock.calls.length,
  reset: () => {
    getVendorProfileSpy.mockReset()
    pushSpy.mockClear()
  },
  recordId: 'SUP-2026-00012',
  ctaTestIds: ['cta-add-cert', 'cta-back'],
  routerPush: pushSpy,
})
