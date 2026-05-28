// Copyright (c) 2026, AssetCore Team
import { computed, ref } from 'vue'

import api from '@/api/axios'
import {
  buildErrorReport, getExportUrl, getTemplateUrl,
  importRefData, initImportFolders, previewRefImport,
} from '@/api/importData'
import { useToast } from '@/composables/useToast'
import type {
  ImportMode, ImportPreviewResult, ImportResult, ImportStep, RefDataDoctype,
} from '@/types/import'

/**
 * State + handlers for the import wizard. Shared by every list view that
 * lets users bulk-import a DocType — keeps wizard UX consistent and folds
 * skip-invalid mode, cascade preview, and error reporting in one place.
 *
 * Each view renders the wizard via `<ImportWizardModal>` and wires its own
 * "reload on success" via the returned `onSuccess` callback.
 */
export function useImportWizard(doctype: RefDataDoctype, onSuccess?: () => void) {
  const toast = useToast()

  const showImport = ref(false)
  const importStep = ref<ImportStep>('upload')
  const uploading = ref(false)
  const importLoading = ref(false)
  const uploadedFileUrl = ref('')
  const uploadedFileName = ref('')
  const importFolder = ref('Home/Attachments')
  const previewData = ref<ImportPreviewResult | null>(null)
  const importResult = ref<ImportResult | null>(null)
  const importErr = ref('')
  const isDragOver = ref(false)
  const importMode = ref<ImportMode>('strict')

  async function open() {
    showImport.value = true
    importStep.value = 'upload'
    uploadedFileUrl.value = ''
    uploadedFileName.value = ''
    previewData.value = null
    importResult.value = null
    importErr.value = ''
    importMode.value = 'strict'
    try {
      importFolder.value = await initImportFolders(doctype)
    } catch {
      importFolder.value = 'Home/Attachments'
    }
  }

  function close() {
    showImport.value = false
    if (
      importStep.value === 'result'
      && (importResult.value?.success ?? 0) > 0
      && onSuccess
    ) onSuccess()
  }

  async function handleFileChange(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0]
    if (file) await _uploadAndPreview(file)
  }

  async function handleDrop(event: DragEvent) {
    isDragOver.value = false
    const file = event.dataTransfer?.files?.[0]
    if (file) await _uploadAndPreview(file)
  }

  async function _uploadAndPreview(file: File) {
    uploading.value = true
    importErr.value = ''
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('is_private', '1')
      fd.append('folder', importFolder.value)
      const res = await api.post<{ message: { file_url: string } }>(
        '/api/method/upload_file', fd,
        { headers: { 'Content-Type': undefined as unknown as string } },
      )
      uploadedFileUrl.value = res.data.message.file_url
      uploadedFileName.value = file.name
      await runPreview()
    } catch (e: unknown) {
      importErr.value = e instanceof Error ? e.message : 'Lỗi upload file'
    } finally {
      uploading.value = false
    }
  }

  async function runPreview() {
    importLoading.value = true
    importErr.value = ''
    try {
      previewData.value = await previewRefImport(doctype, uploadedFileUrl.value)
      importStep.value = 'preview'
    } catch (e: unknown) {
      importErr.value = e instanceof Error ? e.message : 'Lỗi đọc file'
    } finally {
      importLoading.value = false
    }
  }

  async function runImport() {
    importLoading.value = true
    importErr.value = ''
    try {
      importResult.value = await importRefData(doctype, uploadedFileUrl.value, importMode.value)
      importStep.value = 'result'
    } catch (e: unknown) {
      importErr.value = e instanceof Error ? e.message : 'Lỗi import'
    } finally {
      importLoading.value = false
    }
  }

  async function downloadErrorReport() {
    try {
      const r = await buildErrorReport(doctype, uploadedFileUrl.value)
      globalThis.open(r.fileUrl, '_blank')
    } catch {
      toast.error('Không tạo được báo cáo lỗi')
    }
  }

  function doExport() {
    globalThis.location.href = getExportUrl(doctype)
  }

  function doDownloadTemplate() {
    globalThis.location.href = getTemplateUrl(doctype)
  }

  const hasBlockingErrors = computed(
    () => (previewData.value?.errors ?? []).some(e => e.severity === 'error'),
  )

  const totalSkip = computed(() => {
    const p = previewData.value
    if (!p) return 0
    return p.errors.length + (p.cascadeCount ?? 0)
  })

  const skipRatio = computed(() => {
    const p = previewData.value
    if (!p || p.totalRows === 0) return 0
    return totalSkip.value / p.totalRows
  })

  const allRowsInvalid = computed(
    () => previewData.value !== null
      && totalSkip.value >= previewData.value.totalRows,
  )

  const canImport = computed(() => {
    if (!previewData.value || importLoading.value) return false
    if (allRowsInvalid.value) return false
    if (!hasBlockingErrors.value) return true
    return importMode.value === 'skip_invalid'
  })

  return {
    // state
    showImport, importStep, uploading, importLoading,
    uploadedFileUrl, uploadedFileName, importFolder,
    previewData, importResult, importErr, isDragOver, importMode,
    // actions
    open, close, handleFileChange, handleDrop,
    runImport, downloadErrorReport, doExport, doDownloadTemplate,
    // derived
    hasBlockingErrors, totalSkip, skipRatio, allRowsInvalid, canImport,
  }
}

export type ImportWizardCtx = ReturnType<typeof useImportWizard>
