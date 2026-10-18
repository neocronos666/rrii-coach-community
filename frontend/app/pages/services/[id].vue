<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { servicesApi } from "~/features/services/api";
import ServiceEditor from "~/features/services/ServiceEditor.vue";
import ActionPreview from "~/features/services/ActionPreview.vue";
import { errorMessage } from "~/features/shared/http";
import { provideDraftGuard } from "~/features/shared/useDraftGuard";
definePageMeta({ key: (route) => route.path });
const id = String(useRoute().params.id),
  isNew = id === "new",
  api = servicesApi(useRuntimeConfig().public.apiBaseUrl);
const query = useQuery({
  queryKey: ["service-detail", id],
  queryFn: () => api.get(id),
  enabled: !isNew,
  retry: false,
});
const catalog = useQuery({
  queryKey: ["services-review"],
  queryFn: () => api.list(),
  enabled: isNew,
  retry: false,
});
const resetKey = ref(0);
provideDraftGuard(
  "Hay cambios del servicio sin guardar. ¿Salir de la pantalla?",
);
async function refresh() {
  const result = await (isNew ? catalog.refetch() : query.refetch());
  resetKey.value++;
  return !result.isError;
}
async function saved(id: string) {
  if (isNew) await navigateTo(`/services/${id}`);
}
useHead(() => ({
  title: `${isNew ? "Registrar servicio" : (query.data.value?.name ?? "Servicio")} · RRII-Coach`,
}));
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton to="/services" color="neutral" variant="soft"
      >Servicios reutilizables</UButton
    >
    <h1>
      {{
        isNew ? "Registrar servicio" : (query.data.value?.name ?? "Servicio")
      }}
    </h1>
    <UButton color="neutral" variant="soft" @click="refresh"
      >Consultar registros actuales</UButton
    >
    <p v-if="query.error.value || catalog.error.value" role="alert">
      {{ errorMessage(query.error.value || catalog.error.value) }}
    </p>
    <p v-if="!isNew && query.isPending.value" role="status">
      Cargando servicio…
    </p>
    <section
      v-if="query.data.value"
      class="asset-panel"
      aria-label="Datos guardados"
    >
      <p>
        {{ query.data.value.name }} ·
        {{ query.data.value.active ? "Activo" : "Inactivo" }}
      </p>
      <p>{{ query.data.value.instructions }}</p>
      <p>{{ query.data.value.action_template ?? "Sin plantilla" }}</p>
    </section>
    <ServiceEditor
      v-if="isNew || query.data.value"
      :service="query.data.value"
      :refresh="refresh"
      @saved="saved"
      @changed="resetKey++"
    />
    <ActionPreview
      v-if="query.data.value"
      :service="query.data.value"
      :reset-key="resetKey"
    />
    <section v-if="isNew" class="asset-panel">
      <h2>Registros actuales para revisar el resultado</h2>
      <ul>
        <li v-for="row in catalog.data.value" :key="row.id">
          <NuxtLink :to="`/services/${row.id}`">{{ row.name }}</NuxtLink> ·
          {{ row.id }}
        </li>
      </ul>
    </section>
  </div>
</template>
