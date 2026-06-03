<!-- Copyright (c) 2026, AssetCore Team -->
<script setup lang="ts">
import type { ImportWizardCtx } from '@/composables/useImportWizard'

defineProps<{
  /** Composable instance from useImportWizard(doctype, onSuccess). */
  ctx: ImportWizardCtx
  /** Modal header title — e.g. "Import Thiết bị". */
  title: string
  /** Domain noun for the result line (X / Y <unit> import thành công). */
  unit?: string
  /** Optional bullet-list shown on the upload step under "Lưu ý trước khi import". */
  notice?: string[]
  /** How many fieldname columns to preview (default 6). */
  previewColumns?: number
}>()
</script>

<template>
  <div
    v-if="ctx.showImport.value"
    class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
    @click.self="ctx.close"
  >
    <div class="bg-white rounded-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
        <div>
          <h2 class="text-base font-semibold text-gray-800">{{ title }}</h2>
          <p class="text-xs text-gray-500 mt-0.5">
            {{
              ctx.importStep.value === 'upload'
                ? 'Tải file Excel / CSV lên'
                : ctx.importStep.value === 'preview'
                  ? 'Kiểm tra dữ liệu trước khi import'
                  : 'Kết quả import'
            }}
          </p>
        </div>
        <button class="text-gray-400 hover:text-gray-600 p-1" @click="ctx.close">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Step indicator -->
      <div class="flex gap-0 border-b border-gray-100">
        <div v-for="(label, idx) in ['1. Upload', '2. Kiểm tra', '3. Kết quả']" :key="idx"
          :class="['flex-1 text-center py-2 text-xs font-medium',
            (ctx.importStep.value === 'upload' && idx === 0)
              || (ctx.importStep.value === 'preview' && idx === 1)
              || (ctx.importStep.value === 'result' && idx === 2)
              ? 'text-blue-600 border-b-2 border-blue-600 -mb-px'
              : 'text-gray-400']">
          {{ label }}
        </div>
      </div>

      <div class="p-6 space-y-4">
        <div v-if="ctx.importErr.value"
          class="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
          {{ ctx.importErr.value }}
        </div>

        <!-- STEP 1: UPLOAD -->
        <template v-if="ctx.importStep.value === 'upload'">
          <div class="flex items-center justify-between">
            <p class="text-sm text-gray-600">Tải template, điền dữ liệu rồi upload lại:</p>
            <button class="text-xs text-blue-600 hover:underline flex items-center gap-1"
              @click="ctx.doDownloadTemplate">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Tải template Excel
            </button>
          </div>

          <div v-if="notice && notice.length"
            class="text-xs text-gray-500 bg-blue-50 border border-blue-100 rounded-lg px-3 py-2">
            <p class="font-medium text-blue-700 mb-1">Lưu ý trước khi import:</p>
            <ul class="list-disc pl-4 space-y-0.5">
              <li v-for="(n, i) in notice" :key="i" v-html="n" />
            </ul>
          </div>

          <label
            :class="['block border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors',
              ctx.isDragOver.value
                ? 'border-blue-400 bg-blue-50'
                : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50']"
            @dragover.prevent="ctx.isDragOver.value = true"
            @dragleave.prevent="ctx.isDragOver.value = false"
            @drop.prevent="ctx.handleDrop"
          >
            <input type="file" class="hidden" accept=".xlsx,.xls,.csv" @change="ctx.handleFileChange" />
            <div v-if="ctx.uploading.value || ctx.importLoading.value" class="text-gray-500 text-sm">
              <div class="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
              {{ ctx.uploading.value ? 'Đang tải file...' : 'Đang đọc dữ liệu...' }}
            </div>
            <div v-else>
              <svg class="w-10 h-10 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p class="text-sm text-gray-600 font-medium">Kéo thả file vào đây hoặc click để chọn</p>
              <p class="text-xs text-gray-400 mt-1">Chấp nhận .xlsx, .xls, .csv</p>
            </div>
          </label>
        </template>

        <!-- STEP 2: PREVIEW -->
        <template v-else-if="ctx.importStep.value === 'preview' && ctx.previewData.value">
          <div class="flex items-center gap-4 text-sm flex-wrap">
            <span class="text-gray-600">Tổng: <strong>{{ ctx.previewData.value.totalRows }}</strong> dòng</span>
            <span class="text-green-700">Hợp lệ: <strong>{{ ctx.previewData.value.validRows }}</strong></span>
            <span v-if="ctx.previewData.value.errors.length" class="text-red-600">
              Lỗi: <strong>{{ ctx.previewData.value.errors.length }}</strong>
            </span>
            <span v-if="ctx.previewData.value.warnings.length" class="text-amber-600">
              Cảnh báo: <strong>{{ ctx.previewData.value.warnings.length }}</strong>
            </span>
            <span v-if="ctx.previewData.value.cascadeCount" class="text-amber-600">
              Phụ thuộc: <strong>{{ ctx.previewData.value.cascadeCount }}</strong>
            </span>
            <span class="text-xs text-gray-400 truncate">{{ ctx.uploadedFileName.value }}</span>
          </div>

          <div v-if="ctx.previewData.value.errors.length || ctx.previewData.value.warnings.length"
            class="space-y-1 max-h-48 overflow-y-auto">
            <div
              v-for="(issue, i) in [...ctx.previewData.value.errors, ...ctx.previewData.value.warnings].slice(0, 50)"
              :key="i"
              :class="['flex gap-3 text-xs px-3 py-2 rounded-lg',
                issue.severity === 'error' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700']"
            >
              <span class="font-bold shrink-0">Dòng {{ issue.row }}</span>
              <span class="font-medium shrink-0">{{ issue.field || '—' }}</span>
              <span>{{ issue.message }}</span>
            </div>
            <p v-if="ctx.previewData.value.errors.length + ctx.previewData.value.warnings.length > 50"
              class="text-xs text-gray-400 text-center pt-1">
              Chỉ hiển thị 50 vấn đề đầu tiên — tải báo cáo để xem đầy đủ.
            </p>
          </div>
          <div v-else
            class="bg-green-50 text-green-700 text-sm px-4 py-3 rounded-lg flex items-center gap-2">
            <svg class="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clip-rule="evenodd" />
            </svg>
            Dữ liệu hợp lệ, sẵn sàng import.
          </div>

          <!-- Preview table -->
          <div v-if="ctx.previewData.value.preview.length"
            class="border border-gray-200 rounded-lg overflow-x-auto">
            <p class="text-xs text-gray-500 px-3 pt-2 pb-1 font-medium">Xem trước 10 dòng đầu:</p>
            <table class="w-full text-xs">
              <thead class="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th v-for="fn in ctx.previewData.value.fieldnames.slice(0, previewColumns ?? 6)"
                    :key="fn"
                    class="px-3 py-2 text-left font-medium text-gray-500 whitespace-nowrap">
                    {{ fn }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, ri) in ctx.previewData.value.preview" :key="ri"
                  class="border-t border-gray-100 hover:bg-gray-50">
                  <td v-for="fn in ctx.previewData.value.fieldnames.slice(0, previewColumns ?? 6)"
                    :key="fn"
                    class="px-3 py-1.5 text-gray-700 max-w-[140px] truncate"
                    :title="String(row[fn] ?? '')">
                    {{ row[fn] ?? '—' }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Skip mode picker -->
          <div v-if="ctx.hasBlockingErrors.value && !ctx.allRowsInvalid.value"
            class="rounded-lg border border-amber-200 bg-amber-50 p-4 space-y-3">
            <p class="text-sm font-medium text-amber-900">
              File có {{ ctx.previewData.value.errors.length }} dòng lỗi
              <span v-if="ctx.previewData.value.cascadeCount">
                + {{ ctx.previewData.value.cascadeCount }} dòng phụ thuộc (cha bị bỏ qua)
              </span>
              — chọn cách xử lý:
            </p>
            <fieldset class="space-y-2">
              <label class="flex items-start gap-2 cursor-pointer">
                <input type="radio" v-model="ctx.importMode.value" value="strict" class="mt-1" />
                <div>
                  <p class="text-sm font-medium text-gray-800">Huỷ import, sửa file trước (mặc định)</p>
                  <p class="text-xs text-gray-600">An toàn — đảm bảo file sạch trước khi import.</p>
                </div>
              </label>
              <label class="flex items-start gap-2 cursor-pointer">
                <input type="radio" v-model="ctx.importMode.value" value="skip_invalid" class="mt-1" />
                <div>
                  <p class="text-sm font-medium text-gray-800">
                    Bỏ qua {{ ctx.totalSkip.value }} dòng lỗi, import
                    {{ ctx.previewData.value.totalRows - ctx.totalSkip.value }} dòng hợp lệ
                  </p>
                  <p class="text-xs text-gray-600">
                    Tải báo cáo lỗi sau khi import xong để sửa &amp; import lại các dòng đã bỏ qua.
                  </p>
                </div>
              </label>
            </fieldset>
            <div
              v-if="ctx.importMode.value === 'skip_invalid' && ctx.skipRatio.value > 0.3"
              class="text-xs text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2"
            >
              ⚠ Cảnh báo: hơn {{ Math.round(ctx.skipRatio.value * 100) }}% dòng sẽ bị bỏ qua —
              kiểm tra lại file gốc trước khi tiếp tục.
            </div>
          </div>

          <div v-if="ctx.allRowsInvalid.value"
            class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            Không có dòng hợp lệ nào — toàn bộ file bị lỗi. Hãy sửa file và thử lại.
          </div>

          <!-- Actions -->
          <div class="flex items-center justify-between pt-2">
            <div class="flex gap-2">
              <button class="text-xs text-gray-500 hover:text-gray-700 underline"
                @click="ctx.importStep.value = 'upload'">
                ← Đổi file
              </button>
              <button v-if="ctx.previewData.value.errors.length"
                class="text-xs text-red-600 hover:text-red-800 underline"
                @click="ctx.downloadErrorReport">
                Tải báo cáo lỗi (.xlsx)
              </button>
            </div>
            <button
              :disabled="!ctx.canImport.value"
              :class="['px-4 py-2 text-sm rounded-lg font-medium transition-colors flex items-center gap-2',
                !ctx.canImport.value
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-emerald-600 hover:bg-emerald-700 text-white']"
              @click="ctx.runImport"
            >
              <div v-if="ctx.importLoading.value"
                class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              {{ ctx.importLoading.value
                  ? 'Đang import...'
                  : ctx.importMode.value === 'skip_invalid'
                    ? `Import ${ctx.previewData.value.totalRows - ctx.totalSkip.value} dòng (bỏ qua ${ctx.totalSkip.value}) ▶`
                    : 'Bắt đầu Import ▶' }}
            </button>
          </div>
        </template>

        <!-- STEP 3: RESULT -->
        <template v-else-if="ctx.importStep.value === 'result' && ctx.importResult.value">
          <div :class="['p-5 rounded-xl text-center',
            ctx.importResult.value.failed === 0 && ctx.importResult.value.skipped === 0
              ? 'bg-green-50'
              : ctx.importResult.value.success === 0
                ? 'bg-red-50'
                : 'bg-amber-50']">
            <p class="text-3xl font-bold mb-1"
              :class="ctx.importResult.value.failed === 0 && ctx.importResult.value.skipped === 0
                ? 'text-green-700'
                : ctx.importResult.value.success === 0
                  ? 'text-red-700'
                  : 'text-amber-700'">
              {{ ctx.importResult.value.success }} / {{ ctx.importResult.value.total }}
            </p>
            <p class="text-sm text-gray-600">
              {{ unit ?? 'dòng' }} import thành công
              <span v-if="ctx.importResult.value.failed">
                — <span class="text-red-600 font-medium">{{ ctx.importResult.value.failed }} lỗi</span>
              </span>
              <span v-if="ctx.importResult.value.skipped">
                — <span class="text-amber-700 font-medium">{{ ctx.importResult.value.skipped }} bỏ qua</span>
              </span>
            </p>
          </div>

          <!-- Failed rows -->
          <div v-if="ctx.importResult.value.errors.length"
            class="space-y-1 max-h-40 overflow-y-auto">
            <p class="text-xs font-medium text-gray-500">Chi tiết lỗi:</p>
            <div v-for="(e, i) in ctx.importResult.value.errors" :key="i"
              class="flex gap-3 text-xs px-3 py-2 bg-red-50 text-red-700 rounded-lg">
              <span class="font-bold shrink-0">Dòng {{ e.row }}</span>
              <span>{{ e.message }}</span>
            </div>
          </div>

          <!-- Skipped rows -->
          <div v-if="ctx.importResult.value.skippedRows.length" class="space-y-2">
            <div class="flex items-center justify-between">
              <p class="text-xs font-medium text-gray-500">
                Đã bỏ qua {{ ctx.importResult.value.skipped }} dòng:
              </p>
              <button class="text-xs text-amber-700 hover:text-amber-900 underline"
                @click="ctx.downloadErrorReport">
                Tải file dòng bị bỏ qua (.xlsx)
              </button>
            </div>
            <div class="space-y-1 max-h-40 overflow-y-auto">
              <div v-for="(s, i) in ctx.importResult.value.skippedRows" :key="i"
                class="flex gap-3 text-xs px-3 py-2 bg-amber-50 text-amber-800 rounded-lg">
                <span class="font-bold shrink-0">Dòng {{ s.row }}</span>
                <span class="font-medium shrink-0">{{ s.field || '—' }}</span>
                <span class="flex-1">{{ s.message }}</span>
                <span v-if="s.reason === 'cascade_parent_skipped'"
                  class="shrink-0 px-1.5 py-0.5 rounded bg-amber-200 text-amber-900 text-[10px] font-medium">
                  phụ thuộc
                </span>
              </div>
            </div>
          </div>

          <div class="flex justify-between pt-2">
            <button v-if="ctx.importResult.value.failed > 0 || ctx.importResult.value.skipped > 0"
              class="text-xs text-gray-500 hover:text-gray-700 underline"
              @click="ctx.importStep.value = 'upload'">
              ← Import lô khác
            </button>
            <button class="ml-auto px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              @click="ctx.close">
              Đóng
            </button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
