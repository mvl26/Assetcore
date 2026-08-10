// Copyright (c) 2026, AssetCore Team
// Upload tệp đính kèm dùng chung — SSoT cho MỌI field Attach / Attach Image.
//
// QUY TẮC (xem .claude/skills/assetcore-fe): field đính kèm KHÔNG BAO GIỜ được
// render bằng <input type="text"> để người dùng tự gõ đường dẫn "/files/...".
// Tệp phải được TẢI LÊN và lưu vào hệ thống qua endpoint gate quyền dưới đây;
// UI dùng component `FileUploadField.vue`.

import api from './axios'

const UPLOAD_URL = '/api/method/assetcore.api.files.upload_attachment'

export interface UploadedFile {
  name: string
  file_url: string
  file_name: string
  is_private: number
}

export interface UploadAttachmentOptions {
  /** DocType chứa field đính kèm (có thể là bảng con, vd 'Vendor Cert'). */
  doctype: string
  /** Tên field Attach / Attach Image trên `doctype`. */
  fieldname: string
  /** Bản ghi cha để gắn tệp vào — bỏ trống ở màn hình tạo mới. */
  docname?: string
  /** DocType cha — BẮT BUỘC khi `doctype` là bảng con. */
  parentDoctype?: string
}

/**
 * Tải một tệp lên hệ thống và trả về `file_url` để lưu vào field đính kèm.
 *
 * Không dùng `/api/method/upload_file` trần — endpoint AssetCore gate quyền theo
 * capability của hồ sơ đích và chỉ chấp nhận field Attach thật.
 */
export async function uploadAttachment(
  file: File,
  opts: UploadAttachmentOptions,
): Promise<UploadedFile> {
  const form = new FormData()
  form.append('file', file, file.name)
  form.append('doctype', opts.doctype)
  form.append('fieldname', opts.fieldname)
  if (opts.docname) form.append('docname', opts.docname)
  if (opts.parentDoctype) form.append('parent_doctype', opts.parentDoctype)

  // axios v1 tự điền boundary multipart khi data là FormData và Content-Type
  // được đặt 'multipart/form-data' (ghi đè default 'application/json' của instance).
  const res = await api.post<{ message: { success: boolean; data: UploadedFile; error?: string } }>(
    UPLOAD_URL, form, { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  const env = res.data?.message
  if (!env?.success || !env.data?.file_url) {
    throw new Error(env?.error || 'Tải tệp lên thất bại')
  }
  return env.data
}

/** Tên tệp hiển thị suy ra từ đường dẫn đã lưu. */
export function fileNameFromUrl(url: string): string {
  if (!url) return ''
  try {
    return decodeURIComponent(url.split('?')[0].split('/').pop() || url)
  } catch {
    return url
  }
}
