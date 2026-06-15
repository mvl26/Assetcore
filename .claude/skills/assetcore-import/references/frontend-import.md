# Frontend (FE) — Import Wizard

Heavy reference cho phần Frontend của import. Đọc khi viết/sửa `frontend/src/api/importData.ts`,
`ReferenceDataView.vue` / `ImportWizardView.vue`, `frontend/src/types/import.ts`.

---

## 2.1 File structure (hiện tại)

```
frontend/src/
├── api/
│   └── importData.ts               ← typed API client
├── views/
│   └── master-data/
│       └── ReferenceDataView.vue   ← tích hợp import vào tab ref-data
└── types/
    └── import.ts                   ← RefDataDoctype, ImportPreviewResult, ImportResult, ...
```

## 2.2 Types (`types/import.ts`)

```typescript
export type RefDataDoctype = "AC Asset Category" | "AC Department" | "AC Location"

export type ImportMode = "strict" | "skip_invalid"

export interface ImportIssue {
  row: number
  field: string
  message: string
  severity: "error" | "warning"
}

export interface ImportPreviewResult {
  doctype: RefDataDoctype
  totalRows: number
  validRows: number
  preview: Record<string, unknown>[]
  fieldnames: string[]
  errors: ImportIssue[]
  warnings: ImportIssue[]
  cascadeCount?: number   // chỉ có cho Tree DocType (vd AC Location)
}

export interface ImportSkippedRow {
  row: number
  reason: "pre_validate" | "cascade_parent_skipped"
  field: string
  message: string
}

export interface ImportResult {
  total: number
  success: number
  failed: number
  skipped: number            // số dòng bị bỏ qua (mode skip_invalid)
  errors: ImportIssue[]
  skippedRows: ImportSkippedRow[]
}

export interface ErrorReportResult {
  fileUrl: string
  errorCount: number
}
```

## 2.3 API client (`api/importData.ts`) — BASE URL bắt buộc

```typescript
// ĐÚNG — frappePost/frappeGet nhận full path bao gồm /api/method/
const BASE = '/api/method/assetcore.api.import_data'

export async function previewRefImport(doctype, fileUrl): Promise<ImportPreviewResult> {
  const raw = await frappePost(`${BASE}.preview_ref_data`, { doctype, file_url: fileUrl })
  // map snake_case → camelCase ở đây, không để component tự map
}

export async function importRefData(
  doctype: RefDataDoctype,
  fileUrl: string,
  mode: ImportMode = "strict",
): Promise<ImportResult> {
  const raw = await frappePost(`${BASE}.import_ref_data`, {
    doctype,
    file_url: fileUrl,
    skip_invalid: mode === "skip_invalid",
  })
  // map snake_case → camelCase
  return {
    total: raw.total, success: raw.success, failed: raw.failed,
    skipped: raw.skipped ?? 0,
    errors: raw.errors ?? [],
    skippedRows: (raw.skipped_rows ?? []).map((r: any) => ({
      row: r.row, reason: r.reason, field: r.field, message: r.message,
    })),
  }
}

export async function buildErrorReport(doctype, fileUrl): Promise<ErrorReportResult> {
  const raw = await frappePost(`${BASE}.build_error_report`, { doctype, file_url: fileUrl })
  return { fileUrl: raw.file_url, errorCount: raw.error_count }
}

export function getExportUrl(doctype: RefDataDoctype): string {
  return `${BASE}.export_ref_data?doctype=${encodeURIComponent(doctype)}`
}

export function getTemplateUrl(doctype: RefDataDoctype): string {
  return `${BASE}.download_template?doctype=${encodeURIComponent(doctype)}`
}

export async function initImportFolders(doctype: RefDataDoctype): Promise<string> {
  const raw = await frappeGet<{ folder: string }>(`${BASE}.init_import_folders`, { doctype })
  return raw.folder
}

// SAI — thiếu /api/method/ → 404 "Không tìm thấy tài nguyên yêu cầu"
frappePost("assetcore.api.import_data.preview_ref_data", ...)   // ← KHÔNG
```

## 2.4 File upload trong Vue — bắt buộc override Content-Type

```typescript
// ĐÚNG — Axios instance mặc định Content-Type: application/json
// khi gửi FormData, header này phải bị xóa để browser tự set multipart boundary

const fd = new FormData()
fd.append('file', file)
fd.append('is_private', '1')
fd.append('folder', importFolder.value)   // folder đã được init_import_folders tạo

const res = await api.post<{ message: { file_url: string } }>(
  '/api/method/upload_file',
  fd,
  { headers: { 'Content-Type': undefined as unknown as string } },  // ← bắt buộc
)
const fileUrl = res.data.message.file_url

// SAI — không override → Axios gửi Content-Type: application/json với FormData
// → Frappe không parse được file → "Fields `file_name` or `file_url` must be set for File"
await api.post('/api/method/upload_file', fd)   // ← thiếu headers override
```

File import phải là **private** (`is_private: '1'`) — đây là dữ liệu bệnh viện.

## 2.5 Sequence bắt buộc trong openImport()

```typescript
async function openImport(file: File) {
  // 1. Tạo folder trước — PHẢI làm trước upload
  importFolder.value = await initImportFolders(currentDoctype())

  // 2. Upload file với folder đã được commit vào DB
  const fd = new FormData()
  fd.append('file', file)
  fd.append('is_private', '1')
  fd.append('folder', importFolder.value)
  const res = await api.post('/api/method/upload_file', fd,
    { headers: { 'Content-Type': undefined as unknown as string } })
  const fileUrl = res.data.message.file_url

  // 3. Preview với file_url vừa upload
  previewResult.value = await previewRefImport(currentDoctype(), fileUrl)
}
```

