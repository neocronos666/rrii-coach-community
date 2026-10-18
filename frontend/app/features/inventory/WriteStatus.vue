<script setup lang="ts">
import type { useRecordedWrite } from "./useRecordedWrite";
import { inventoryMessages as i } from "~/i18n/inventory";
const props = defineProps<{ state: ReturnType<typeof useRecordedWrite> }>();
const confirmed = ref(false);
watch(
  () => props.state.review.value,
  () => {
    confirmed.value = false;
  },
);
</script>
<template>
  <div class="asset-form">
    <p v-if="state.error.value" role="alert">{{ state.error.value }}</p>
    <p v-if="state.saved.value" role="status">{{ i.saved }}</p>
    <p v-if="!state.persistent.value" role="alert">{{ i.storage }}</p>
    <section
      v-if="!state.busy.value && (state.review.value || state.invalid.value)"
      class="asset-panel asset-form"
      aria-label="Revisar operación incierta"
    >
      <p role="alert">{{ state.invalid.value ? i.invalid : i.review }}</p>
      <p v-if="state.review.value">
        {{ i.uncertainSummary }}: {{ state.review.value.summary }} ·
        {{ new Date(state.review.value.createdAt).toLocaleString("es-AR") }}
      </p>
      <UButton color="neutral" variant="soft" @click="state.inspect">{{
        i.refresh
      }}</UButton>
      <label class="catalog-check"
        ><input
          v-model="confirmed"
          type="checkbox"
          :disabled="!state.reviewed.value"
        />{{ i.reviewConfirm }}</label
      >
      <UButton
        :disabled="!confirmed || !state.reviewed.value"
        @click="state.acknowledge"
        >{{ i.unlock }}</UButton
      >
    </section>
  </div>
</template>
