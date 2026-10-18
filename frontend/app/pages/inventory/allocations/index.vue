<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { inventoryApi, type Schema } from "~/features/inventory/api";
import { commercialApi } from "~/features/commercial/api";
import VariantPicker from "~/features/inventory/VariantPicker.vue";
import ReferenceLabel from "~/features/test-prints/components/ReferenceLabel.vue";
import { usePending } from "~/features/shared/usePending";
import PendingStatus from "~/features/shared/PendingStatus.vue";
import {
  provideDraftGuard,
  useDraftGuard,
} from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
import { inventoryMessages as i } from "~/i18n/inventory";
import { testPrintMessages as t } from "~/i18n/test-prints";
definePageMeta({ key: (route) => route.fullPath });
const route = useRoute(),
  value = (key: string) =>
    typeof route.query[key] === "string" ? (route.query[key] as string) : "";
const order = value("order"),
  component = value("component"),
  project = value("project"),
  valid = !!(
    (order && !component && !project) ||
    (component && project && !order)
  );
const base = useRuntimeConfig().public.apiBaseUrl,
  api = inventoryApi(base),
  commercial = commercialApi(base);
const query = useQuery({
  queryKey: ["inventory-allocations", order, component],
  queryFn: () => api.allocations(order || undefined, component || undefined),
  retry: false,
});
const origin = useQuery({
  queryKey: ["inventory-origin", order, component, project],
  enabled: valid,
  retry: false,
  queryFn: async () => {
    if (order) {
      const row = await commercial.order(order);
      return {
        title: `${row.code} · ${row.title}`,
        url: `/orders/${row.id}`,
        status: row.status,
      };
    }
    const row = await commercial.project(project);
    const part = row.components.find((entry) => entry.id === component);
    if (!part) throw new Error(i.selectOrigin);
    return {
      title: `${row.code} · ${part.description}`,
      url: `/projects/${row.id}`,
      status: row.status,
    };
  },
});
const variant = ref(""),
  quantity = ref(""),
  confirmed = ref(false);
const registry = provideDraftGuard(i.unsaved),
  markSaved = useDraftGuard(
    "allocation",
    () => [variant.value, quantity.value],
    registry,
  );
const mutation = usePending<
  Schema["AllocationCreate"],
  Schema["AllocationResult"]
>(`allocate:${order}:${component}`, api.allocate, "inventory");
async function save() {
  if (
    !mutation.pending.value &&
    (!confirmed.value || !valid || origin.data.value?.status !== "pending")
  )
    return;
  const result = await mutation.run({
    variant_id: variant.value,
    quantity: quantity.value,
    ...(order ? { order_id: order } : { project_component_id: component }),
  });
  if (result) {
    markSaved();
    await navigateTo(`/inventory/allocations/${result.allocation.id}`);
  }
}
useHead({ title: `${i.allocations} · RRII-Coach` });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton to="/inventory" color="neutral" variant="soft">{{
      i.title
    }}</UButton>
    <h1>{{ i.allocations }}</h1>
    <p v-if="!valid">{{ i.selectOrigin }}</p>
    <p v-if="origin.error.value" role="alert">
      {{ errorMessage(origin.error.value) }}
    </p>
    <section v-if="origin.data.value" class="asset-panel">
      <h2>{{ origin.data.value.title }}</h2>
      <UButton :to="origin.data.value.url" color="neutral" variant="soft">{{
        i.origin
      }}</UButton>
      <p v-if="origin.data.value.status !== 'pending'">{{ i.cancelled }}</p>
    </section>
    <PendingStatus
      :pending="!!mutation.pending.value"
      :busy="mutation.busy.value"
      :error="mutation.error.value"
      :persistent="mutation.persistent.value"
      :invalid="mutation.invalid.value"
      @retry="save"
      @clear="mutation.clearInvalid"
    />
    <form
      v-if="origin.data.value?.status === 'pending'"
      class="asset-panel asset-form"
      @submit.prevent="save"
    >
      <h2>{{ i.allocate }}</h2>
      <p>{{ i.allocationHelp }}</p>
      <fieldset
        :disabled="
          !mutation.ready.value ||
          mutation.busy.value ||
          !!mutation.pending.value ||
          mutation.invalid.value
        "
      >
        <VariantPicker v-model="variant" /><label
          >{{ i.quantity
          }}<input v-model="quantity" inputmode="decimal" required /></label
        ><label class="catalog-check"
          ><input v-model="confirmed" type="checkbox" required />{{
            i.allocateConfirm
          }}</label
        ><UButton type="submit">{{ i.allocate }}</UButton>
      </fieldset>
    </form>
    <p v-if="query.isPending.value" role="status">{{ t.loading }}</p>
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <UButton
      color="neutral"
      variant="soft"
      @click="
        query.refetch();
        if (valid) origin.refetch();
      "
      >{{ i.refresh }}</UButton
    >
    <p v-if="query.data.value?.length === 0">{{ i.empty }}</p>
    <ul class="asset-grid">
      <li v-for="row in query.data.value" :key="row.id" class="asset-panel">
        <h2>
          <NuxtLink :to="`/inventory/allocations/${row.id}`"
            >{{ i.allocation }} · {{ row.id }}</NuxtLink
          >
        </h2>
        <p><ReferenceLabel :id="row.variant_id" kind="variant" /></p>
        <p>{{ i.pending }}: {{ row.quantity }} {{ row.unit }}</p>
        <p>
          {{ row.order_id ? "Pedido" : "Componente" }}:
          {{ row.order_id || row.project_component_id }}
        </p>
      </li>
    </ul>
  </div>
</template>
