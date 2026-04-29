// Composable dùng chung cho DateInput / DateTimeInput.
// Quản lý text mask + sync với modelValue + mở native picker.
import { ref, watch, type Ref } from 'vue'

export interface DateMaskConfig {
  isoToDisplay: (iso: string | number | null | undefined) => string
  displayToIso: (s: string) => string
  /** Nhận chuỗi digits đã lọc (đã slice maxDigits) → trả ra text đã chèn separator. */
  formatMask: (digits: string) => string
  maxDigits: number
}

export interface MaskedDateInputApi {
  text: Ref<string>
  nativeRef: Ref<HTMLInputElement | null>
  onInput: (e: Event) => void
  onBlur: () => void
  onNativeChange: (e: Event) => void
  openPicker: (disabled: boolean) => void
}

type EmitFn = {
  (event: 'update:modelValue', v: string): void
  (event: 'change', v: string): void
}

export function useMaskedDateInput(
  modelValue: () => string | number | null | undefined,
  emit: EmitFn,
  config: DateMaskConfig,
): MaskedDateInputApi {
  const text = ref('')
  const nativeRef = ref<HTMLInputElement | null>(null)

  watch(modelValue, (v) => {
    const next = config.isoToDisplay(v)
    if (next !== text.value) text.value = next
  }, { immediate: true })

  function onInput(e: Event) {
    const raw = (e.target as HTMLInputElement).value
    const digits = raw.replace(NON_DIGIT_RE, '').slice(0, config.maxDigits)
    const out = config.formatMask(digits)
    text.value = out

    const iso = config.displayToIso(out)
    if (iso) {
      emit('update:modelValue', iso)
      emit('change', iso)
    } else if (out === '') {
      emit('update:modelValue', '')
      emit('change', '')
    }
  }

  function onBlur() {
    const iso = config.displayToIso(text.value)
    if (!iso && text.value !== '') {
      text.value = config.isoToDisplay(modelValue())
      if (!text.value) {
        emit('update:modelValue', '')
        emit('change', '')
      }
    }
  }

  function onNativeChange(e: Event) {
    const v = (e.target as HTMLInputElement).value
    text.value = config.isoToDisplay(v)
    emit('update:modelValue', v)
    emit('change', v)
  }

  function openPicker(disabled: boolean) {
    const el = nativeRef.value
    if (!el || disabled) return
    const withPicker = el as HTMLInputElement & { showPicker?: () => void }
    if (typeof withPicker.showPicker === 'function') {
      try { withPicker.showPicker(); return } catch { /* fallthrough */ }
    }
    el.focus()
    el.click()
  }

  return { text, nativeRef, onInput, onBlur, onNativeChange, openPicker }
}

const NON_DIGIT_RE = /\D/g

const ISO_DATE_RE = /^(\d{4})-(\d{2})-(\d{2})/
const DISPLAY_DATE_RE = /^(\d{2})\/(\d{2})\/(\d{4})$/

const ISO_DATETIME_RE = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/
const DISPLAY_DATETIME_RE = /^(\d{2})\/(\d{2})\/(\d{4})\s+(\d{2}):(\d{2})$/

const pad2 = (n: number): string => String(n).padStart(2, '0')

function isValidDate(yyyy: number, mm: number, dd: number): boolean {
  if (mm < 1 || mm > 12 || dd < 1 || dd > 31 || yyyy < 1900) return false
  const dt = new Date(yyyy, mm - 1, dd)
  return dt.getFullYear() === yyyy && dt.getMonth() === mm - 1 && dt.getDate() === dd
}

// ─── Date (yyyy-mm-dd) ────────────────────────────────────────────────────────

export const dateMaskConfig: DateMaskConfig = {
  isoToDisplay(iso) {
    if (!iso) return ''
    const m = ISO_DATE_RE.exec(String(iso))
    return m ? `${m[3]}/${m[2]}/${m[1]}` : ''
  },
  displayToIso(s) {
    const m = DISPLAY_DATE_RE.exec(s.trim())
    if (!m) return ''
    const dd = +m[1], mm = +m[2], yyyy = +m[3]
    if (!isValidDate(yyyy, mm, dd)) return ''
    return `${yyyy}-${pad2(mm)}-${pad2(dd)}`
  },
  formatMask(digits) {
    if (digits.length > 4) return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`
    if (digits.length > 2) return `${digits.slice(0, 2)}/${digits.slice(2)}`
    return digits
  },
  maxDigits: 8,
}

// ─── Datetime (yyyy-mm-ddTHH:mm) ──────────────────────────────────────────────

export const dateTimeMaskConfig: DateMaskConfig = {
  isoToDisplay(iso) {
    if (!iso) return ''
    const m = ISO_DATETIME_RE.exec(String(iso))
    return m ? `${m[3]}/${m[2]}/${m[1]} ${m[4]}:${m[5]}` : ''
  },
  displayToIso(s) {
    const m = DISPLAY_DATETIME_RE.exec(s.trim())
    if (!m) return ''
    const dd = +m[1], mm = +m[2], yyyy = +m[3], hh = +m[4], mi = +m[5]
    if (!isValidDate(yyyy, mm, dd) || hh > 23 || mi > 59) return ''
    return `${yyyy}-${pad2(mm)}-${pad2(dd)}T${pad2(hh)}:${pad2(mi)}`
  },
  formatMask(digits) {
    if (digits.length > 8) {
      const tail = digits.length > 10 ? ':' + digits.slice(10, 12) : ''
      return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4, 8)} ${digits.slice(8, 10)}${tail}`
    }
    if (digits.length > 4) return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`
    if (digits.length > 2) return `${digits.slice(0, 2)}/${digits.slice(2)}`
    return digits
  },
  maxDigits: 12,
}
