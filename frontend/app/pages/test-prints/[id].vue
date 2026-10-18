<script setup lang="ts">
import ReferenceLabel from "~/features/test-prints/components/ReferenceLabel.vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { testPrintApi, type Schema } from "~/features/test-prints/api";
import {
  snapshotName,
  omittedKeys,
  configurationSnapshot,
  orderedSteps,
} from "~/features/test-prints/snapshots";
import { usePending } from "~/features/shared/usePending";
import PendingStatus from "~/features/shared/PendingStatus.vue";
import StepCard from "~/features/test-prints/components/StepCard.vue";
import {
  provideDraftGuard,
  useDraftGuard,
} from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
import { testPrintMessages as t, testPrintStates } from "~/i18n/test-prints";
definePageMeta({ key: (route) => route.path });
const id = String(useRoute().params.id),
  api = testPrintApi(useRuntimeConfig().public.apiBaseUrl),
  cache = useQueryClient();
const query = useQuery({
  queryKey: ["test-print", id],
  queryFn: () => api.get(id),
  retry: false,
});
const configuration = computed(() =>
  configurationSnapshot.safeParse(query.data.value?.snapshot.configuration),
);
const movement = useQuery({
  queryKey: computed(() => [
    "test-promotion",
    id,
    query.data.value?.promotion_movement_id,
  ]),
  enabled: computed(() => !!query.data.value?.promotion_movement_id),
  retry: false,
  queryFn: async () =>
    (await api.stockMovements(query.data.value!.variant_id)).find(
      (row) => row.id === query.data.value!.promotion_movement_id,
    ) ?? null,
});
const units = computed(() => {
  const value = query.data.value?.snapshot.supply_units;
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
});
const registry = provideDraftGuard(t.unsaved);
const quantity = ref(""),
  promoteConfirmed = ref(false),
  cancelConfirmed = ref(false),
  saved = ref(false);
const markSaved = useDraftGuard(
  "test-promotion",
  () => quantity.value,
  registry,
);
const promotion = usePending<
  Schema["TestPrintPromotion"],
  Schema["StockMovementRead"]
>(`promote:${id}`, (body) => api.promote(id, body), "test-print");
const cancellation = usePending<
  { request_id: string },
  Schema["TestPrintRead"]
