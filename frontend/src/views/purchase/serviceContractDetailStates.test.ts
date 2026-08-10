// Copyright (c) 2026, AssetCore Team
// TC-UX4-48 (docs/ui-ux/03 §13.6) — ServiceContractDetailView áp khuôn `DetailPageShell` (lô 2, nhóm N3).
//
// RED trước fix: KHÔNG lối nạp lại nào — mất mạng / 403 in ra dòng «Không tìm thấy hợp đồng.» căn
// giữa (dán nhãn 404 cho MỌI lỗi, ngõ cụt); `error` dùng CHUNG với «Lưu»/«Xoá» nên một cú bấm hỏng
// cũng in banner đè lên hợp đồng đang xem (bẫy 13.9.7). Sau fix: 4 trạng thái loại trừ, kind THẬT.
import { vi } from 'vitest'
import { mount } from '@vue/test-utils'
import type { ServiceContract } from '@/types/imm00'
import { describeDetailStates } from '@/test/detailStatesHarness'

const pushSpy = vi.fn()
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: 'SC-2026-0009' } }),
  useRouter: () => ({ push: pushSpy, back: vi.fn() }),
}))

const frappeGetSpy = vi.fn()
vi.mock('@/api/helpers', () => ({
  frappeGet: (...a: unknown[]) => frappeGetSpy(...(a as [])),
  frappePost: vi.fn(),
}))

import ServiceContractDetailView from './ServiceContractDetailView.vue'

const stubs = { SmartSelect: true, CurrencyInput: true, DateInput: true, RouterLink: true }

function contractFixture(): ServiceContract {
  return {
    name: 'SC-2026-0009',
    contract_title: 'Hợp đồng bảo trì định kỳ máy thở 2026',
    contract_type: 'Preventive Maintenance',
    contract_start: '2026-01-01',
    contract_end: '2026-12-31',
    supplier: 'SUP-2026-00012',
  } as unknown as ServiceContract
}

describeDetailStates({
  view: 'ServiceContractDetailView',
  tc: 'TC-UX4-48',
  mount: () => mount(ServiceContractDetailView, { global: { stubs } }) as never,
  pending: () => frappeGetSpy.mockReturnValue(new Promise(() => {})),
  fail: (e) => frappeGetSpy.mockRejectedValue(e),
  empty: () => frappeGetSpy.mockResolvedValue(null),
  ok: () => frappeGetSpy.mockResolvedValue(contractFixture()),
  loadCalls: () => frappeGetSpy.mock.calls.length,
  reset: () => {
    frappeGetSpy.mockReset()
    pushSpy.mockClear()
  },
  recordId: 'SC-2026-0009',
  ctaTestIds: ['cta-edit', 'cta-delete'],
  routerPush: pushSpy,
})
