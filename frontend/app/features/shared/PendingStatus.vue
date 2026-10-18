<script setup lang="ts">
import { requestMessages as q } from "~/i18n/requests";
defineProps<{
  pending: boolean;
  busy: boolean;
  error: string;
  persistent: boolean;
  invalid: boolean;
}>();
defineEmits<{ retry: []; clear: [] }>();
</script>
<template>
  <div class="asset-form">
    <p v-if="error" role="alert">{{ error }}</p>
    <template v-if="pending"
      ><p role="status">{{ q.pending }}</p>
      <UButton :disabled="busy" @click="$emit('retry')">{{
        q.retryPending
      }}</UButton></template
    >
    <p v-if="!persistent" role="alert">{{ q.storageUnavailable }}</p>
    <template v-if="invalid"
      ><p role="alert">{{ q.invalidPending }}</p>
      <UButton color="neutral" variant="soft" @click="$emit('clear')">{{
        q.clearPending
      }}</UButton></template
    >
  </div>
</template>
