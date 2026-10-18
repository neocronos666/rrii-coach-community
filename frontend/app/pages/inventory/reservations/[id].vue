<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { inventoryApi } from "~/features/inventory/api";
import { productionApi } from "~/features/production/api";
import StockSummary from "~/features/inventory/StockSummary.vue";
import WriteStatus from "~/features/inventory/WriteStatus.vue";
import { useRecordedWrite } from "~/features/inventory/useRecordedWrite";
import {
  provideDraftGuard,
  useDraftGuard,
} from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
import { inventoryMessages as i } from "~/i18n/inventory";
import { testPrintMessages as t } from "~/i18n/test-prints";
definePageMeta({ key: (route) => route.path });
const id = String(useRoute().params.id),
  base = useRuntimeConfig().public.apiBaseUrl,
  api = inventoryApi(base),
  supply = ref(""),
  quantity = ref(""),
  confirmed = ref(false);
const query = useQuery({
  queryKey: ["inventory-reservations", id],
  retry: false,
  queryFn: async () => {
    const [task, supplies, reservations] = await Promise.all([
      productionApi(base).task(id),
      api.supplies(),
      api.reservations(id),
    ]);
    return { task, supplies, reservations };
  },
});
const availability = useQuery({
  queryKey: computed(() => ["inventory-availability", supply.value]),
  queryFn: () => api.availability(supply.value),
  enabled: computed(() => !!supply.value),
  retry: false,
});
async function refresh() {
  const result = await query.refetch();
  if (supply.value) await availability.refetch();
  return !result.isError;
}
const state = useRecordedWrite(`reservation:${id}`, refresh);
const registry = provideDraftGuard(i.unsaved),
  markSaved = useDraftGuard(
    "reservation",
    () => [supply.value, quantity.value],
    registry,
  );
async function save() {
  if (!confirmed.value) return;
  const result = await state.run(
    `${i.reserve}: ${query.data.value?.supplies.find((row) => row.id === supply.value)?.name || supply.value} · ${quantity.value}`,
    () => api.reserve(id, supply.value, { quantity: quantity.value }),
  );
  if (result) {
    quantity.value = "";
    confirmed.value = false;
    markSaved();
  }
}
useHead({ title: `${i.reservations} · RRII-Coach` });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton :to="`/production/tasks/${id}`" color="neutral" variant="soft">{{
      i.task
    }}</UButton>
    <h1>{{ i.reservations }}</h1>
    <p v-if="query.isPending.value" role="status">{{ t.loading }}</p>
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <UButton color="neutral" variant="soft" @click="refresh">{{
      i.refresh
    }}</UButton
    ><template v-if="query.data.value"
      ><h2>
        {{ query.data.value.task.code }} · {{ query.data.value.task.title }}
      </h2>
      <WriteStatus :state="state" />
      <form class="asset-panel asset-form" @submit.prevent="save">
        <p>{{ i.reserveHelp }}</p>
        <fieldset :disabled="state.locked.value">
          <label
            >{{ i.supply
            }}<select v-model="supply" required>
              <option value="">{{ t.choose }}</option>
              <option
                v-for="row in query.data.value.supplies"
                :key="row.id"
                :value="row.id"
              >
                {{ row.name }} · {{ row.base_unit }}
              </option>
            </select></label
          ><label
            >{{ i.quantity
            }}<input v-model="quantity" inputmode="decimal" required /></label
          ><label class="catalog-check"
            ><input v-model="confirmed" type="checkbox" required />{{
              i.reserveConfirm
            }}</label
          ><UButton type="submit">{{ i.reserve }}</UButton>
        </fieldset>
      </form>
      <p v-if="availability.error.value" role="alert">
        {{ errorMessage(availability.error.value) }}
      </p>
      <StockSummary
        v-if="availability.data.value"
        :stock="availability.data.value"
      />
      <section class="asset-panel">
        <h2>{{ i.reservations }}</h2>
        <p v-if="!query.data.value.reservations.length">{{ i.empty }}</p>
        <ul>
          <li
            v-for="row in query.data.value.reservations"
            :key="row.id"
            data-testid="reservation-row"
          >
            <NuxtLink :to="`/inventory/supplies/${row.supply_id}`">{{
              query.data.value.supplies.find(
                (item) => item.id === row.supply_id,
              )?.name || row.supply_id
            }}</NuxtLink>
            · {{ row.quantity }} {{ row.unit }}
          </li>
        </ul>
      </section></template
    >
  </div>
</template>
