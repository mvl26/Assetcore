<script setup lang="ts">
withDefaults(
  defineProps<{
    rows?: number
    cols?: number
  }>(),
  {
    rows: 5,
    cols: 4,
  },
)
</script>

<template>
  <div class="animate-pulse" role="status" aria-label="Đang tải...">
    <div
      v-for="row in rows"
      :key="row"
      class="flex gap-4 py-3 border-b border-gray-100"
    >
      <div
        v-for="col in cols"
        :key="col"
        class="bg-gray-200 rounded h-4 flex-1"
      />
    </div>
  </div>
</template>