>(`cancel:${id}`, () => api.cancel(id), "test-print");
async function refresh() {
  await Promise.all([
    cache.invalidateQueries({ queryKey: ["test-print", id] }),
    cache.invalidateQueries({ queryKey: ["test-runs", id] }),
    cache.invalidateQueries({ queryKey: ["test-prints"] }),
  ]);
}
async function promote() {
  if (!promotion.pending.value && !promoteConfirmed.value) return;
  const result = await promotion.run({ quantity: quantity.value });
  if (result) {
    markSaved();
    saved.value = true;
    await refresh();
  }
}
async function cancel() {
  if (!cancellation.pending.value && !cancelConfirmed.value) return;
  if (await cancellation.run({})) {
    saved.value = true;
    await refresh();
  }
}
useHead(() => ({
  title: `${query.data.value ? snapshotName(query.data.value.snapshot) : t.title} · RRII-Coach`,
}));
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton
      :to="
        query.data.value
          ? `/test-prints?variant=${query.data.value.variant_id}`
          : '/test-prints'
      "
      color="neutral"
      variant="soft"
      >{{ t.back }}</UButton
    >
    <h1>{{ t.title }}</h1>
    <p v-if="query.isPending.value" role="status">{{ t.loading }}</p>
    <div v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </div>
    <UButton color="neutral" variant="soft" @click="refresh">{{
      t.refresh
    }}</UButton>
    <p v-if="saved" role="status">{{ t.saved }}</p>
    <template v-if="query.data.value"
      ><section class="asset-panel asset-form">
        <h2>{{ snapshotName(query.data.value.snapshot) }}</h2>
        <p>{{ t.historical }}</p>
        <p data-testid="test-status">
          {{
            testPrintStates[query.data.value.status] || query.data.value.status
          }}
        </p>
        <p>
          {{ t.variant }}:
          <ReferenceLabel :id="query.data.value.variant_id" kind="variant" />
        </p>
        <p>
          {{ t.target }}: {{ query.data.value.target_quantity }}
          {{ query.data.value.unit }}
        </p>
        <p>
          {{ t.omitted }}:
          {{ omittedKeys(query.data.value.snapshot).join(", ") || t.none }}
        </p>
      </section>
      <details v-if="configuration.success" class="asset-panel asset-form">
        <summary>{{ t.configuration }}</summary>
        <article
          v-for="selection in configuration.data.selections"
          :key="selection.definition_id"
        >
          <h3>{{ t.definition }}: {{ selection.definition_id }}</h3>
          <p v-for="value in selection.values" :key="value.value_id">
            {{ t.value }}: {{ value.value_id }} · {{ t.selectedQuantity }}:
            {{ value.quantity
            }}<span v-if="value.revision_id">
              · {{ t.revision }}: {{ value.revision_id }}</span
            >
          </p>
        </article>
      </details>
      <StepCard
        v-for="step in orderedSteps(query.data.value.steps)"
        :key="step.id"
        :api="api"
        :id="id"
        :step="step"
        :status="query.data.value.status"
        :units="units"
        @saved="refresh"
      />
      <section class="asset-panel asset-form" :aria-label="t.promotion">
        <h2>{{ t.promotion }}</h2>
        <p>{{ t.promotionHelp }}</p>
        <p>
          {{ t.promotable }}: {{ query.data.value.promotable_quantity }}
          {{ query.data.value.unit }}
        </p>
        <p v-if="query.data.value.promotion_movement_id" role="status">
          {{ t.promoted }} · {{ t.movement }}:
          {{ query.data.value.promotion_movement_id }}
        </p>
        <p v-if="movement.data.value" data-testid="promoted-quantity">
          {{ t.promotedQuantity }}: {{ movement.data.value.quantity }}
          {{ movement.data.value.unit }}
        </p>
        <div v-if="movement.error.value" role="alert">
          {{ errorMessage(movement.error.value)
          }}<UButton @click="movement.refetch()">{{ t.retry }}</UButton>
        </div>
        <PendingStatus
          :pending="!!promotion.pending.value"
          :busy="promotion.busy.value"
          :error="promotion.error.value"
          :persistent="promotion.persistent.value"
          :invalid="promotion.invalid.value"
          @retry="promote"
          @clear="promotion.clearInvalid"
        />
        <form
          v-if="!query.data.value.promotion_movement_id"
          class="asset-form"
          @submit.prevent="promote"
        >
          <fieldset
            :disabled="
              query.data.value.status !== 'completed' ||
              !promotion.ready.value ||
              promotion.busy.value ||
              !!promotion.pending.value ||
              promotion.invalid.value
            "
          >
            <label
              >{{ t.promotionQuantity
              }}<input v-model="quantity" inputmode="decimal" required /></label
            ><label class="catalog-check"
              ><input v-model="promoteConfirmed" type="checkbox" required />{{
                t.promotionConfirm
              }}</label
            ><UButton type="submit">{{ t.promote }}</UButton>
          </fieldset>
        </form>
      </section>
      <section class="asset-panel asset-form" :aria-label="t.cancel">
        <h2>{{ t.cancel }}</h2>
        <p>{{ t.cancelHelp }}</p>
        <PendingStatus
          :pending="!!cancellation.pending.value"
          :busy="cancellation.busy.value"
          :error="cancellation.error.value"
          :persistent="cancellation.persistent.value"
          :invalid="cancellation.invalid.value"
          @retry="cancel"
          @clear="cancellation.clearInvalid"
        />
        <form
          v-if="query.data.value.status === 'open'"
          @submit.prevent="cancel"
        >
          <fieldset
            :disabled="
              !cancellation.ready.value ||
              cancellation.busy.value ||
              !!cancellation.pending.value ||
              cancellation.invalid.value
            "
          >
            <label class="catalog-check"
              ><input v-model="cancelConfirmed" type="checkbox" required />{{
                t.cancelConfirm
              }}</label
            ><UButton type="submit" color="neutral" variant="soft">{{
              t.cancel
            }}</UButton>
          </fieldset>
        </form>
      </section></template
    >
  </div>
</template>
