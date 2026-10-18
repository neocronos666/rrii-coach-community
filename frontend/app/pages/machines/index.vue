<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { machinesApi, type Schema } from "~/features/machines/api";
import { machineTypes } from "~/features/machines/fields";
import { errorMessage } from "~/features/shared/http";
const api = machinesApi(useRuntimeConfig().public.apiBaseUrl);
const active = ref(""),
  type = ref<Schema["MachineType"] | "">("");
const query = useQuery({
  queryKey: computed(() => ["machines-catalog", active.value, type.value]),
  queryFn: () =>
    api.list(
      active.value === "" ? undefined : active.value === "true",
      type.value || undefined,
    ),
  retry: false,
});
useHead({ title: "Máquinas · RRII-Coach" });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <h1>Máquinas</h1>
    <UButton to="/machines/new">Registrar máquina</UButton>
    <p>
      El catálogo conserva equipos activos e inactivos. La ocupación se consulta
      desde producción.
    </p>
    <div class="asset-panel asset-form">
      <label
        >Estado<select v-model="active">
          <option value="">Todos</option>
          <option value="true">Activas</option>
          <option value="false">Inactivas</option>
        </select></label
      >
      <label
        >Tipo<select v-model="type">
          <option value="">Todos</option>
          <option
            v-for="(label, value) in machineTypes"
            :key="value"
            :value="value"
          >
            {{ label }}
          </option>
        </select></label
      >
      <UButton color="neutral" variant="soft" @click="query.refetch()"
        >Actualizar listado</UButton
      >
    </div>
    <p v-if="query.isPending.value" role="status">Cargando máquinas…</p>
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <p v-if="query.data.value?.length === 0">
      No hay máquinas para estos filtros.
    </p>
    <ul class="asset-form">
      <li
        v-for="row in query.data.value"
        :key="row.id"
        class="asset-panel"
        data-testid="machine-row"
      >
        <NuxtLink :to="`/machines/${row.id}`">{{ row.name }}</NuxtLink> ·
        {{ machineTypes[row.machine_type] }} ·
        {{ row.active ? "Activa" : "Inactiva" }}
        <p>{{ row.manufacturer }} {{ row.model }}</p>
      </li>
    </ul>
  </div>
</template>
