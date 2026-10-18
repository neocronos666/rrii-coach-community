<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { structureApi } from "~/features/asset-structure/api";
import FamilyEditor from "~/features/asset-structure/FamilyEditor.vue";
import { provideDraftGuard } from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
definePageMeta({ key: (route) => route.path });
const id = String(useRoute().params.id),
  isNew = id === "new",
  api = structureApi(useRuntimeConfig().public.apiBaseUrl);
const query = useQuery({
  queryKey: ["design-family", id],
  queryFn: () => api.family(id),
  enabled: !isNew,
  retry: false,
});
const list = useQuery({
  queryKey: ["families-review"],
  queryFn: api.families,
  enabled: isNew,
  retry: false,
});
provideDraftGuard("Hay cambios de familia sin guardar. ¿Salir?");
async function refresh() {
  return !(await (isNew ? list.refetch() : query.refetch())).isError;
}
useHead(() => ({
  title: `${query.data.value?.name ?? "Crear familia"} · RRII-Coach`,
}));
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton to="/families" color="neutral" variant="soft"
      >Familias de diseño</UButton
    >
    <h1>
      {{ isNew ? "Crear familia" : (query.data.value?.name ?? "Familia") }}
    </h1>
    <UButton color="neutral" variant="soft" @click="refresh"
      >Consultar registros actuales</UButton
    >
    <p v-if="query.error.value || list.error.value" role="alert">
      {{ errorMessage(query.error.value || list.error.value) }}
    </p>
    <section
      v-if="query.data.value"
      class="asset-panel"
      aria-label="Datos guardados"
    >
      <p>{{ query.data.value.name }}</p>
      <p>{{ query.data.value.description }}</p>
    </section>
    <FamilyEditor
      v-if="isNew || query.data.value"
      :family="query.data.value"
      :refresh="refresh"
      @saved="(value) => (isNew ? navigateTo(`/families/${value}`) : undefined)"
    />
    <section v-if="isNew" class="asset-panel">
      <h2>Registros actuales para revisar el resultado</h2>
      <ul>
        <li v-for="row in list.data.value" :key="row.id">
          <NuxtLink :to="`/families/${row.id}`">{{ row.name }}</NuxtLink> ·
          {{ row.id }}
        </li>
      </ul>
    </section>
  </div>
</template>
