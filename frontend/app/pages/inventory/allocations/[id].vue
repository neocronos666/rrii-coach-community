<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { inventoryApi, type Schema } from "~/features/inventory/api";
import ReferenceLabel from "~/features/test-prints/components/ReferenceLabel.vue";
import StockSummary from "~/features/inventory/StockSummary.vue";
import { usePending } from "~/features/shared/usePending";
import PendingStatus from "~/features/shared/PendingStatus.vue";
import {
  provideDraftGuard,
  useDraftGuard,
} from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
import { inventoryMessages as i } from "~/i18n/inventory";
import { testPrintMessages as t } from "~/i18n/test-prints";
definePageMeta({ key: (route) => route.path });
const id = String(useRoute().params.id),
  api = inventoryApi(useRuntimeConfig().public.apiBaseUrl);
const query = useQuery({
  queryKey: ["inventory-allocation", id],
  retry: false,
  queryFn: async () => {
    const allocation = await api.allocation(id);
    const [stock, movements] = await Promise.all([
      api.stock(allocation.variant_id),
      api.stockMovements(allocation.variant_id),
    ]);
    return {
      allocation,
      stock,
      deliveries: movements.filter(
        (row) => row.allocation_id === id && row.movement_type === "delivery",
      ),
    };
  },
});
const quantity = ref(""),
  deliveryConfirmed = ref(false),
  releaseConfirmed = ref(false),
  saved = ref(false);
const registry = provideDraftGuard(i.unsaved),
  markSaved = useDraftGuard("delivery", () => quantity.value, registry);
const delivery = usePending<
  Schema["AllocationDelivery"],
  Schema["StockMovementRead"]
>(`deliver:${id}`, (body) => api.deliver(id, body), "inventory");
const release = usePending<{ request_id: string }, Schema["AllocationRead"]>(
  `release:${id}`,
  () => api.release(id),
  "inventory",
);
const locked = computed(
  () =>
    !delivery.ready.value ||
    !release.ready.value ||
    delivery.busy.value ||
    release.busy.value ||
    !!delivery.pending.value ||
    !!release.pending.value ||
    delivery.invalid.value ||
    release.invalid.value,
);
async function deliver() {
  if (release.pending.value || release.busy.value) return;
  if (!delivery.pending.value && !deliveryConfirmed.value) return;
  if (await delivery.run({ quantity: quantity.value })) {
    quantity.value = "";
    deliveryConfirmed.value = false;
    markSaved();
    saved.value = true;
    await query.refetch();
  }
}
async function free() {
  if (delivery.pending.value || delivery.busy.value) return;
  if (!release.pending.value && !releaseConfirmed.value) return;
  if (await release.run({})) {
    releaseConfirmed.value = false;
    saved.value = true;
    await query.refetch();
  }
}
useHead({ title: `${i.allocation} · RRII-Coach` });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton to="/inventory/allocations" color="neutral" variant="soft">{{
      i.allocations
    }}</UButton>
    <h1>{{ i.allocation }}</h1>
    <p v-if="query.isPending.value" role="status">{{ t.loading }}</p>
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <UButton color="neutral" variant="soft" @click="query.refetch()">{{
      i.refresh
    }}</UButton>
    <p v-if="saved" role="status">{{ i.saved }}</p>
    <template v-if="query.data.value"
      ><section class="asset-panel">
        <p>
          <ReferenceLabel
            :id="query.data.value.allocation.variant_id"
            kind="variant"
          />
        </p>
        <p>
          {{ i.initial }}: {{ query.data.value.allocation.initial_quantity }}
          {{ query.data.value.allocation.unit }}
        </p>
        <p data-testid="allocation-pending">
          {{ i.pending }}: {{ query.data.value.allocation.quantity }}
          {{ query.data.value.allocation.unit }}
        </p>
        <UButton
          :to="`/inventory/variants/${query.data.value.allocation.variant_id}`"
          color="neutral"
          variant="soft"
          >{{ i.stockLink }}</UButton
        ><UButton
          v-if="query.data.value.allocation.order_id"
          :to="`/orders/${query.data.value.allocation.order_id}`"
          color="neutral"
          variant="soft"
          >{{ i.origin }}</UButton
        >
        <p v-else>
          Componente: {{ query.data.value.allocation.project_component_id }}
        </p>
      </section>
      <StockSummary :stock="query.data.value.stock" />
      <section class="asset-panel asset-form">
        <h2>{{ i.deliver }}</h2>
        <p>{{ i.deliverHelp }}</p>
        <PendingStatus
          :pending="!!delivery.pending.value"
          :busy="delivery.busy.value"
          :error="delivery.error.value"
          :persistent="delivery.persistent.value"
          :invalid="delivery.invalid.value"
          @retry="deliver"
          @clear="delivery.clearInvalid"
        />
        <form class="asset-form" @submit.prevent="deliver">
          <fieldset :disabled="locked">
            <label
              >{{ i.deliveryQuantity
              }}<input v-model="quantity" inputmode="decimal" required /></label
            ><label class="catalog-check"
              ><input v-model="deliveryConfirmed" type="checkbox" required />{{
                i.deliverConfirm
              }}</label
            ><UButton type="submit">{{ i.deliver }}</UButton>
          </fieldset>
        </form>
      </section>
      <section class="asset-panel asset-form">
        <h2>{{ i.release }}</h2>
        <p>{{ i.releaseHelp }}</p>
        <PendingStatus
          :pending="!!release.pending.value"
          :busy="release.busy.value"
          :error="release.error.value"
          :persistent="release.persistent.value"
          :invalid="release.invalid.value"
          @retry="free"
          @clear="release.clearInvalid"
        />
        <form @submit.prevent="free">
          <fieldset :disabled="locked">
            <label class="catalog-check"
              ><input v-model="releaseConfirmed" type="checkbox" required />{{
                i.releaseConfirm
              }}</label
            ><UButton type="submit" color="neutral" variant="soft">{{
              i.release
            }}</UButton>
          </fieldset>
        </form>
      </section>
      <section class="asset-panel">
        <h2>{{ i.deliveries }}</h2>
        <p v-if="!query.data.value.deliveries.length">{{ i.empty }}</p>
        <ul>
          <li
            v-for="row in query.data.value.deliveries"
            :key="row.id"
            data-testid="delivery-row"
          >
            {{ row.quantity }} {{ row.unit }} ·
            {{ new Date(row.occurred_at).toLocaleString("es-AR") }}
          </li>
        </ul>
      </section></template
    >
  </div>
</template>
