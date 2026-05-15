<script setup lang="ts">
// MobileListWrapper — switches between table (sm+) and card list (< sm).
// Usage:
//   <MobileListWrapper>
//     <template #desktop>  <table>…</table>  </template>
//     <template #mobile>   <div v-for="…" class="mobile-card">…</div>  </template>
//   </MobileListWrapper>
defineProps<{ wrapperClass?: string }>()
</script>

<template>
  <!-- Desktop: table with horizontal scroll -->
  <div class="hidden sm:block table-wrapper" :class="wrapperClass">
    <slot name="desktop" />
  </div>

  <!-- Mobile: card stack -->
  <div class="sm:hidden mobile-card-list">
    <slot name="mobile" />
  </div>
</template>
