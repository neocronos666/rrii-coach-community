<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { optionsApi, type OptionRecord, type Schema } from "./api";
import OptionEditor from "./OptionEditor.vue";
import OptionList from "./OptionList.vue";
import { errorMessage } from "~/features/shared/http";
import { provideDraftGuard } from "~/features/shared/useDraftGuard";
const props = defineProps<{ definition: string; value?: string }>();
const valueMode = props.value !== undefined,
  id = props.value ?? props.definition,
  isNew = id === "new";
const api = optionsApi(useRuntimeConfig().public.apiBaseUrl);
const query = useQuery({
  queryKey: ["option-detail", props.definition, props.value ?? ""],
  retry: false,
  queryFn: async (): Promise<{
    parent?: Schema["OptionDefinitionRead"];
    record?: OptionRecord;
  }> => {
    const parent = valueMode
      ? await api.definition(props.definition)
      : undefined;
    const record = isNew
      ? undefined
      : valueMode
        ? await api.value(props.definition, id)
        : await api.definition(id);
    return { parent, record };
  },
});
const review = useQuery({
  queryKey: ["options-review", valueMode ? props.definition : ""],
  enabled: isNew,
  retry: false,
  queryFn: () => (valueMode ? api.values(props.definition) : api.definitions()),
});
provideDraftGuard(
  "Hay cambios del catálogo sin guardar. ¿Salir de la pantalla?",
);
async function refresh() {
  const results = await Promise.all([
    query.refetch(),
    ...(isNew ? [review.refetch()] : []),
  ]);
  return results.every((result) => !result.isError);
}
async function saved(id: string) {
  if (isNew)
    await navigateTo(
      valueMode
        ? `/options/${props.definition}/values/${id}`
        : `/options/${id}`,
    );
}
const title = computed(() =>
  isNew
    ? valueMode
      ? "Crear valor"
      : "Crear característica"
    : (query.data.value?.record?.name ?? "Catálogo de opciones"),
);
useHead(() => ({ title: `${title.value} · RRII-Coach` }));
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton
      :to="valueMode ? `/options/${definition}` : '/options'"
      color="neutral"
      variant="soft"
      >{{
        valueMode ? "Volver a la característica" : "Opciones y valores"
      }}</UButton
    >
    <h1>{{ title }}</h1>
    <p v-if="query.data.value?.parent">
      Característica: {{ query.data.value.parent.name }} ·
      {{ query.data.value.parent.active ? "Activa" : "Inactiva" }}
    </p>
    <UButton color="neutral" variant="soft" @click="refresh"
      >Consultar registros actuales</UButton
    >
    <p v-if="query.isPending.value" role="status">Cargando registro…</p>
    <p v-if="query.error.value || review.error.value" role="alert">
      {{ errorMessage(query.error.value || review.error.value) }}
    </p>
    <section
      v-if="query.data.value?.record"
      class="asset-panel"
      aria-label="Datos guardados"
    >
      <p>
        {{ query.data.value.record.name }} ·
        {{ query.data.value.record.active ? "Activo" : "Inactivo" }}
      </p>
      <p>{{ query.data.value.record.description }}</p>
      <template v-if="'family_id' in query.data.value.record"
        ><p>
          Familia: {{ query.data.value.record.family_id ?? "Sin vínculo" }}
        </p>
        <p>Insumo: {{ query.data.value.record.supply_id ?? "Sin vínculo" }}</p>
        <NuxtLink
          v-if="query.data.value.record.supply_id"
          :to="`/inventory/supplies/${query.data.value.record.supply_id}`"
          >Ver insumo</NuxtLink
        ></template
      >
    </section>
    <OptionEditor
      v-if="query.data.value"
      :record="query.data.value.record"
      :definition="valueMode ? definition : undefined"
      :refresh="refresh"
      @saved="saved"
    />
    <OptionList
      v-if="!valueMode && !isNew && query.data.value?.record"
      :definition="definition"
    />
    <section v-if="isNew" class="asset-panel">
      <h2>Registros actuales para revisar el resultado</h2>
      <ul>
        <li v-for="row in review.data.value" :key="row.id">
          <NuxtLink
            :to="
              valueMode
                ? `/options/${definition}/values/${row.id}`
                : `/options/${row.id}`
            "
            >{{ row.name }}</NuxtLink
          >
          · {{ row.id }}
        </li>
      </ul>
    </section>
  </div>
</template>
