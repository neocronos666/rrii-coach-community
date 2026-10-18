<script setup lang="ts">
import { utcDateTime } from "~/features/inventory/values";
import ConsumptionSelector from "~/features/production-editor/ConsumptionSelector.vue";
import ReferenceLabel from "./ReferenceLabel.vue";
import { useQuery } from "@tanstack/vue-query";
import type { TestPrintApi, Schema } from "../api";
import type { StepSnapshot } from "../snapshots";
import { usePending } from "~/features/shared/usePending";
import PendingStatus from "~/features/shared/PendingStatus.vue";
import { useDraftGuard } from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
import {
  testPrintMessages as t,
  testPrintStates,
  failureReasons,
} from "~/i18n/test-prints";
const props = defineProps<{
  api: Pick<TestPrintApi, "close" | "supplies" | "products">;
  namespace?: string;
  closeHelp?: string;
  run: Schema["RunRead"];
  snapshot: StepSnapshot;
  units: Record<string, unknown>;
}>();
const emit = defineEmits<{ saved: [] }>();
const body = ref<Schema["RunClose"]>({
  good_quantity: "",
  failed_quantity: "0",
  failure_reason: null,
  actual_duration_seconds: null,
  notes: null,
  supply_consumptions: [],
  product_consumptions: [],
});
const supplies = ref(
  props.snapshot.supply_inputs.map((row) => ({
    id: row.supply_id,
    include: true,
    consumed: "",
    wasted: "0",
  })),
);
const products = ref(
  props.snapshot.product_inputs.map((row) => ({
    id: row.product_variant_id,
    source: row.source_step_key,
    include: true,
    consumed: "",
    wasted: "0",
  })),
);
const endedAt = ref("");
const confirmed = ref(false),
  expanded = ref(false);
const history = useQuery({
  queryKey: ["test-run-consumptions", props.run.id],
  queryFn: async () => {
    const [supplies, products] = await Promise.all([
      props.api.supplies(props.run.id),
      props.api.products(props.run.id),
    ]);
    return { supplies, products };
  },
  enabled: computed(() => expanded.value && props.run.status !== "running"),
  retry: false,
});
const markSaved = useDraftGuard(`test-run:${props.run.id}`, () => [
  body.value,
  endedAt.value,
  supplies.value,
  products.value,
]);
// El servidor identifica el cierre por run_id; el UUID local conserva el sobre de reintento.
const mutation = usePending<
  Schema["RunClose"] & { request_id: string },
  Schema["RunRead"]