## 2.6 Skip-Invalid Mode UX (ImportWizardView — bước 3 Confirm)

Khi preview phát hiện `errors.length > 0`, hiển thị radio 2-mode (KHÔNG default skip):

```vue
<div v-if="preview.errors.length" class="rounded-lg border border-amber-200 bg-amber-50 p-4">
  <p class="font-medium text-amber-900">
    File có {{ preview.errors.length }} dòng lỗi
    <span v-if="preview.cascadeCount">
      + {{ preview.cascadeCount }} dòng phụ thuộc (cha bị bỏ qua)
    </span>
  </p>

  <fieldset class="mt-3 space-y-2">
    <label class="flex items-start gap-2">
      <input type="radio" v-model="importMode" value="strict" class="mt-1" />
      <div>
        <p class="font-medium">Huỷ import, sửa file trước (mặc định)</p>
        <p class="text-sm text-slate-600">An toàn — đảm bảo file sạch trước khi import</p>
      </div>
    </label>
    <label class="flex items-start gap-2">
      <input type="radio" v-model="importMode" value="skip_invalid" class="mt-1" />
      <div>
        <p class="font-medium">
          Bỏ qua {{ totalSkip }} dòng lỗi, import {{ preview.totalRows - totalSkip }} dòng hợp lệ
        </p>
        <p class="text-sm text-slate-600">
          Tải file dòng bị bỏ qua sau khi import xong để sửa & import lại sau
        </p>
      </div>
    </label>
  </fieldset>
</div>

<script setup>
const importMode = ref<ImportMode>('strict')
const totalSkip = computed(() =>
  preview.value.errors.length + (preview.value.cascadeCount ?? 0)
)

async function runImport() {
  result.value = await importRefData(currentDoctype(), fileUrl.value, importMode.value)
}
</script>
```

**Bước 4 (Result)**: hiển thị card riêng cho `skipped` với button "Tải file dòng bị bỏ qua" (gọi `buildErrorReport` với cùng `file_url`).

```vue
<div v-if="result.skipped > 0" class="rounded-lg border border-amber-200 bg-amber-50 p-4">
  <p class="font-medium">Đã bỏ qua {{ result.skipped }} dòng</p>
  <ul class="mt-2 max-h-48 overflow-auto text-sm">
    <li v-for="r in result.skippedRows" :key="r.row">
      Dòng {{ r.row }} — {{ r.message }}
      <span v-if="r.reason === 'cascade_parent_skipped'"
            class="ml-1 rounded bg-amber-200 px-1 text-xs">phụ thuộc</span>
    </li>
  </ul>
  <button @click="downloadSkippedReport" class="mt-3 text-sm font-medium text-amber-700">
    Tải file dòng bị bỏ qua
  </button>
</div>
```

**Rule UX bắt buộc**:
- Default mode = `strict` — KHÔNG auto-select skip để tránh user import thiếu data mà không biết.
- Cảnh báo cascade phải hiển thị TRƯỚC khi user chọn skip — không silent.
- Nếu `totalSkip / preview.totalRows > 0.3` (>30%) → thêm warning đỏ "Cảnh báo: hơn 30% dòng bị bỏ qua, kiểm tra lại file gốc".
- Nếu `totalSkip === preview.totalRows` (100% invalid) → disable nút "Import" cả 2 mode, hiện thông báo "Không có dòng hợp lệ".

## 2.7 Template download — dùng URL trực tiếp, không gọi API

```typescript
// ĐÚNG — mở URL trực tiếp, browser tự xử lý Content-Disposition
function downloadTemplate(doctype: RefDataDoctype) {
  window.open(getTemplateUrl(doctype), '_blank')
  // hoặc: window.location.href = getTemplateUrl(doctype)
}

// Mỗi doctype phải map đúng file riêng của nó:
// "AC Asset Category" → download_template?doctype=AC%20Asset%20Category
//   → BE trả 01a_danh_muc_tai_san.xlsx
// "AC Department"     → download_template?doctype=AC%20Department
//   → BE trả 01b_khoa_phong.xlsx
// "AC Location"       → download_template?doctype=AC%20Location
//   → BE trả 01c_vi_tri.xlsx
```

---

## Phần 3 — Anti-patterns FE (chi tiết, KHÔNG làm)

> Tóm tắt dạng table ở SKILL.md §Common Rationalizations. Chi tiết đầy đủ giữ ở đây.

10. **Gọi `api.post('/api/method/upload_file', formData)` không override Content-Type** — Axios instance default `Content-Type: application/json` phá multipart boundary. Phải pass `{ headers: { 'Content-Type': undefined as unknown as string } }`.

11. **Upload file trước khi gọi `initImportFolders()`** — folder chưa tồn tại, Frappe reject với *"Could not find Folder: ..."*.

12. **`frappePost("assetcore.api.import_data.preview")` không có `/api/method/`** — 404. Dùng `const BASE = '/api/method/assetcore.api.import_data'` rồi `${BASE}.preview_ref_data`.

13. **Download template bằng cách gọi API thay vì mở URL trực tiếp** — `getTemplateUrl()` trả URL để `window.open()`, không phải để `frappeGet()`.

14. **Dùng 1 template URL cho tất cả tab** — mỗi tab ref-data có doctype riêng, `getTemplateUrl(currentDoctype())` phải được gọi với đúng doctype của tab đang active.
