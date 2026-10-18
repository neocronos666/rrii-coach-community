<script setup lang="ts">
import RunOptions from "~/features/production-editor/RunOptions.vue";
import { startPayload } from "~/features/production-editor/run-options";
const runOptions = ref({ startedAt: "", override: false, parameters: "{}" });
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { productionApi, type Schema } from "~/features/production/api";
import { testPrintApi } from "~/features/test-prints/api";
import { productApi } from "~/features/products/api";
import { stepSnapshot } from "~/features/test-prints/snapshots";
import LegacyActions from "~/features/production-editor/LegacyActions.vue";
import RunCard from "~/features/test-prints/components/RunCard.vue";
import ReferenceLabel from "~/features/test-prints/components/ReferenceLabel.vue";
import PendingStatus from "~/features/shared/PendingStatus.vue";
import { usePending } from "~/features/shared/usePending";
import {
  provideDraftGuard,
  useDraftGuard,
} from "~/features/shared/useDraftGuard";
import { ApiError, errorMessage } from "~/features/shared/http";
import { inventoryMessages as i } from "~/i18n/inventory";
import { productionMessages as p, productionStates } from "~/i18n/production";
import { testPrintMessages as t } from "~/i18n/test-prints";
definePageMeta({ key: (route) => route.path });
const id = String(useRoute().params.id),
  base = useRuntimeConfig().public.apiBaseUrl,
  api = productionApi(base),
  helper = testPrintApi(base),
  cache = useQueryClient();
const query = useQuery({
  queryKey: ["production-task", id],
  queryFn: () => api.task(id),
  retry: false,
});
const task = computed(() => query.data.value);
const parsed = computed(() =>
  stepSnapshot.safeParse(
    task.value?.origin === "manual"
      ? {
          key: task.value.id,
          title: task.value.title,
          kind: task.value.task_type,
          unit: task.value.planned_unit ?? "",
          depends_on: [],
          resources: [],
          supply_inputs: [],
          product_inputs: [],
        }
      : task.value?.recipe_snapshot?.step,
  ),
);
const runs = useQuery({
  queryKey: ["production-runs", id],
  queryFn: () => api.runs(id),
  enabled: computed(() => task.value?.execution_mode === "runs"),
  retry: false,
});
const progress = useQuery({
  queryKey: ["production-progress", id],
  queryFn: () => api.progress(id),
  enabled: computed(() => task.value?.execution_mode === "runs"),
  retry: false,
});
const dependencies = useQuery({
  queryKey: ["production-dependencies", id],
  queryFn: () => api.dependencies(id),
  enabled: computed(() => !!task.value),
  retry: false,
});
const machines = useQuery({
  queryKey: ["quote-machines"],
  queryFn: helper.machines,
  retry: false,
});
const supplies = useQuery({
  queryKey: ["test-reference-supplies"],
  queryFn: productApi(base).supplies,
  retry: false,
});
const units = computed(() =>
  Object.fromEntries(
    (supplies.data.value ?? []).map((row) => [row.id, row.base_unit]),
  ),
);
const machine = ref(""),
  busy = ref(false),
  error = ref(""),
  confirmed = ref(false);
