<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import SupplyEditor from "~/features/inventory/SupplyEditor.vue";
import { inventoryApi } from "~/features/inventory/api";
import { provideDraftGuard } from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
import { inventoryMessages as i } from "~/i18n/inventory";
const api = inventoryApi(useRuntimeConfig().public.apiBaseUrl);
const query = useQuery({
  queryKey: ["inventory-supplies-review"],
  queryFn: () => api.supplies(),
  retry: false,
});
provideDraftGuard(i.unsaved);
async function refresh() {
  return !(await query.refetch()).isError;
}
useHead({ title: `${i.newSupply} · RRII-Coach` });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton to="/inventory" color="neutral" variant="soft">{{
      i.title
    }}</UButton>
    <h1>{{ i.newSupply }}</h1>
    <SupplyEditor
      :refresh="refresh"
      @saved="(id) => navigateTo(`/inventory/supplies/${id}`)"
    />
    <section class="asset-panel">
      <h2>{{ i.supplies }}</h2>
      <p v-if="query.error.value" role="alert">
        {{ errorMessage(query.error.value) }}
      </p>
      <ul>
        <li v-for="row in query.data.value" :key="row.id">
          <NuxtLink :to="`/inventory/supplies/${row.id}`"
            >{{ row.name }} · {{ row.sku }} · {{ row.base_unit }}</NuxtLink
          >
        </li>
      </ul>
    </section>
  </div>
</template>
