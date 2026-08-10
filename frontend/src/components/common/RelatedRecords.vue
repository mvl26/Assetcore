<script setup lang="ts">
// Copyright (c) 2026, AssetCore Team
// «Bản ghi liên quan» — NỘI DUNG MỘT TAB dùng chung cho MỌI màn chi tiết.
//
// Toàn bộ nội dung đến từ đồ thị liên kết khai ở backend (`<doctype>_dashboard.py`),
// nên thêm một liên kết mới KHÔNG phải sửa file này. Component chỉ lo hiển thị.
//
// Component KHÔNG tự vẽ tiêu đề hay khung thẻ: nó là phần thân của một tab, tiêu đề
// là tên tab do màn chi tiết gắn (`defineExpose` phơi `total` để tab hiện badge số).
// Trước đây khối này là một thẻ dài chiếm hết màn mà chỉ hiện được con số — nay mỗi ô
// hiện DỮ LIỆU THẬT (tối đa 5 dòng) và chỉ dựng nút khi nút đó thật sự đi tới đâu đó.
//
// Chỉ ô CÓ dữ liệu được dựng thành khối (AC-CR-93): tab của một thiết bị có 19 ô mà
// thường chỉ 3 ô có bản ghi, nên 16 khối còn lại chỉ để nói "0". Ô rỗng KHÔNG bị ẩn hẳn
// — chúng được nêu tên bằng tiếng Việt trong đúng MỘT dòng gộp của chính nhóm nó, để vẫn
// phân biệt được "chưa có gì" với "chưa tải xong".
//
// Năm lời hứa được giữ bằng test (`RelatedRecords.test.ts`):
//   • nhãn 100% tiếng Việt — không rò tên DocType tiếng Anh;
//   • 0 nút chết — không route chi tiết ⇒ text tĩnh; màn đích KHÔNG lọc được theo hồ sơ
//     cha ⇒ không «Xem tất cả» (dựng nút = dẫn ra danh sách toàn hệ thống); cả nút
//     «Xem tất cả» lẫn «Tạo …» còn phải qua capability của CHÍNH route đích;
//   • cắt bớt trung thực — chạm trần đếm ⇒ '100+', không bao giờ bịa "còn N bản ghi";
//   • «Tạo từ ngữ cảnh cha» — nút tạo mang theo hồ sơ cha qua query prefill, không bao
//     giờ sinh query rác (`?asset=undefined`) khi backend không gửi giá trị;
//   • dòng gộp ô rỗng là TEXT TĨNH — 0 nút, 0 link, 0 toggle.
//
// AC-CR-105 — «Tạo từ ngữ cảnh cha» cho ô 0 bản ghi: thứ người dùng cần tạo GẦN NHƯ LUÔN
// là thứ chưa có (ô `total === 0`), nên khi gộp ô rỗng thành một dòng (AC-CR-93) nút tạo
// mất chỗ treo và cả tính năng thành nút chết. Lời hứa cũ "dòng gộp là TEXT TĨNH" được
// GIỮ NGUYÊN bằng cách đặt chip ra khối SIBLING `conn-empty-actions` NGAY SAU thẻ `<p>`:
// câu «Chưa có: …» vẫn 0 nút/0 link, và mọi điều hướng vẫn đi qua ĐÚNG MỘT `openCreate`
// (nhánh push thứ hai = chỗ để 3 lớp gate lệch nhau âm thầm).
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  getConnections, detailRouteForDoctype, listTarget,
  viLabel, countBadge, previewMeta, createTarget, createLabel,
  dataCells, emptyCreatables, emptySummary,
  type ConnectionGroup, type ConnectionItem, type ConnectionPreviewRow, type CreateTarget,
  type ListTarget,
} from '@/api/connections'
import { canAccessCreateRoute, canAccessDrill } from '@/router/routeAccess'
import { useCapabilities } from '@/composables/useCapabilities'
import { toApiError } from '@/api/errors'
import { formatDate } from '@/utils/formatters'

const props = defineProps<{
  /** DocType của bản ghi đang xem, vd 'AC Asset'. */
  doctype: string
  /** Mã bản ghi đang xem. */
  name: string
}>()

const router = useRouter()
const { can } = useCapabilities()
const groups = ref<ConnectionGroup[]>([])
const total = ref(0)
const loading = ref(false)
const errorMessage = ref('')