>(
  `close:${props.run.id}`,
  ({ request_id: _, ...payload }) => props.api.close(props.run.id, payload),
  props.namespace ?? "test-print",
);
async function close() {
  if (!mutation.pending.value && !confirmed.value) return;
  let ended: string | undefined;
  try {
    ended =
      !mutation.pending.value && endedAt.value
        ? utcDateTime(endedAt.value)
        : undefined;
  } catch (failure) {
    mutation.error.value = errorMessage(failure);
    return;
  }
  const result = await mutation.run({
    ...(ended ? { ended_at: ended } : {}),
    ...body.value,
    supply_consumptions: supplies.value
      .filter((row) => row.include)
      .map((row) => ({
        supply_id: row.id,
        consumed: row.consumed,
        wasted: row.wasted,
      })),
    product_consumptions: products.value
      .filter((row) => row.include)
      .map((row) => ({
        variant_id: row.id,
        consumed: row.consumed,
        wasted: row.wasted,
      })),
  });
  if (result) {
    markSaved();
    emit("saved");
  }
}
const locked = computed(
  () =>
    !mutation.ready.value ||
    mutation.busy.value ||
    !!mutation.pending.value ||
    mutation.invalid.value,
);
</script>
<template>
  <article class="catalog-group asset-form" :aria-label="`${t.run} ${run.id}`">
    <h4>{{ t.run }} · {{ testPrintStates[run.status] || run.status }}</h4>
    <p>
      {{ t.started }}: {{ new Date(run.started_at).toLocaleString("es-AR") }}
    </p>
    <details>
      <summary>Parámetros guardados del intento</summary>
      <pre class="run-parameters">{{
        JSON.stringify(run.parameters, null, 2)
      }}</pre>
    </details>
    <p v-if="run.machine_id">{{ t.machine }}: {{ run.machine_id }}</p>
    <ul v-if="run.warnings.length">
      <li v-for="warning in run.warnings" :key="warning">{{ warning }}</li>
    </ul>
    <PendingStatus
      :pending="!!mutation.pending.value"
      :busy="mutation.busy.value"
      :error="mutation.error.value"
      :persistent="mutation.persistent.value"
      :invalid="mutation.invalid.value"
      @retry="close"
      @clear="mutation.clearInvalid"
    />
    <form
      v-if="run.status === 'running'"
      class="asset-form"
      @submit.prevent="close"
    >
      <p>{{ closeHelp ?? t.closeHelp }}</p>
      <fieldset :disabled="locked">
        <ConsumptionSelector
          @supply="
            (id) => {
              if (!supplies.some((row) => row.id === id))
                supplies.push({ id, include: true, consumed: '', wasted: '0' });
            }
          "
          @variant="
            (id) => {
              if (!products.some((row) => row.id === id))
                products.push({
                  id,
                  source: null,
                  include: true,
                  consumed: '',
                  wasted: '0',
                });
            }
          "
        />
        <label
          >Fin real (opcional)<input
            v-model="endedAt"
            type="datetime-local"
            step="1"
        /></label>
        <p>
          Vacío usa la hora del servidor. La fecha ingresada usa la zona horaria
          de este navegador.
        </p>
        <label
          >{{ t.good
          }}<input
            v-model="body.good_quantity"
            inputmode="decimal"
            required /></label
        ><label
          >{{ t.failed
          }}<input v-model="body.failed_quantity" inputmode="decimal" required
        /></label>
        <label
          >{{ t.failureReason
          }}<select v-model="body.failure_reason">
            <option :value="null">{{ t.none }}</option>
            <option
              v-for="(label, value) in failureReasons"
              :key="value"
              :value="value"
            >
              {{ label }}
            </option>
          </select></label
        >
        <label
          >{{ t.duration
          }}<input
            :value="body.actual_duration_seconds ?? ''"
            inputmode="decimal"
            @input="
              body.actual_duration_seconds =
                ($event.target as HTMLInputElement).value || null
            " /></label
        ><label>{{ t.notes }}<textarea v-model="body.notes" /></label>
        <section
          v-for="row in supplies"
          :key="row.id"
          class="catalog-group asset-form"
        >
          <h5>
            {{ t.materials }}: <ReferenceLabel :id="row.id" kind="supply" />
          </h5>
          <p>{{ t.unit }}: {{ units[row.id] ?? t.none }}</p>
          <label class="catalog-check"
            ><input v-model="row.include" type="checkbox" />{{
              t.include
            }}</label
          ><template v-if="row.include"
            ><label
              >{{ t.consumed
              }}<input
                v-model="row.consumed"
                inputmode="decimal"
                required /></label
            ><label
              >{{ t.wasted
              }}<input
                v-model="row.wasted"
                inputmode="decimal"
                required /></label
          ></template>
        </section>
        <section
          v-for="row in products"
          :key="row.id"
          class="catalog-group asset-form"
        >
          <h5>
            {{ t.components }}: <ReferenceLabel :id="row.id" kind="variant" />
          </h5>
          <p>{{ row.source ? `${t.internal}: ${row.source}` : t.external }}</p>
          <label class="catalog-check"
            ><input v-model="row.include" type="checkbox" />{{
              t.include
            }}</label
          ><template v-if="row.include"
            ><label
              >{{ t.consumed
              }}<input
                v-model="row.consumed"
                inputmode="decimal"
                required /></label
            ><label
              >{{ t.wasted
              }}<input
                v-model="row.wasted"
                inputmode="decimal"
                required /></label
          ></template>
        </section>
        <label class="catalog-check"
          ><input v-model="confirmed" type="checkbox" required />{{
            t.closeConfirm
          }}</label
        ><UButton type="submit">{{ t.close }}</UButton>
      </fieldset>
    </form>
    <template v-else
      ><p>
        {{ t.good }}: {{ run.good_quantity }} · {{ t.failed }}:
        {{ run.failed_quantity }} {{ run.unit }}
      </p>
      <p>
        {{ t.ended }}:
        {{
          run.ended_at ? new Date(run.ended_at).toLocaleString("es-AR") : t.none
        }}
      </p>
      <p>{{ t.duration }}: {{ run.actual_duration_seconds ?? t.none }}</p>
      <p v-if="run.failure_reason">{{ failureReasons[run.failure_reason] }}</p>
      <p>{{ run.notes }}</p>
      <UButton color="neutral" variant="soft" @click="expanded = !expanded">{{
        t.details
      }}</UButton>
      <div v-if="expanded">
        <p v-if="history.isPending.value" role="status">{{ t.loading }}</p>
        <div v-if="history.error.value" role="alert">
          {{ errorMessage(history.error.value)
          }}<UButton @click="history.refetch()">{{ t.retry }}</UButton>
        </div>
        <h5>{{ t.consumptions }}</h5>
        <p v-for="row in history.data.value?.supplies" :key="row.id">
          <ReferenceLabel :id="row.supply_id" kind="supply" /> ·
          {{ t.consumed }}: {{ row.consumed }} {{ row.unit }} · {{ t.wasted }}:
          {{ row.wasted }}
        </p>
        <p v-for="row in history.data.value?.products" :key="row.id">
          <ReferenceLabel :id="row.variant_id" kind="variant" /> ·
          {{ t.consumed }}: {{ row.consumed }} {{ row.unit }} · {{ t.wasted }}:
          {{ row.wasted }} ·
          {{ row.internal_source_step_id ? t.internal : t.external }}
        </p>
      </div></template
    >
  </article>
</template>

<style scoped>
.run-parameters {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
