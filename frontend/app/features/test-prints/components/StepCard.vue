<script setup lang="ts">
import RunOptions from "~/features/production-editor/RunOptions.vue";
import { startPayload } from "~/features/production-editor/run-options";
const runOptions = ref({ startedAt: "", override: false, parameters: "{}" });
import ReferenceLabel from "./ReferenceLabel.vue";
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import type { TestPrintApi, Schema } from "../api";
import { stepSnapshot } from "../snapshots";
import { usePending } from "~/features/shared/usePending";
import PendingStatus from "~/features/shared/PendingStatus.vue";
import { useDraftGuard } from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
import { testPrintMessages as t } from "~/i18n/test-prints";
import RunCard from "./RunCard.vue";
const props = defineProps<{
  api: TestPrintApi;
  id: string;
  step: Schema["TestPrintStepRead"];
  status: string;
  units: Record<string, unknown>;
}>();
const emit = defineEmits<{ saved: [] }>(),
  cache = useQueryClient(),
  machine = ref("");
const parsed = computed(() => stepSnapshot.safeParse(props.step.snapshot));
const runs = useQuery({
  queryKey: ["test-runs", props.id, props.step.key],
  queryFn: () => props.api.runs(props.id, props.step.key),
  retry: false,
});
const machines = useQuery({
  queryKey: ["quote-machines"],
  queryFn: () => props.api.machines(),
  retry: false,
});
const mutation = usePending<Schema["RunCreate"], Schema["RunRead"]>(
  `start:${props.id}:${props.step.key}`,
  (body) => props.api.start(props.id, props.step.key, body),
  "test-print",
);
const markSaved = useDraftGuard(`test-start:${props.step.id}`, () => [
  machine.value,
  runOptions.value,
]);
async function refresh() {
  await cache.invalidateQueries({
    queryKey: ["test-runs", props.id, props.step.key],
  });
  emit("saved");
}
async function start() {
  let payload;
  try {
    payload = mutation.pending.value
      ? undefined
      : startPayload(machine.value, runOptions.value);
  } catch (failure) {
    mutation.error.value = errorMessage(failure);
    return;
  }
  const result = await mutation.run(payload);
  if (result) {
    runOptions.value.startedAt = "";
    markSaved();
    await refresh();
  }
}
</script>
<template>
  <section class="asset-panel asset-form" :aria-label="`${t.step} ${step.key}`">
    <template v-if="parsed.success"
      ><h2>{{ parsed.data.title }}</h2>
      <p>
        {{ t.target }}: {{ step.planned_quantity }} {{ parsed.data.unit }} ·
        {{ step.completed ? t.complete : t.incomplete }}
      </p>
      <p>
        {{ t.good }}: {{ step.good_quantity }} · {{ t.failed }}:
        {{ step.failed_quantity }}
      </p>
      <p>
        {{ t.dependencies }}: {{ parsed.data.depends_on.join(", ") || t.none }}
      </p>
      <p v-if="parsed.data.instructions">{{ parsed.data.instructions }}</p>
      <p v-if="parsed.data.service_action">{{ parsed.data.service_action }}</p>
      <p v-if="parsed.data.service_instructions">
        {{ parsed.data.service_instructions }}
      </p>
      <details>
        <summary>{{ t.resources }}</summary>
        <p v-for="resource in parsed.data.resources" :key="resource.key">
          {{ resource.name }} · Revisión {{ resource.revision_number }} ·
          {{ resource.quantity_per_batch }}
        </p>
        <p
          v-for="material in parsed.data.supply_inputs"
          :key="material.supply_id"
        >
          {{ t.materials }}:
          <ReferenceLabel :id="material.supply_id" kind="supply" /> ·
          {{ material.quantity_per_batch }}
          {{ units[material.supply_id] ?? "" }}
        </p>
        <p
          v-for="component in parsed.data.product_inputs"
          :key="component.product_variant_id"
        >
          {{ t.components }}:
          <ReferenceLabel :id="component.product_variant_id" kind="variant" /> ·
          {{ component.quantity_per_batch }} ·
          {{
            component.source_step_key
              ? `${t.internal}: ${component.source_step_key}`
              : t.external
          }}
        </p>
      </details>
      <PendingStatus
        :pending="!!mutation.pending.value"
        :busy="mutation.busy.value"
        :error="mutation.error.value"
        :persistent="mutation.persistent.value"
        :invalid="mutation.invalid.value"
        @retry="start"
        @clear="mutation.clearInvalid" />
      <form
        v-if="status === 'open' && !step.open_run_id"
        class="asset-form"
        @submit.prevent="start"
      >
        <fieldset
          :disabled="
            !mutation.ready.value ||
            mutation.busy.value ||
            !!mutation.pending.value ||
            mutation.invalid.value
          "
        >
          <RunOptions v-model="runOptions" />
          <p>{{ t.machineHelp }}</p>
          <div v-if="machines.error.value" role="alert">
            {{ errorMessage(machines.error.value)
            }}<UButton @click="machines.refetch()">{{ t.retry }}</UButton>
          </div>
          <label
            >{{ t.machine
            }}<select v-model="machine">
              <option value="">Usar asignación guardada (si existe)</option>
              <option value="none">Sin máquina</option>
              <option
                v-for="row in machines.data.value"
                :key="row.id"
                :value="row.id"
              >
                {{ row.name }}
              </option>
            </select></label
          ><UButton type="submit">{{ t.start }}</UButton>
        </fieldset>
      </form>
      <h3>{{ t.attempts }}</h3>
      <p v-if="runs.isPending.value" role="status">{{ t.loading }}</p>
      <div v-if="runs.error.value" role="alert">
        {{ errorMessage(runs.error.value)
        }}<UButton @click="runs.refetch()">{{ t.retry }}</UButton>
      </div>
      <RunCard
        v-for="run in runs.data.value"
        :key="run.id"
        :api="api"
        :run="run"
        :snapshot="parsed.data"
        :units="units"
        @saved="refresh"
    /></template>
    <p v-else role="alert">{{ t.snapshotError }}</p>
  </section>
</template>
