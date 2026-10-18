<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { productionApi, type TaskFilters } from "~/features/production/api";
import { testPrintApi } from "~/features/test-prints/api";
import TaskList from "~/features/production/TaskList.vue";
import { errorMessage } from "~/features/shared/http";
import {
  productionMessages as p,
  productionStates,
  productionPriorities,
} from "~/i18n/production";
import { testPrintMessages as t } from "~/i18n/test-prints";
definePageMeta({ key: (route) => route.fullPath });
const route = useRoute(),
  base = useRuntimeConfig().public.apiBaseUrl,
  api = productionApi(base);
const value = (key: string) =>
  typeof route.query[key] === "string"
    ? (route.query[key] as string)
    : undefined;
const filters = reactive<TaskFilters>({
  machine_id: value("machine"),
  order_id: value("order"),
  project_component_id: value("component"),
  project_id: value("project"),
});
const applied = ref<TaskFilters>({ ...filters });
const query = useQuery({
  queryKey: computed(() => ["production-tasks", applied.value]),
  queryFn: () => api.tasks(applied.value),
  retry: false,
});
const machines = useQuery({
  queryKey: ["quote-machines"],
  queryFn: testPrintApi(base).machines,
  retry: false,
});
useHead({ title: `${p.title} · RRII-Coach` });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <h1>{{ p.title }}</h1>
    <nav class="asset-actions" :aria-label="p.source">
      <UButton to="/orders" color="neutral" variant="soft">Pedidos</UButton
      ><UButton to="/projects" color="neutral" variant="soft">Proyectos</UButton
      ><UButton
        v-if="
          filters.order_id || filters.project_id || filters.project_component_id
        "
        to="/production"
        color="neutral"
        variant="soft"
        >{{ p.clear }}</UButton
      >
    </nav>
    <p v-if="filters.order_id">Pedido: {{ filters.order_id }}</p>
    <p v-if="filters.project_component_id">
      Componente: {{ filters.project_component_id }}
    </p>
    <p v-if="filters.project_id">Proyecto: {{ filters.project_id }}</p>
    <form
      class="asset-panel asset-form"
      @submit.prevent="applied = { ...filters }"
    >
      <label
        >{{ t.status
        }}<select v-model="filters.status">
          <option :value="undefined">{{ p.all }}</option>
          <option
            v-for="(label, key) in productionStates"
            :key="key"
            :value="key"
          >
            {{ label }}
          </option>
        </select></label
      >
      <label
        >{{ p.priority
        }}<select v-model="filters.priority">
          <option :value="undefined">{{ p.all }}</option>
          <option
            v-for="(label, key) in productionPriorities"
            :key="key"
            :value="key"
          >
            {{ label }}
          </option>
        </select></label
      >
      <label
        >{{ p.machine
        }}<select v-model="filters.machine_id">
          <option :value="undefined">{{ p.all }}</option>
          <option
            v-for="row in machines.data.value"
            :key="row.id"
            :value="row.id"
          >
            {{ row.name }}
          </option>
        </select></label
      >
      <UButton type="submit">{{ p.filter }}</UButton>
    </form>
    <div v-if="machines.error.value" role="alert">
      {{ errorMessage(machines.error.value)
      }}<UButton @click="machines.refetch()">{{ t.retry }}</UButton>
    </div>
    <p v-if="query.isPending.value" role="status">{{ t.loading }}</p>
    <div v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </div>
    <UButton color="neutral" variant="soft" @click="query.refetch()">{{
      t.refresh
    }}</UButton>
    <TaskList v-if="query.data.value" :tasks="query.data.value" />
  </div>
</template>
