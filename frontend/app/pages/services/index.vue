<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { servicesApi } from "~/features/services/api";
import { errorMessage } from "~/features/shared/http";
const api = servicesApi(useRuntimeConfig().public.apiBaseUrl);
const active = ref(""),
  search = ref(""),
  applied = ref({ active: "", search: "" });
const query = useQuery({
  queryKey: computed(() => ["services-catalog", applied.value]),
  queryFn: () =>
    api.list(
      applied.value.active === "" ? undefined : applied.value.active === "true",
      applied.value.search || undefined,
    ),
  retry: false,
});
useHead({ title: "Servicios reutilizables · RRII-Coach" });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <h1>Servicios reutilizables</h1>
    <UButton to="/services/new">Registrar servicio</UButton>
    <form
      class="asset-panel asset-form"
      @submit.prevent="applied = { active, search }"
    >
      <label>Buscar servicio<input v-model="search" maxlength="255" /></label>
      <label
        >Estado<select v-model="active">
          <option value="">Todos</option>
          <option value="true">Activos</option>
          <option value="false">Inactivos</option>
        </select></label
      >
      <UButton type="submit">Aplicar filtros</UButton>
    </form>
    <UButton color="neutral" variant="soft" @click="query.refetch()"
      >Actualizar listado</UButton
    >
    <p v-if="query.isPending.value" role="status">Cargando servicios…</p>
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <p v-if="query.data.value?.length === 0">
      No hay servicios para estos filtros.
    </p>
    <ul class="asset-form">
      <li v-for="row in query.data.value" :key="row.id" class="asset-panel">
        <NuxtLink :to="`/services/${row.id}`">{{ row.name }}</NuxtLink> ·
        {{ row.active ? "Activo" : "Inactivo" }}
        <p>{{ row.instructions }}</p>
      </li>
    </ul>
  </div>
</template>
