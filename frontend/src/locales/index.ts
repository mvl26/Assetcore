// Copyright (c) 2026, AssetCore Team
// vue-i18n setup — bootstrap với hai locale vi/en, mặc định vi.
//
// ─── `src/locales/` là NHÀ CHUỖI DUY NHẤT của FE (SSoT, chốt 2026-08-13) ──────
// Thư mục `src/i18n/` cũ đã bị gộp vào đây. Hai loại dữ liệu khác nhau sống cạnh
// nhau, KHÔNG trộn — đừng nhồi loại này vào loại kia:
//
//   1. `vi.json` / `en.json` + file này — chuỗi UI phẳng cho vue-i18n (`$t('common.save')`).
//      Viết tay. Hiện chưa có component nào tiêu thụ (giàn giáo đa ngôn ngữ).
//   2. `messages.ts` + `messageTypes.ts` — registry MÃ thông báo nghiệp vụ
//      (title + template + action_hint + severity + http_status), tiêu thụ qua
//      `useNotify`/`MSG.*`. **AUTO-GENERATED** từ BE `assetcore/utils/messages.py`
//      bằng `python scripts/gen_fe_messages.py` — KHÔNG sửa tay, guard parity
//      `messageParity.test.ts` sẽ đỏ nếu lệch.
//
// Sử dụng:
//   import { useI18n } from 'vue-i18n'
//   const { t } = useI18n()
//   t('common.save') → 'Lưu'
//
// Hoặc trong template: {{ $t('imm12.title') }}
//
// Đổi ngôn ngữ: import { setLocale } from '@/locales'; setLocale('en')
// Persist qua localStorage key 'assetcore.locale'.

import { createI18n } from 'vue-i18n'
import vi from './vi.json'
import en from './en.json'

const STORAGE_KEY = 'assetcore.locale'

export type SupportedLocale = 'vi' | 'en'

const stored = (typeof localStorage !== 'undefined'
  ? localStorage.getItem(STORAGE_KEY)
  : null) as SupportedLocale | null

const defaultLocale: SupportedLocale = stored === 'en' ? 'en' : 'vi'

export const i18n = createI18n({
  legacy: false,
  locale: defaultLocale,
  fallbackLocale: 'vi',
  messages: { vi, en },
  missingWarn: false,
  fallbackWarn: false,
})

export function setLocale(loc: SupportedLocale): void {
  i18n.global.locale.value = loc
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, loc)
  }
}

export function getLocale(): SupportedLocale {
  return i18n.global.locale.value as SupportedLocale
}
