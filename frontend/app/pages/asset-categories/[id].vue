<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { detailsApi } from "~/features/asset-details/api";
import { useRecordedWrite } from "~/features/inventory/useRecordedWrite";
import WriteStatus from "~/features/inventory/WriteStatus.vue";
import {
  provideDraftGuard,
  useDraftGuard,
} from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
definePageMeta({ key: (route) => route.path });
const id = String(useRoute().params.id),
  isNew = id === "new",
  api = detailsApi(useRuntimeConfig().public.apiBaseUrl);
const query = useQuery({
  queryKey: ["asset-category-admin", id],
  queryFn: api.categories,
  retry: false,
});
const record = computed(() => query.data.value?.find((row) => row.id === id));
const name = ref(""),
  ready = ref(isNew),
  confirmed = ref(false);
const registry = provideDraftGuard(
    "Hay cambios de categoría sin guardar. ¿Salir?",
  ),
  markSaved = useDraftGuard("category", () => name.value, registry);
watch(
  record,
  (row) => {
    if (row && !ready.value) {
      name.value = row.name;
      ready.value = true;
      markSaved();
    }
  },
  { immediate: true },
);
async function refresh() {
  return !(await query.refetch()).isError;
}
const state = useRecordedWrite(`asset-category:${id}`, refresh);
async function save() {
  if (!confirmed.value) return;
  const row = await state.run(name.value, () =>
    isNew ? api.createCategory(name.value) : api.renameCategory(id, name.value),
  );
  if (row) {
    name.value = row.name;
    confirmed.value = false;
    markSaved();
    if (isNew) await navigateTo(`/asset-categories/${row.id}`);
  }
}
async function remove() {
  if (
    !window.confirm(
      "¿Eliminar esta categoría? Sus Assets se reasignarán a la categoría de respaldo. No se eliminan Assets, revisiones ni archivos.",
    )
  )
    return;
  const result = await state.run(
    "Eliminar categoría y reasignar Assets a respaldo",
    () => api.deleteCategory(id),
  );
  if (result) {
    markSaved();
    await navigateTo("/asset-categories");
  }
}
useHead(() => ({
  title: `${isNew ? "Crear categoría" : (record.value?.name ?? "Categoría")} · RRII-Coach`,
}));
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton to="/asset-categories" color="neutral" variant="soft"
      >Categorías de Assets</UButton
    >
    <h1>{{ isNew ? "Crear categoría" : (record?.name ?? "Categoría") }}</h1>
    <UButton color="neutral" variant="soft" @click="refresh"
      >Consultar registros actuales</UButton
    >
    <p v-if="query.isPending.value" role="status">Cargando categoría…</p>
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <WriteStatus :state="state" />
    <p v-if="!isNew && query.data.value && !record">
      La categoría ya no aparece en los registros actuales. Revisá el listado
      antes de realizar otra operación.
    </p>
    <p v-if="record?.system_key">
      Categoría del sistema protegida. No se puede renombrar ni eliminar.
    </p>
    <p v-if="record">Nombre guardado: {{ record.name }}</p>
    <form
      v-if="isNew || record"
      class="asset-panel asset-form"
      @submit.prevent="save"
    >
      <fieldset
        :disabled="state.locked.value || !ready || !!record?.system_key"
      >
        <label>Nombre<input v-model="name" required maxlength="255" /></label
        ><label class="catalog-check"
          ><input v-model="confirmed" required type="checkbox" />Confirmo el
          nombre de la categoría.</label
        ><UButton type="submit">Guardar categoría</UButton>
      </fieldset>
    </form>
    <section v-if="record && !record.system_key" class="asset-panel asset-form">
      <p>
        Eliminar reasigna sus Assets a la categoría de respaldo. Conserva los
        recursos y toda su historia.
      </p>
      <UButton
        color="neutral"
        variant="soft"
        :disabled="state.locked.value"
        @click="remove"
        >Eliminar categoría</UButton
      >
    </section>
    <section class="asset-panel">
      <h2>Registros actuales para revisar el resultado</h2>
      <ul>
        <li v-for="row in query.data.value" :key="row.id">
          <NuxtLink :to="`/asset-categories/${row.id}`">{{
            row.name
          }}</NuxtLink>
          · {{ row.id }}
        </li>
      </ul>
    </section>
  </div>
</template>