const registry = provideDraftGuard(t.unsaved);
const markSaved = useDraftGuard(
  `production-start:${id}`,
  () => [machine.value, runOptions.value],
  registry,
);
const startMutation = usePending<Schema["RunCreate"], Schema["RunRead"]>(
  `start:${id}`,
  (body) => api.start(id, body),
  "production",
);
async function refresh() {
  await Promise.all([
    query.refetch(),
    runs.isEnabled.value ? runs.refetch() : Promise.resolve(),
    progress.isEnabled.value ? progress.refetch() : Promise.resolve(),
    dependencies.refetch(),
    cache.invalidateQueries({ queryKey: ["production-tasks"] }),
    cache.invalidateQueries({ queryKey: ["production-plan"] }),
  ]);
}
async function start() {
  let payload;
  try {
    payload = startMutation.pending.value
      ? undefined
      : startPayload(machine.value, runOptions.value);
  } catch (failure) {
    startMutation.error.value = errorMessage(failure);
    return;
  }
  const result = await startMutation.run(payload);
  if (result) {
    runOptions.value.startedAt = "";
    markSaved();
    await refresh();
  }
}
async function action(value: "pause" | "resume" | "cancel") {
  if (busy.value || !confirmed.value) return;
  busy.value = true;
  error.value = "";
  try {
    await api.action(id, value);
    confirmed.value = false;
  } catch (failure) {
    error.value = errorMessage(failure);
    if (
      !(failure instanceof ApiError) ||
      failure.status >= 500 ||
      failure.status === 408
    )
      error.value += ` ${p.uncertain}`;
  } finally {
    await refresh();
    busy.value = false;
  }
}
useHead(() => ({ title: `${task.value?.code || p.task} · RRII-Coach` }));
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton to="/production" color="neutral" variant="soft">{{
      p.title
    }}</UButton>
    <p v-if="query.isPending.value" role="status">{{ t.loading }}</p>
    <div v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </div>
    <UButton color="neutral" variant="soft" @click="refresh">{{
      t.refresh
    }}</UButton>
    <template v-if="task">
      <h1>{{ task.code }} · {{ task.title }}</h1>
      <UButton :to="`/task-edit/${task.id}`">Editar planificación</UButton>
      <UButton
        :to="`/inventory/reservations/${task.id}`"
        color="neutral"
        variant="soft"
        >{{ i.reservations }}</UButton
      >
      <p data-testid="task-status">{{ productionStates[task.status] }}</p>
      <p>{{ t.target }}: {{ task.planned_quantity }} {{ task.planned_unit }}</p>
      <p>{{ task.description }}</p>
      <p>{{ task.notes }}</p>
      <UButton
        v-if="task.production_plan_id"
        :to="`/production/plans/${task.production_plan_id}`"
        color="neutral"
        variant="soft"
        >{{ p.planLink }}</UButton
      >
      <UButton
        v-if="task.order_id"
        :to="`/orders/${task.order_id}`"
        color="neutral"
        variant="soft"
        >{{ p.source }}</UButton
      >
      <section class="asset-panel">
        <h2>{{ t.dependencies }}</h2>
        <p v-if="dependencies.isPending.value" role="status">{{ t.loading }}</p>
        <div v-if="dependencies.error.value" role="alert">
          {{ errorMessage(dependencies.error.value) }}
        </div>
        <p v-if="dependencies.data.value?.length === 0">{{ t.none }}</p>
        <ul>
          <li
            v-for="row in dependencies.data.value"
            :key="row.depends_on_task_id"
          >
            <NuxtLink :to="`/production/tasks/${row.depends_on_task_id}`"
              >{{ row.prerequisite.code }} ·
              {{ row.prerequisite.title }}</NuxtLink
            >
            · {{ productionStates[row.prerequisite.status] }}
          </li>
        </ul>
      </section>
      <LegacyActions
        v-if="task.execution_mode === 'legacy'"
        :task="task"
        :refresh="refresh"
      />
      <template v-else>
        <section class="asset-panel">
          <h2>{{ p.progress }}</h2>
          <p v-if="progress.isPending.value" role="status">{{ t.loading }}</p>
          <div v-if="progress.error.value" role="alert">
            {{ errorMessage(progress.error.value) }}
          </div>
          <dl v-if="progress.data.value" data-testid="task-progress">
            <dt>{{ t.good }}</dt>
            <dd>{{ progress.data.value.good_quantity }}</dd>
            <dt>{{ t.failed }}</dt>
            <dd>{{ progress.data.value.failed_quantity }}</dd>
            <dt>{{ p.remaining }}</dt>
            <dd>{{ progress.data.value.remaining_quantity }}</dd>
            <dt>{{ p.excess }}</dt>
            <dd>{{ progress.data.value.excess_quantity }}</dd>
          </dl>
        </section>
        <template v-if="parsed.success">
          <details class="asset-panel">
            <summary>{{ t.resources }}</summary>
            <p v-if="parsed.data.instructions">
              {{ parsed.data.instructions }}
            </p>
            <p v-for="resource in parsed.data.resources" :key="resource.key">
              {{ resource.name }} · {{ t.revision }}
              {{ resource.revision_number }} · {{ resource.quantity_per_batch }}
            </p>
            <p
              v-for="material in parsed.data.supply_inputs"
              :key="material.supply_id"
            >
              {{ t.materials }}:
              <ReferenceLabel :id="material.supply_id" kind="supply" /> ·
              {{ material.quantity_per_batch }}
            </p>
            <p
              v-for="component in parsed.data.product_inputs"
              :key="component.product_variant_id"
            >
              {{ t.components }}:
              <ReferenceLabel
                :id="component.product_variant_id"
                kind="variant"
              />
              · {{ component.quantity_per_batch }} ·
              {{ component.source_step_key || t.external }}
            </p>
          </details>
          <PendingStatus
            :pending="!!startMutation.pending.value"
            :busy="startMutation.busy.value"
            :error="startMutation.error.value"
            :persistent="startMutation.persistent.value"
            :invalid="startMutation.invalid.value"
            @retry="start"
            @clear="startMutation.clearInvalid"
          />
          <form
            v-if="
              ['queued', 'in_progress'].includes(task.status) &&
              runs.data.value &&
              !runs.data.value.some((row) => row.status === 'running')
            "
            class="asset-panel asset-form"
            @submit.prevent="start"
          >
            <fieldset
              :disabled="
                !startMutation.ready.value ||
                startMutation.busy.value ||
                !!startMutation.pending.value ||
                startMutation.invalid.value ||
                busy
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
          <h2>{{ t.attempts }}</h2>
          <p>{{ p.currentUnits }}</p>
          <div v-if="supplies.error.value" role="alert">
            {{ errorMessage(supplies.error.value)
            }}<UButton @click="supplies.refetch()">{{ t.retry }}</UButton>
          </div>
          <p v-if="runs.isPending.value" role="status">{{ t.loading }}</p>
          <div v-if="runs.error.value" role="alert">
            {{ errorMessage(runs.error.value) }}
          </div>
          <RunCard
            v-for="run in runs.data.value"
            :key="run.id"
            :api="helper"
            :run="run"
            :snapshot="parsed.data"
            :units="units"
            namespace="production"
            :close-help="p.closeHelp"
            @saved="refresh"
          />
        </template>
        <p v-else role="alert">
          {{ task.origin === "recipe" ? t.snapshotError : p.manual }}
        </p>
        <p v-if="error" role="alert">{{ error }}</p>
        <section
          v-if="['queued', 'in_progress', 'paused'].includes(task.status)"
          class="asset-panel asset-form"
        >
          <h2>{{ t.status }}</h2>
          <p>{{ p.actionHelp }}</p>
          <fieldset
            :disabled="
              busy || startMutation.busy.value || !!startMutation.pending.value
            "
          >
            <label class="catalog-check"
              ><input v-model="confirmed" type="checkbox" />{{
                p.actionConfirm
              }}</label
            >
            <div class="asset-actions">
              <UButton
                v-if="task.status === 'in_progress'"
                :disabled="!confirmed"
                @click="action('pause')"
                >{{ p.pause }}</UButton
              ><UButton
                v-if="task.status === 'paused'"
                :disabled="!confirmed"
                @click="action('resume')"
                >{{ p.resume }}</UButton
              ><UButton
                :disabled="!confirmed"
                color="neutral"
                variant="soft"
                @click="action('cancel')"
                >{{ p.cancel }}</UButton
              >
            </div>
          </fieldset>
        </section>
      </template>
    </template>
  </div>
</template>
