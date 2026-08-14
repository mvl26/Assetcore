// Copyright (c) 2026, AssetCore Team — AC-CR-80 §FE-1: picker nói ĐÚNG SỰ THẬT.
//
// Bug lớp "cắt IM LẶNG": BE trả tối đa `limit` người, picker hiện 20 dòng và im
// — người dùng tin rằng "chỉ có 20 người đủ năng lực" rồi chọn nhầm / bỏ cuộc.
// AC-CR-80 bắt BE công bố `total`/`truncated`; nếu FE KHÔNG render thì state
// truncation là STATE CHẾT (cùng bẫy CR-69).
//
// Test RENDER trên DOM (LL-FE-46: vitest xanh ở tầng api-client KHÔNG chứng minh
// UI hiện chữ). Chuỗi CHỐT theo `docs/imm-00/06_Frontend_Design.md §VIII.3.2`:
//     "Đang hiển thị {N}/{M} người — gõ tên để tìm thêm"
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const listAssignableUsersMock = vi.fn()
const getUsersByRoleMock = vi.fn()

vi.mock('@/api/user', async () => {
  const actual = await vi.importActual<typeof import('@/api/user')>('@/api/user')
  return {
    ...actual,
    listAssignableUsers: (context: string, search?: string, limit?: number) =>
      listAssignableUsersMock(context, search, limit),
  }
})
vi.mock('@/api/imm04', () => ({
  getUsersByRole: (role: string, search?: string, limit?: number) =>
    getUsersByRoleMock(role, search, limit),
}))

import ApproverSelect from '@/components/commissioning/ApproverSelect.vue'

const BANNER = 'Đang hiển thị'

function makeUsers(n: number, from = 0) {
  return Array.from({ length: n }, (_, i) => ({
    name: `u${from + i}@benhvien.vn`,
    full_name: `Nguyễn Văn ${from + i}`,
    email: `u${from + i}@benhvien.vn`,
    user_image: null,
  }))
}

/** Mount + mở dropdown (focus ô tìm kiếm) rồi đợi fetch xong. */
async function openPicker(props: Record<string, unknown> = {}) {
  const wrapper = mount(ApproverSelect, {
    props: { modelValue: undefined, context: 'repair', label: 'Kỹ thuật viên', ...props },
  })
  await wrapper.find('input').trigger('focus')
  await flushPromises()
  await wrapper.vm.$nextTick()
  return wrapper
}

describe('ApproverSelect — dải "đang xem N/M" khi danh sách bị cắt (AC-CR-80)', () => {
  beforeEach(() => {
    listAssignableUsersMock.mockReset()
    getUsersByRoleMock.mockReset()
  })

  it('truncated=1 ⇒ DOM CHỨA "Đang hiển thị 20/47 người — gõ tên để tìm thêm"', async () => {
    listAssignableUsersMock.mockResolvedValue({
      items: makeUsers(20), total: 47, truncated: 1, limit: 20,
    })
    const wrapper = await openPicker()

    expect(wrapper.text()).toContain('Đang hiển thị 20/47 người — gõ tên để tìm thêm')
    // Dải phải là vùng thông báo (trình đọc màn hình) — WCAG 2.1 AA.
    const banner = wrapper.find('[role="status"]')
    expect(banner.exists()).toBe(true)
    expect(banner.text()).toContain('Đang hiển thị 20/47 người')
  })

  it('dải nằm NGOÀI vùng cuộn ⇒ thấy ngay, không phải cuộn hết 20 dòng', async () => {
    // Bằng chứng render 2026-07-27: để dải BÊN TRONG `.overflow-y-auto` thì DOM
    // có chữ (test xanh) nhưng màn hình KHÔNG hiện — vẫn là cắt im lặng bằng mắt
    // (lớp lỗi LL-FE-48). Ghim cấu trúc để lần sửa sau không lồng lại.
    listAssignableUsersMock.mockResolvedValue({
      items: makeUsers(20), total: 47, truncated: 1, limit: 20,
    })
    const wrapper = await openPicker()
    const banner = wrapper.find('[role="status"]').element
    expect(banner.closest('.overflow-y-auto')).toBeNull()
    // Đối chứng (chống assert rỗng): dòng kết quả THÌ nằm trong vùng cuộn.
    const row = wrapper.findAll('button').find(b => b.text().includes('Nguyễn Văn 0'))!.element
    expect(row.closest('.overflow-y-auto')).not.toBeNull()
  })

  it('truncated=0 ⇒ KHÔNG render dải nào (không để dải rỗng chiếm chỗ)', async () => {
    listAssignableUsersMock.mockResolvedValue({
      items: makeUsers(3), total: 3, truncated: 0, limit: 20,
    })
    const wrapper = await openPicker()

    expect(wrapper.text()).not.toContain(BANNER)
    expect(wrapper.find('[role="status"]').exists()).toBe(false)
    // Danh sách vẫn render bình thường.
    expect(wrapper.text()).toContain('Nguyễn Văn 0')
  })

  it('N/M lấy từ dữ liệu THẬT (10/113), không hardcode', async () => {
    listAssignableUsersMock.mockResolvedValue({
      items: makeUsers(10), total: 113, truncated: 1, limit: 10,
    })
    const wrapper = await openPicker()
    expect(wrapper.text()).toContain('Đang hiển thị 10/113 người')
  })

  it('lỗi tải ⇒ KHÔNG hiện dải (không khẳng định số liệu khi không có dữ liệu)', async () => {
    listAssignableUsersMock.mockRejectedValue(new Error('403'))
    const wrapper = await openPicker()
    expect(wrapper.text()).not.toContain(BANNER)
    expect(wrapper.text()).toContain('Không tìm thấy người dùng nào')
  })

  it('shape CŨ (mảng trần, BE chưa reload) ⇒ vẫn render danh sách, KHÔNG dải, KHÔNG trắng', async () => {
    listAssignableUsersMock.mockResolvedValue(makeUsers(2))
    const wrapper = await openPicker()
    expect(wrapper.text()).toContain('Nguyễn Văn 0')
    expect(wrapper.text()).toContain('Nguyễn Văn 1')
    expect(wrapper.text()).not.toContain(BANNER)
  })

  it('nhánh role= (getUsersByRole) vẫn chạy, không dải (nguồn chưa có meta cắt)', async () => {
    getUsersByRoleMock.mockResolvedValue(makeUsers(2))
    const wrapper = await openPicker({ context: '', role: 'AssetCore Board Approver' })
    expect(getUsersByRoleMock).toHaveBeenCalled()
    expect(listAssignableUsersMock).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Nguyễn Văn 0')
    expect(wrapper.text()).not.toContain(BANNER)
  })

  it('full_name null (tài khoản cũ) ⇒ fallback tên đăng nhập, KHÔNG crash', async () => {
    listAssignableUsersMock.mockResolvedValue({
      items: [{ name: 'cu@benhvien.vn', full_name: null, email: null, user_image: null }],
      total: 1, truncated: 0, limit: 20,
    })
    const wrapper = await openPicker()
    expect(wrapper.text()).toContain('cu@benhvien.vn')
  })

  it('chọn người ⇒ emit đúng `update:modelValue` (0 hồi quy hợp đồng v-model)', async () => {
    listAssignableUsersMock.mockResolvedValue({
      items: makeUsers(2), total: 2, truncated: 0, limit: 20,
    })
    const wrapper = await openPicker()
    const rows = wrapper.findAll('button').filter(b => b.text().includes('Nguyễn Văn 1'))
    expect(rows.length).toBe(1)
    await rows[0].trigger('mousedown')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['u1@benhvien.vn'])
  })
})
