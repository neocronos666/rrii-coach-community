<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { testPrintApi } from "~/features/test-prints/api";
import { snapshotName } from "~/features/test-prints/snapshots";
import { errorMessage } from "~/features/shared/http";
import { testPrintMessages as t, testPrintStates } from "~/i18n/test-prints";
definePageMeta({ key: (route) => route.fullPath });
const variant = String(useRoute().query.variant || ""),
  offset = ref(0),
  api = testPrintApi(useRuntimeConfig().public.apiBaseUrl);
const query = useQuery({
  queryKey: computed(() => ["test-prints", variant, offset.value]),
  queryFn: () => api.list(offset.value, variant),
  retry: false,
});
useHead({ title: `${t.title} · RRII-Coach` });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <h1>{{ t.title }}</h1>
    <p>{{ t.description }}</p>
    <div class="asset-actions">
      <UButton to="/products" color="neutral" variant="soft">{{
        t.products
      }}</UButton
      ><UButton v-if="variant" :to="`/test-prints/new?variant=${variant}`">{{
        t.new
      }}</UButton>
    </div>
    <p v-if="query.isPending.value" role="status">{{ t.loading }}</p>
    <div v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value)
      }}<UButton @click="query.refetch()">{{ t.retry }}</UButton>
    </div>
    <template v-if="query.data.value"
      ><p v-if="!query.data.value.length">{{ t.empty }}</p>
      <ul class="asset-grid">
        <li
          v-for="row in query.data.value.slice(0, 24)"
          :key="row.id"
          class="asset-panel"
        >
          <h2>
            <NuxtLink :to="`/test-prints/${row.id}`">{{
              snapshotName(row.snapshot) || row.id
            }}</NuxtLink>
          </h2>
          <p>
            {{ testPrintStates[row.status] || row.status }} ·
            {{ row.target_quantity }} {{ row.unit }}
          </p>
          <time :datetime="row.created_at">{{
            new Date(row.created_at).toLocaleString("es-AR")
          }}</time>
        </li>
      </ul>
      <nav class="asset-actions" :aria-label="t.title">
        <UButton
          color="neutral"
          variant="soft"
          :disabled="offset === 0"
          @click="offset = Math.max(0, offset - 24)"
          >{{ t.previous }}</UButton
        ><UButton
          color="neutral"
          variant="soft"
          :disabled="query.data.value.length <= 24"
          @click="offset += 24"
          >{{ t.next }}</UButton
        >
      </nav></template
    >
  </div>
</template>
