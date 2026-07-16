// CR-RBAC-PARITY (2026-07-15) — Guard: DeviceModelFormView phải render READ-ONLY
// khi user thiếu data.write (route /device-models/:id đã hạ xuống data.read để user
// chỉ-đọc XEM được chi tiết model — chống dead-gate click-toàn-hàng). Read-only =
// (a) computed `readonly` neo vào can('data.write'), (b) fieldset khoá input theo
// :disabled="readonly", (c) nút Lưu ẩn khi readonly. Ghi thật vẫn cần data.write ở BE.
// Test source-level (không mount 490-dòng form) — cùng phong cách createButtonAffordance.
import { readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, it, expect } from 'vitest'

const SRC = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), 'DeviceModelFormView.vue'),
  'utf8',
)

describe('CR-RBAC-PARITY — DeviceModelFormView read-only khi thiếu data.write', () => {
  it('readonly computed neo vào can(data.write) và chỉ áp trong edit mode', () => {
    expect(SRC).toContain("const readonly = computed(() => isEdit.value && !can('data.write'))")
  })
  it('fieldset khoá toàn bộ input theo :disabled="readonly"', () => {
    expect(SRC).toMatch(/<fieldset[^>]*:disabled="readonly"/)
  })
  it('nút Lưu/Cập nhật ẩn khi readonly (v-if="!readonly")', () => {
    // Nút submit gate v-if="!readonly" → user chỉ-đọc không thấy nút ghi.
    expect(SRC).toMatch(/v-if="!readonly"[^>]*@click="save"|@click="save"[^>]*v-if="!readonly"/)
  })
  it('nút Xóa ẩn khi readonly', () => {
    expect(SRC).toMatch(/v-if="isEdit && !readonly"[^>]*@click="remove"/)
  })
})
