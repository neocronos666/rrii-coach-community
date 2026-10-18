<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { productionApi } from "~/features/production/api";
import TaskList from "~/features/production/TaskList.vue";
import ReferenceLabel from "~/features/test-prints/components/ReferenceLabel.vue";
import {
  configurationSnapshot,
  snapshotName,
  omittedKeys,
} from "~/features/test-prints/snapshots";
import { errorMessage } from "~/features/shared/http";
import { inventoryMessages as i } from "~/i18n/inventory";
import { productionMessages as p } from "~/i18n/production";
import { testPrintMessages as t } from "~/i18n/test-prints";
definePageMeta({ key: (route) => route.path });
const id = String(useRoute().params.id),
  api = productionApi(useRuntimeConfig().public.apiBaseUrl);
const query = useQuery({
  queryKey: ["production-plan", id],
  queryFn: () => api.plan(id),
  retry: false,
});
const plan = computed(() => query.data.value);
const configuration = computed(() =>
  configurationSnapshot.safeParse(plan.value?.snapshot.configuration),
);
useHead({ title: `${p.plan} · RRII-Coach` });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton to="/production" color="neutral" variant="soft">{{
      p.title
    }}</UButton>
    <h1>{{ p.plan }}</h1>
    <p v-if="query.isPending.value" role="status">{{ t.loading }}</p>
    <div v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </div>
    <UButton color="neutral" variant="soft" @click="query.refetch()">{{
      t.refresh
    }}</UButton>
    <template v-if="plan">
      <section class="asset-panel asset-form">
        <h2>{{ snapshotName(plan.snapshot) }}</h2>
        <p>{{ p.historical }}</p>
        <p>
          {{ t.variant }}:
          <ReferenceLabel :id="plan.variant_id" kind="variant" />
        </p>
        <p>{{ t.target }}: {{ plan.target_quantity }}</p>
        <p>
          {{ t.omitted }}: {{ omittedKeys(plan.snapshot).join(", ") || t.none }}
        </p>
        <p>{{ p.allocation }}: {{ plan.allocation_id || p.noAllocation }}</p>
        <UButton
          v-if="plan.order_id"
          :to="`/orders/${plan.order_id}`"
          color="neutral"
          variant="soft"
          >{{ p.source }}</UButton
        >
        <UButton
          v-if="plan.project_component_id"
          :to="`/production?component=${plan.project_component_id}`"
          color="neutral"
          variant="soft"
          >{{ p.productionLink }} · {{ plan.project_component_id }}</UButton
        >
      </section>
      <section v-if="plan.warnings.length" class="asset-panel">
        <h2>{{ p.warnings }}</h2>
        <ul>
          <li v-for="warning in plan.warnings" :key="warning">{{ warning }}</li>
        </ul>
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
      <UButton
        v-if="plan.allocation_id"
        :to="`/inventory/allocations/${plan.allocation_id}`"
        >{{ i.allocations }}</UButton
      >
      <TaskList :tasks="plan.tasks" />
    </template>
  </div>
</template>
