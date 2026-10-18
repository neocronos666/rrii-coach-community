<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { assetApi } from "~/features/assets/api";
import { structureApi } from "~/features/asset-structure/api";
import { detailsApi } from "~/features/asset-details/api";
import { textFields } from "~/features/asset-details/fields";
import MetadataEditor from "~/features/asset-details/MetadataEditor.vue";
import { provideDraftGuard } from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
definePageMeta({ key: (route) => route.path });
const id = String(useRoute().params.id),
  base = useRuntimeConfig().public.apiBaseUrl;
const query = useQuery({
  queryKey: ["asset-metadata", id],
  retry: false,
  queryFn: async () => {
    const [asset, categories, families] = await Promise.all([
      assetApi(base).get(id),
      detailsApi(base).categories(),
      structureApi(base).families(),
    ]);
    return { asset, categories, families };
  },
});
provideDraftGuard("Hay datos del Asset sin guardar. ¿Salir?");
async function refresh() {
  return !(await query.refetch()).isError;
}
useHead(() => ({
  title: `Datos · ${query.data.value?.asset.name ?? "Asset"} · RRII-Coach`,
}));
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton :to="`/assets/${id}`" color="neutral" variant="soft"
      >Volver al Asset</UButton
    >
    <h1>Datos · {{ query.data.value?.asset.name ?? "Asset" }}</h1>
    <UButton color="neutral" variant="soft" @click="refresh"
      >Consultar datos guardados</UButton
    >
    <p v-if="query.isPending.value" role="status">Cargando datos…</p>
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <template v-if="query.data.value"
      ><details class="asset-panel">
        <summary>Datos guardados</summary>
        <dl>
          <template v-for="field in textFields" :key="field.key"
            ><dt>{{ field.label }}</dt>
            <dd>
              {{ query.data.value.asset[field.key] ?? "Sin definir" }}
            </dd></template
          >
          <dt>Categoría</dt>
          <dd>
            {{
              query.data.value.categories.find(
                (row) => row.id === query.data.value!.asset.category_id,
              )?.name ?? query.data.value.asset.category_id
            }}
          </dd>
          <dt>Familia</dt>
          <dd>
            {{
              query.data.value.families.find(
                (row) => row.id === query.data.value!.asset.family_id,
              )?.name ??
              query.data.value.asset.family_id ??
              "Sin familia"
            }}
          </dd>
          <dt>Terceros</dt>
          <dd>{{ query.data.value.asset.third_party ? "Sí" : "No" }}</dd>
          <dt>Archivado</dt>
          <dd>{{ query.data.value.asset.archived ? "Sí" : "No" }}</dd>
        </dl>
      </details>
      <MetadataEditor
        :asset="query.data.value.asset"
        :categories="query.data.value.categories"
        :families="query.data.value.families"
        :refresh="refresh"
    /></template>
  </div>
</template>
