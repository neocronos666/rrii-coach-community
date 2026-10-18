<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { quickQuoteApi } from "~/features/quick-quotes/api";
import ItemsEditor from "~/features/quote-composition/ItemsEditor.vue";
import { provideDraftGuard } from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
provideDraftGuard("Hay ítems sin guardar. ¿Salir?");
const query = useQuery({
  queryKey: ["quotes"],
  queryFn: quickQuoteApi(useRuntimeConfig().public.apiBaseUrl).quotes,
  retry: false,
});
async function refresh() {
  return !(await query.refetch()).isError;
}
useHead({ title: "Nuevo presupuesto · RRII-Coach" });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <NuxtLink to="/quotes">Presupuestos</NuxtLink>
    <h1>Presupuesto con ítems técnicos</h1>
    <ItemsEditor :refresh="refresh" />
    <details class="asset-panel">
      <summary>Presupuestos guardados para revisar</summary>
      <p v-if="query.error.value" role="alert">
        {{ errorMessage(query.error.value) }}
      </p>
      <ul>
        <li v-for="row in query.data.value" :key="row.id">
          <NuxtLink :to="`/quotes/${row.id}`"
            >{{ row.code }} · {{ row.title }}</NuxtLink
          >
        </li>
      </ul>
    </details>
  </div>
</template>
