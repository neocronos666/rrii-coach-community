<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { inventoryApi, type Schema } from "~/features/inventory/api";
import { productApi } from "~/features/products/api";
import StockSummary from "~/features/inventory/StockSummary.vue";
import { usePending } from "~/features/shared/usePending";
import PendingStatus from "~/features/shared/PendingStatus.vue";
import {
  provideDraftGuard,
  useDraftGuard,
} from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
import { inventoryMessages as i, movementLabels } from "~/i18n/inventory";
import { testPrintMessages as t } from "~/i18n/test-prints";
definePageMeta({ key: (route) => route.path });
const id = String(useRoute().params.id),
  base = useRuntimeConfig().public.apiBaseUrl,
  api = inventoryApi(base);
const query = useQuery({
  queryKey: ["inventory-variant", id],
  retry: false,
  queryFn: async () => {
    const [variant, stock, movements] = await Promise.all([
      productApi(base).variant(id),
      api.stock(id),
      api.stockMovements(id),
    ]);
    return { variant, stock, movements };
  },
});
const body = ref<Omit<Schema["StockMovementCreate"], "request_id">>({
    movement_type: "adjustment_in",
    quantity: "",
    reason: "",
  }),
  confirmed = ref(false);
const registry = provideDraftGuard(i.unsaved),
  markSaved = useDraftGuard("movement", () => body.value, registry);
const mutation = usePending<
  Schema["StockMovementCreate"],
  Schema["StockMovementRead"]
>(`move:${id}`, (payload) => api.move(id, payload), "inventory");
async function save() {
  if (!mutation.pending.value && !confirmed.value) return;
  if (await mutation.run(body.value)) {
    body.value.quantity = "";
    body.value.reason = "";
    confirmed.value = false;
    markSaved();
    await query.refetch();
  }
}
useHead(() => ({
  title: `${query.data.value?.variant.name || i.products} · RRII-Coach`,
}));
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton to="/inventory" color="neutral" variant="soft">{{
      i.title
    }}</UButton>
    <h1>{{ query.data.value?.variant.name || i.products }}</h1>
    <p v-if="query.isPending.value" role="status">{{ t.loading }}</p>
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <UButton color="neutral" variant="soft" @click="query.refetch()">{{
      i.refresh
    }}</UButton
    ><template v-if="query.data.value"
      ><UButton
        :to="`/products/${query.data.value.variant.product_id}`"
        color="neutral"
        variant="soft"
        >Producto</UButton
      ><StockSummary :stock="query.data.value.stock" /><PendingStatus
        :pending="!!mutation.pending.value"
        :busy="mutation.busy.value"
        :error="mutation.error.value"
        :persistent="mutation.persistent.value"
        :invalid="mutation.invalid.value"
        @retry="save"
        @clear="mutation.clearInvalid"
      />
      <form class="asset-panel asset-form" @submit.prevent="save">
        <h2>{{ i.move }}</h2>
        <p>{{ i.movementHelp }}</p>
        <fieldset
          :disabled="
            !mutation.ready.value ||
            mutation.busy.value ||
            !!mutation.pending.value ||
            mutation.invalid.value
          "
        >
          <label
            >{{ i.movement
            }}<select v-model="body.movement_type">
              <option value="purchase">{{ movementLabels.purchase }}</option>
              <option value="adjustment_in">
                {{ movementLabels.adjustment_in }}
              </option>
              <option value="adjustment_out">
                {{ movementLabels.adjustment_out }}
              </option>
            </select></label
          ><label
            >{{ i.quantity
            }}<input
              v-model="body.quantity"
              inputmode="decimal"
              required /></label
          ><label
            >{{ i.reason
            }}<textarea
              v-model="body.reason"
              required
              maxlength="2000"
            /></label
          ><label class="catalog-check"
            ><input v-model="confirmed" type="checkbox" required />{{
              i.moveConfirm
            }}</label
          ><UButton type="submit">{{ i.move }}</UButton>
        </fieldset>
      </form>
      <section class="asset-panel">
        <h2>{{ i.movements }}</h2>
        <p v-if="!query.data.value.movements.length">{{ i.empty }}</p>
        <ul>
          <li v-for="row in query.data.value.movements" :key="row.id">
            {{ movementLabels[row.movement_type] || row.movement_type }} ·
            {{ row.quantity }} {{ row.unit }} ·
            {{ new Date(row.occurred_at).toLocaleString("es-AR") }} ·
            {{ row.reason
            }}<NuxtLink
              v-if="row.allocation_id"
              :to="`/inventory/allocations/${row.allocation_id}`"
            >
              · {{ i.allocation }}</NuxtLink
            ><NuxtLink
              v-if="row.test_print_id"
              :to="`/test-prints/${row.test_print_id}`"
            >
              · Prueba de receta</NuxtLink
            >
          </li>
        </ul>
      </section></template
    >
  </div>
</template>
