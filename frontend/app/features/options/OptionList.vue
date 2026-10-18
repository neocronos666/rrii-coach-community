<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { optionsApi } from "./api";
import { errorMessage } from "~/features/shared/http";
const props = defineProps<{ definition?: string }>();
const api = optionsApi(useRuntimeConfig().public.apiBaseUrl);
const search = ref(""),
  active = ref(""),
  applied = ref({ search: "", active: "" });
const query = useQuery({
  queryKey: computed(() => [
    "options-list",
    props.definition ?? "",
    applied.value,
  ]),
  queryFn: () => {
    const enabled =
      applied.value.active === "" ? undefined : applied.value.active === "true";
    return props.definition
      ? api.values(props.definition, enabled, applied.value.search || undefined)
      : api.definitions(enabled, applied.value.search || undefined);
  },
  retry: false,
});
const root = computed(() =>
  props.definition ? `/options/${props.definition}/values` : "/options",
);
</script>
<template>
  <section
    class="asset-form"
    :aria-label="
      definition
        ? 'Valores de la característica'
        : 'Catálogo de características'
    "
  >
    <h2>
      {{
        definition
          ? "Valores de la característica"
          : "Características reutilizables"
      }}
    </h2>
    <UButton :to="`${root}/new`">{{
      definition ? "Crear valor" : "Crear característica"
    }}</UButton>
    <form
      class="asset-panel asset-form"
      @submit.prevent="applied = { search, active }"
    >
      <label>Buscar por nombre<input v-model="search" maxlength="255" /></label>
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
    <p v-if="query.isPending.value" role="status">Cargando catálogo…</p>
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <p v-if="query.data.value?.length === 0">
      No hay registros para estos filtros.
    </p>
    <ul class="asset-form">
      <li v-for="row in query.data.value" :key="row.id" class="asset-panel">
        <NuxtLink :to="`${root}/${row.id}`">{{ row.name }}</NuxtLink> ·
        {{ row.active ? "Activo" : "Inactivo" }}
        <p>{{ row.description }}</p>
      </li>
    </ul>
  </section>
</template>
