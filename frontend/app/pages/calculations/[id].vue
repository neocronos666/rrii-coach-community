<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { compositionApi } from "~/features/quote-composition/api";
import CalculationView from "~/features/quote-composition/CalculationView.vue";
import { errorMessage } from "~/features/shared/http";
definePageMeta({ key: (route) => route.path });
const id = String(useRoute().params.id),
  api = compositionApi(useRuntimeConfig().public.apiBaseUrl);
const query = useQuery({
  queryKey: ["calculation", id],
  queryFn: () => api.calculation(id),
  retry: false,
});
useHead({ title: "Cálculo técnico · RRII-Coach" });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <NuxtLink to="/quotes/new">Crear presupuesto con ítems</NuxtLink>
    <h1>Cálculo técnico</h1>
    <p v-if="query.isPending.value" role="status">Cargando…</p>
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <UButton @click="query.refetch()">Consultar snapshot</UButton
    ><CalculationView v-if="query.data.value" :calculation="query.data.value" />
  </div>
</template>
