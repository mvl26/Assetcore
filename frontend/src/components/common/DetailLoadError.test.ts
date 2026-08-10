// Copyright (c) 2026, AssetCore Team
// TDD — empty-state CHUNG cho màn chi tiết khi nạp bản ghi thất bại.
//
// SSoT copy VI + lối thoát cho mọi *DetailView (chống lặp markup & lệch chữ):
//   kind='notfound' → "Không tìm thấy <nhãn>: <mã>" + gợi ý kiểm tra mã, KHÔNG nút Thử lại
//                     (retry vô nghĩa với mã sai/đã xoá).
//   kind='unknown'  → message thật của server (fallback VI nếu rỗng) + nút Thử lại.
// Luôn có nút quay về danh sách ⇒ KHÔNG dead-end.
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DetailLoadError from './DetailLoadError.vue'

describe('DetailLoadError', () => {
  it("kind='notfound' → nêu nhãn + mã bản ghi, chỉ nút quay về danh sách", async () => {
    const wrapper = mount(DetailLoadError, {
      props: {
        kind: 'notfound' as const,
        entityLabel: 'phiếu hiệu chuẩn',
        recordId: 'CAL-2026-04591',
        backLabel: 'Về danh sách hiệu chuẩn',
      },
    })
    expect(wrapper.text()).toContain('Không tìm thấy phiếu hiệu chuẩn')
    expect(wrapper.text()).toContain('CAL-2026-04591')
    expect(wrapper.text()).not.toContain('Thử lại')

    const back = wrapper.findAll('button').find(b => b.text().includes('Về danh sách hiệu chuẩn'))!
    await back.trigger('click')
    expect(wrapper.emitted('back')).toHaveLength(1)
  })

  it("kind='unknown' → hiện message server + nút Thử lại phát sự kiện retry", async () => {
    const wrapper = mount(DetailLoadError, {
      props: {
        kind: 'unknown' as const,
        entityLabel: 'phiếu hiệu chuẩn',
        recordId: 'CAL-2026-04591',
        message: 'Mất kết nối tới máy chủ',
        backLabel: 'Về danh sách hiệu chuẩn',
      },
    })
    expect(wrapper.text()).toContain('Mất kết nối tới máy chủ')

    const retry = wrapper.findAll('button').find(b => b.text().includes('Thử lại'))!
    await retry.trigger('click')
    expect(wrapper.emitted('retry')).toHaveLength(1)
  })

  it("kind='unknown' KHÔNG có message → fallback VI theo nhãn (không để trống)", () => {
    const wrapper = mount(DetailLoadError, {
      props: {
        kind: 'unknown' as const,
        entityLabel: 'cuộc soát xét quản lý',
        backLabel: 'Về danh sách',
      },
    })
    expect(wrapper.text()).toContain('Không tải được cuộc soát xét quản lý')
  })
})
