<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { detailsApi } from "~/features/asset-details/api";
import { errorMessage } from "~/features/shared/http";
const api = detailsApi(useRuntimeConfig().public.apiBaseUrl);
const query = useQuery({
  queryKey: ["asset-categories-admin"],
  queryFn: api.categories,
  retry: false,
});
useHead({ title: "Categorías de Assets · RRII-Coach" });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton to="/assets" color="neutral" variant="soft">Biblioteca</UButton>
    <h1>Categorías de Assets</h1>
    <UButton to="/asset-categories/new">Crear categoría</UButton
    ><UButton color="neutral" variant="soft" @click="query.refetch()"
      >Actualizar listado</UButton
    >
    <p v-if="query.isPending.value" role="status">Cargando categorías…</p>
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <ul class="asset-form">
      <li v-for="row in query.data.value" :key="row.id" class="asset-panel">
        <NuxtLink :to="`/asset-categories/${row.id}`">{{ row.name }}</NuxtLink
        >{{ row.system_key ? " · Categoría del sistema protegida" : "" }}
      </li>
    </ul>
  </div>
</template>
