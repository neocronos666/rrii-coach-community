<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { inventoryApi, type Schema } from "~/features/inventory/api";
import VariantPicker from "~/features/inventory/VariantPicker.vue";
import { errorMessage } from "~/features/shared/http";
import { inventoryMessages as i, supplyCategories } from "~/i18n/inventory";
import { testPrintMessages as t } from "~/i18n/test-prints";
const api = inventoryApi(useRuntimeConfig().public.apiBaseUrl),
  active = ref<boolean | undefined>(undefined),
  category = ref<Schema["SupplyCategory"] | undefined>(),
  variant = ref("");
const query = useQuery({
  queryKey: computed(() => [
    "inventory-supplies",
    active.value,
    category.value,
  ]),
  queryFn: () => api.supplies(active.value, category.value),
  retry: false,
});
useHead({ title: `${i.title} · RRII-Coach` });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <h1>{{ i.title }}</h1>
    <nav class="asset-actions" aria-label="Inventario">
      <UButton to="/inventory/supplies/new">{{ i.newSupply }}</UButton
      ><UButton to="/inventory/allocations" color="neutral" variant="soft">{{
        i.allocations
      }}</UButton>
    </nav>
    <section class="asset-panel asset-form">
      <h2>{{ i.products }}</h2>
      <VariantPicker v-model="variant" /><UButton
        v-if="variant"
        :to="`/inventory/variants/${variant}`"
        >{{ i.stockLink }}</UButton
      >
    </section>
    <h2>{{ i.supplies }}</h2>
    <label
      >{{ i.active
      }}<select v-model="active">
        <option :value="undefined">{{ i.all }}</option>
        <option :value="true">Activos</option>
        <option :value="false">Inactivos</option>
      </select></label
    ><label
      >{{ i.category
      }}<select v-model="category">
        <option :value="undefined">{{ i.all }}</option>
        <option
          v-for="(label, value) in supplyCategories"
          :key="value"
          :value="value"
        >
          {{ label }}
        </option>
      </select></label
    >
    <p v-if="query.isPending.value" role="status">{{ t.loading }}</p>
    <div v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value)
      }}<UButton @click="query.refetch()">{{ t.retry }}</UButton>
    </div>
    <p v-if="query.data.value?.length === 0">{{ i.empty }}</p>
    <ul class="asset-grid">
      <li v-for="row in query.data.value" :key="row.id" class="asset-panel">
        <h3>
          <NuxtLink :to="`/inventory/supplies/${row.id}`">{{
            row.name
          }}</NuxtLink>
        </h3>
        <p>
          {{ row.sku }} · {{ supplyCategories[row.category] }} ·
          {{ row.base_unit }} · {{ row.active ? "Activo" : "Inactivo" }}
        </p>
      </li>
    </ul>
  </div>
</template>