async function load(): Promise<void> {
  if (!props.doctype || !props.name) return
  loading.value = true
  errorMessage.value = ''
  try {
    const payload = await getConnections(props.doctype, props.name)
    groups.value = payload.groups
    total.value = payload.total
  } catch (e: unknown) {
    // Khối phụ trợ: hỏng thì báo và cho thử lại, KHÔNG được làm vỡ màn chi tiết.
    errorMessage.value = toApiError(e).message || 'Không tải được bản ghi liên quan.'
    groups.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => [props.doctype, props.name], load)

/**
 * Có ít nhất một ô mang dữ liệu trên TOÀN payload?
 *
 * Điều kiện của câu «Chưa có bản ghi nào liên quan…» — nới từ `groups.length === 0` (vòng
 * 2) sang "không ô nào có dữ liệu", vì backend luôn trả đủ nhóm/ô kể cả khi mọi ô đều 0.
 * Câu này trả lời "hồ sơ này có gì không?", còn các dòng gộp trả lời "cụ thể chưa có
 * những loại nào" — hai câu hỏi khác nhau ⇒ CẢ HAI cùng hiện, không thay nhau.
 *
 * Vị-từ "ô này có dữ liệu chưa?" nằm ở `api/connections.ts` (`dataCells`) — component
 * KHÔNG giữ bản sao, để hợp đồng chỉ có một chỗ để lệch.
 */
const hasAnyData = computed(() => groups.value.some((g) => dataCells(g).length > 0))

// ── Điều hướng ──────────────────────────────────────────────────────────────
/** Dòng preview chỉ bấm được khi doctype có màn chi tiết thật (không dẫn tới 404). */
function rowPath(item: ConnectionItem, row: ConnectionPreviewRow): string | null {
  return detailRouteForDoctype(item.doctype, row.name)
}

function openRow(item: ConnectionItem, row: ConnectionPreviewRow): void {
  const path = rowPath(item, row)
  if (!path) return
  router.push(path)
}

/**
 * Đích của nút «Xem tất cả», hoặc null ⇒ KHÔNG dựng nút. Ba lớp, phải qua cả ba
 * (cùng khuôn với nút «Tạo …» — ADR D-CR5-5):
 *  1. hợp đồng dữ liệu (`listTarget`: doctype có màn LỌC ĐƯỢC + khoá dịch được);
 *  2. route có thật trong FE;
 *  3. capability của CHÍNH route đích — thiếu thì bấm xong bị route-guard đá ra
 *     `/unauthorized`, cũng là "nút chết".
 *
 * Lớp 1 là thứ vòng này thêm: trước đây chỉ cần "có ≥1 khoá lọc" nên nút vẫn mọc cho ô
 * mà màn đích KHÔNG đọc khoá nào — bấm ra danh sách toàn hệ thống trong khi ô vừa hứa
 * "6 bản ghi" (đúng bug người dùng báo).
 */
function seeAllFor(item: ConnectionItem): ListTarget | null {
  const target = listTarget(item)
  if (!target) return null
  if (!routeExists(target.path)) return null
  if (!canAccessDrill(target.path, can)) return null
  return target
}

function openAll(item: ConnectionItem): void {
  const target = seeAllFor(item)
  if (!target) return
  router.push({ path: target.path, query: target.query })
}

/** Gợi ý đường dẫn của backend có phân giải được thành route thật không (không dẫn tới 404). */
function routeExists(path: string): boolean {
  try {
    const resolved = router.resolve(path) as { matched?: unknown[] } | undefined
    return (resolved?.matched?.length ?? 0) > 0
  } catch {
    return false
  }
}

/**
 * Đích của nút «Tạo …», hoặc null ⇒ KHÔNG dựng nút. Ba lớp, phải qua cả ba:
 *  1. hợp đồng backend (`createTarget`: quyền tạo + hint + prefill đã lọc);
 *  2. route có thật trong FE — backend chỉ biết quyền, không biết màn hình nào đã có;
 *  3. capability của CHÍNH route đích — nếu không, người dùng bấm xong bị route-guard
 *     đá ra `/unauthorized`, đúng loại "nút chết" mà vòng này xoá.
 */
function createFor(item: ConnectionItem): CreateTarget | null {
  const target = createTarget(item)
  if (!target) return null
  if (!routeExists(target.path)) return null
  if (!canAccessCreateRoute(target.path, can)) return null
  return target
}

/**
 * Ô RỖNG được phép mọc chip «+ Tạo …» — giao của "ô rỗng" và "qua đủ 3 lớp gate tạo".
 *
 * Dùng CHÍNH `createFor` (không phải một vị-từ thứ hai): nếu chip có điều kiện riêng thì
 * sẽ có ngày chip hiện mà `openCreate` không đi đâu — đúng loại nút chết vòng này xoá.
 * `emptyCreatables` là phần bù của `dataCells` ⇒ chip KHÔNG bao giờ trùng với nút «Tạo …»
 * của ô có dữ liệu (mỗi ô thuộc đúng một trong hai nhánh).
 */
function emptyChips(group: ConnectionGroup): ConnectionItem[] {
  return emptyCreatables(group).filter((item) => createFor(item) !== null)
}

function openCreate(item: ConnectionItem): void {
  const target = createFor(item)
  if (!target) return
  // Có prefill ⇒ đẩy kèm query để màn tạo điền sẵn hồ sơ cha; không có ⇒ push trần
  // (KHÔNG gửi `query: {}` để URL không mọc dấu '?' vô nghĩa).
  router.push(target.query ? { path: target.path, query: target.query } : { path: target.path })
}

defineExpose({ reload: load, total })
</script>

<template>
  <div data-testid="related-records">
    <p v-if="loading" class="py-6 text-sm text-slate-500 dark:text-slate-400">
      Đang tải bản ghi liên quan…
    </p>

    <div v-else-if="errorMessage" class="py-6">
      <p class="text-sm text-rose-600 dark:text-rose-400">{{ errorMessage }}</p>
      <button
        type="button"
        class="mt-2 rounded border border-slate-300 px-3 py-1 text-sm text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700"
        @click="load"
      >
        Thử lại
      </button>
    </div>

    <div v-else class="space-y-5">
      <!-- Không ô nào có dữ liệu ⇒ nói thẳng; các dòng gộp bên dưới vẫn nêu tên từng loại. -->
      <p v-if="!hasAnyData" class="pt-6 text-sm text-slate-500 dark:text-slate-400">
        Chưa có bản ghi nào liên quan tới hồ sơ này.
      </p>

      <template v-for="group in groups" :key="group.label">
        <!-- Nhóm 0 ô (hoặc mọi nhãn rỗng) ⇒ không dựng khung trống. -->
        <div
          v-if="dataCells(group).length || emptySummary(group) || emptyChips(group).length"
          data-testid="conn-group"
        >
          <!-- Nhóm toàn rỗng ⇒ bỏ tiêu đề: dòng gộp đã tự mô tả bằng danh từ nghiệp vụ. -->
          <h3
            v-if="dataCells(group).length"
            data-testid="conn-group-label"
            class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"
          >
            {{ viLabel(group) }}
          </h3>

          <ul v-if="dataCells(group).length" class="space-y-3">
            <li
              v-for="item in dataCells(group)"
              :key="item.doctype"
              data-testid="conn-item"
              class="border-l-2 border-slate-200 pl-3 dark:border-slate-700"
            >
              <!-- Dòng tiêu đề ô: nhãn tiếng Việt + số đếm + dải cắt bớt -->
              <div class="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                <span class="text-sm font-medium text-slate-800 dark:text-slate-100">
                  {{ viLabel(item) }}
                </span>
                <!-- Mọi ô được render đều CÓ dữ liệu ⇒ nhánh badge xám (số 0) không còn
                     đường tới, đã gỡ thay vì để lại nhánh chết. -->
                <span
                  data-testid="conn-count"
                  class="rounded-full bg-sky-100 px-1.5 py-0.5 text-xs font-semibold text-sky-800 dark:bg-sky-900 dark:text-sky-200"
                >
                  {{ countBadge(item) }}
                </span>
                <span
                  v-if="previewMeta(item)"
                  data-testid="conn-meta"
                  class="text-xs text-slate-500 dark:text-slate-400"
                >
                  {{ previewMeta(item) }}
                </span>
              </div>

              <!-- Xem trước: dữ liệu thật, không phải mỗi con số -->
              <ul v-if="item.items && item.items.length" class="mt-1.5 space-y-0.5">
                <li v-for="row in item.items" :key="row.name">
                  <button
                    v-if="rowPath(item, row)"
                    type="button"
                    data-testid="conn-row"
                    :aria-label="`Mở ${viLabel(item)}: ${row.title}`"
                    class="flex w-full flex-wrap items-baseline gap-x-2 rounded px-1.5 py-1 text-left text-sm text-slate-700 hover:bg-sky-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 dark:text-slate-200 dark:hover:bg-slate-700"
                    @click="openRow(item, row)"
                  >
                    <span class="min-w-0 flex-1 truncate">{{ row.title }}</span>
                    <span v-if="row.status_label" class="shrink-0 text-xs text-slate-500 dark:text-slate-400">
                      {{ row.status_label }}
                    </span>
                    <span class="shrink-0 text-xs tabular-nums text-slate-400 dark:text-slate-500">
                      {{ formatDate(row.date) }}
                    </span>
                  </button>

                  <span
                    v-else
                    data-testid="conn-row"
                    title="Chưa có màn hình chi tiết cho nhóm này"
                    class="flex w-full flex-wrap items-baseline gap-x-2 px-1.5 py-1 text-sm text-slate-600 dark:text-slate-300"
                  >
                    <span class="min-w-0 flex-1 truncate">{{ row.title }}</span>
                    <span v-if="row.status_label" class="shrink-0 text-xs text-slate-500 dark:text-slate-400">
                      {{ row.status_label }}
                    </span>
                    <span class="shrink-0 text-xs tabular-nums text-slate-400 dark:text-slate-500">
                      {{ formatDate(row.date) }}
                    </span>
                  </span>
                </li>
              </ul>

              <!-- Lối đi tiếp: chỉ dựng khi thật sự dẫn tới đâu đó -->
              <div v-if="seeAllFor(item) || createFor(item)" class="mt-1.5 flex flex-wrap gap-3 pl-1.5">
                <button
                  v-if="seeAllFor(item)"
                  type="button"
                  data-testid="conn-see-all"
                  :aria-label="`Xem tất cả ${viLabel(item)} của hồ sơ này`"
                  class="rounded text-xs font-medium text-sky-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 dark:text-sky-300"
                  @click="openAll(item)"
                >
                  Xem tất cả
                </button>
                <button
                  v-if="createFor(item)"
                  type="button"
                  data-testid="conn-create"
                  :aria-label="`${createLabel(item)} cho hồ sơ này`"
                  class="rounded text-xs font-medium text-emerald-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 dark:text-emerald-300"
                  @click="openCreate(item)"
                >
                  {{ createLabel(item) }}
                </button>
              </div>
            </li>
          </ul>

          <!-- Ô rỗng gộp MỘT dòng/nhóm: TEXT TĨNH tuyệt đối — 0 nút, 0 link, 0 toggle.
               Thà một dòng nêu tên đầy đủ bằng tiếng Việt còn hơn 16 khối chỉ nói "0",
               và còn hơn ẩn hẳn (ẩn hẳn thì mất phân biệt "chưa có" vs "chưa tải"). -->
          <p
            v-if="emptySummary(group)"
            data-testid="conn-empty-summary"
            class="mt-2 text-xs text-slate-500 dark:text-slate-400"
          >
            {{ emptySummary(group) }}
          </p>

          <!-- «Tạo từ ngữ cảnh cha» cho ô 0 bản ghi (AC-CR-105) — khối SIBLING, NGOÀI thẻ
               `<p>` ở trên: câu «Chưa có: …» phải giữ nguyên 0 nút / 0 link (D-CR93-4 vẫn
               đúng với DÒNG GỘP), còn lối tạo thì không được mất. Ô nào không qua đủ 3 lớp
               gate (`createFor`) thì CHỈ được nêu tên trong câu — không chip nào mọc ra. -->
          <div
            v-if="emptyChips(group).length"
            data-testid="conn-empty-actions"
            class="mt-1.5 flex flex-wrap gap-2"
          >
            <button
              v-for="item in emptyChips(group)"
              :key="`create-${item.doctype}`"
              type="button"
              data-testid="conn-create"
              :aria-label="`${createLabel(item)} cho hồ sơ này`"
              class="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 hover:bg-emerald-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 dark:border-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200 dark:hover:bg-emerald-900"
              @click="openCreate(item)"
            >
              <!-- Dấu '+' là trang trí: để screen-reader đọc "cộng" trước mỗi nhãn là rác,
                   và nếu nó vào chuỗi nhìn thấy thì `aria-label` không còn CHỨA nhãn ấy
                   (vi phạm WCAG 2.5.3 label-in-name). -->
              <span aria-hidden="true">+</span> {{ createLabel(item) }}
            </button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
