// Copyright (c) 2026, AssetCore Team
// vue-i18n setup — bootstrap với hai locale vi/en, mặc định vi.
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
