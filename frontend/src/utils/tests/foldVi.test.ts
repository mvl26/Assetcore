// TDD — diacritic-fold VI (ADR-IMM00-CMDK D3). TC-CMDK-05.
import { describe, it, expect } from 'vitest'
import { foldVi } from '@/utils/foldVi'

describe('foldVi — diacritic-fold tiếng Việt', () => {
  it('TC-CMDK-05: foldVi("Bảo trì") === "bao tri"', () => {
    expect(foldVi('Bảo trì')).toBe('bao tri')
  })
  it('TC-CMDK-05: foldVi("Thiết bị") === "thiet bi"', () => {
    expect(foldVi('Thiết bị')).toBe('thiet bi')
  })
  it('TC-CMDK-05: foldVi("Đo") === "do" (đ/Đ → d)', () => {
    expect(foldVi('Đo')).toBe('do')
  })
  it('mọi dấu thanh + ký tự đặc biệt VI fold đúng', () => {
    expect(foldVi('Hiệu chuẩn')).toBe('hieu chuan')
    expect(foldVi('Sửa chữa')).toBe('sua chua')
    expect(foldVi('Đề xuất nhu cầu')).toBe('de xuat nhu cau')
    expect(foldVi('Tồn kho phụ tùng')).toBe('ton kho phu tung')
    expect(foldVi('Người dùng')).toBe('nguoi dung')
  })
  it('idempotent + lowercase + trim', () => {
    expect(foldVi('  ASSETCORE  ')).toBe('assetcore')
    expect(foldVi(foldVi('Bảo trì'))).toBe('bao tri')
  })
})
