<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { structureApi } from "~/features/asset-structure/api";
import { errorMessage } from "~/features/shared/http";
const api = structureApi(useRuntimeConfig().public.apiBaseUrl);
const query = useQuery({
  queryKey: ["design-families"],
  queryFn: api.families,
  retry: false,
});
useHead({ title: "Familias de diseño · RRII-Coach" });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <h1>Familias de diseño</h1>
    <p>
      Agrupan diseños para opciones y recursos. No declaran compatibilidad por
      sí mismas.
    </p>
    <UButton to="/families/new">Crear familia</UButton
    ><UButton color="neutral" variant="soft" @click="query.refetch()"
      >Actualizar listado</UButton
    >
    <p v-if="query.isPending.value" role="status">Cargando familias…</p>
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <p v-if="query.data.value?.length === 0">No hay familias.</p>
    <ul class="asset-form">
      <li v-for="row in query.data.value" :key="row.id" class="asset-panel">
        <NuxtLink :to="`/families/${row.id}`">{{ row.name }}</NuxtLink>
        <p>{{ row.description }}</p>
      </li>
    </ul>
  </div>
</template>
