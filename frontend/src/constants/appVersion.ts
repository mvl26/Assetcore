// Phiên bản AssetCore — SSoT DUY NHẤT cho mọi chỗ hiển thị version trên UI.
//
// Chuỗi thoát ra khỏi file này bằng đúng một đường: Vite `define` bơm
// `__APP_VERSION__` từ `frontend/package.json` (khai ở CẢ `vite.config.ts` lẫn
// `vitest.config.ts` — hai config độc lập, không thừa kế nhau).
//
// Trục đồng bộ toàn hệ thống:
//   assetcore/__init__.py::__version__   ← SSoT sản phẩm (BE, OpenAPI info.version,
//                                            cache-key spec, version-stamp capabilities)
//   frontend/package.json::version       ← bản sao FE, PHẢI khớp BE
//   __APP_VERSION__ → APP_VERSION        ← mọi view đọc từ đây
// `appVersion.test.ts` chặn drift giữa hai file trên và chặn hardcode chuỗi
// version trong `src/`. Nâng version = sửa ĐÚNG 2 file, không sửa view nào.
declare const __APP_VERSION__: string

/** Phiên bản trần, vd `'0.2.0'`. `'0.0.0'` = build thiếu `define` (khớp fallback BE `_app_version()`). */
export const APP_VERSION: string =
  typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : '0.0.0'

/** Dạng hiển thị có tiền tố, vd `'v0.2.0'` — dùng cho footer / about / topbar. */
export const APP_VERSION_LABEL = `v${APP_VERSION}`

/** Nhãn đầy đủ kèm tên sản phẩm, vd `'AssetCore v0.2.0'`. */
export const APP_VERSION_FULL_LABEL = `AssetCore ${APP_VERSION_LABEL}`
