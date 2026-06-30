// Composable cho CurrencyInput — quản lý text hiển thị (nhóm hàng nghìn kiểu
// Việt Nam) + sync với modelValue number. Mirror cấu trúc useMaskedDateInput:
// trả `text` ref + `onInput`/`onBlur`; v-model emit number SẠCH (KHÔNG chuỗi).
import { ref, watch, type Ref } from 'vue'
import { formatThousands, parseThousands } from '@/utils/formatters'

export interface ThousandsInputApi {
  text: Ref<string>
  onInput: (e: Event) => void
  onBlur: () => void
}

type EmitFn = {
  (event: 'update:modelValue', v: number | null): void
  (event: 'change', v: number | null): void
}

export function useThousandsInput(
  modelValue: () => number | null | undefined,
  emit: EmitFn,
): ThousandsInputApi {
  const text = ref('')

  // modelValue đổi từ ngoài (reset form / load draft) → đồng bộ text. Guard
  // `!==` để KHÔNG tự ghi đè khi chính onInput vừa emit (parent set lại cùng số).
  watch(modelValue, (v) => {
    const next = formatThousands(v ?? null)
    if (next !== text.value) text.value = next
  }, { immediate: true })

  function onInput(e: Event) {
    const n = parseThousands((e.target as HTMLInputElement).value)
    text.value = formatThousands(n)   // reflow nhóm ngay khi gõ
    emit('update:modelValue', n)
    emit('change', n)
  }

  function onBlur() {
    // chuẩn hoá hiển thị về dạng nhóm canonical theo modelValue hiện tại.
    text.value = formatThousands(modelValue() ?? null)
  }

  return { text, onInput, onBlur }
}
