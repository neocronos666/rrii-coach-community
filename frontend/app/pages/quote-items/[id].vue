<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { quickQuoteApi } from "~/features/quick-quotes/api";
import ItemsEditor from "~/features/quote-composition/ItemsEditor.vue";
import { provideDraftGuard } from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
definePageMeta({ key: (route) => route.path });
provideDraftGuard("Hay ítems sin guardar. ¿Salir?");
const id = String(useRoute().params.id);
const api = quickQuoteApi(useRuntimeConfig().public.apiBaseUrl);
const query = useQuery({
  queryKey: ["quote", id],
  queryFn: () => api.quote(id),
  retry: false,
});
async function refresh() {
  return !(await query.refetch()).isError;
}
useHead({ title: "Composición comercial · RRII-Coach" });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <NuxtLink :to="`/quotes/${id}`">Volver al presupuesto</NuxtLink>
    <h1>Composición comercial</h1>
    <p v-if="query.isPending.value" role="status">Cargando…</p>
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <UButton @click="refresh">Consultar registros actuales</UButton>
    <ItemsEditor
      v-if="query.data.value"
      :quote="query.data.value"
      :refresh="refresh"
    />
  </div>
</template>
