<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { assetApi } from "~/features/assets/api";
import { structureApi } from "~/features/asset-structure/api";
import RelationsEditor from "~/features/asset-structure/RelationsEditor.vue";
import CompositionEditor from "~/features/asset-structure/CompositionEditor.vue";
import { provideDraftGuard } from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
definePageMeta({ key: (route) => route.fullPath });
const route = useRoute(),
  id = String(route.params.id),
  requested =
    typeof route.query.revision === "string" ? route.query.revision : undefined;
const base = useRuntimeConfig().public.apiBaseUrl,
  assets = assetApi(base),
  api = structureApi(base);
let pinned = requested;
const registry = provideDraftGuard(
  "Hay cambios de estructura sin publicar. ¿Salir?",
);
onBeforeRouteUpdate(
  () =>
    ![...registry.values()].some(Boolean) ||
    window.confirm(
      "Hay cambios de estructura sin publicar. ¿Cambiar de revisión?",
    ),
);
const query = useQuery({
  queryKey: ["asset-structure", id, requested ?? "current"],
  retry: false,
  queryFn: async () => {
    const [asset, revisions, families, allAssets, relations] =
      await Promise.all([
        assets.get(id),
        assets.revisions(id),
        api.families(),
        api.assets(),
        api.compatibilities(id),
      ]);
    const selected = pinned ?? asset.current_revision_id;
    pinned = selected;
    const revision = revisions.find((row) => row.id === selected);
    if (!revision) throw new Error("La revisión no pertenece al Asset.");
    const [components, updates] = await Promise.all([
      api.composition(id, selected),
      api.updates(id, selected),
    ]);
    return {
      asset,
      revision,
      components,
      updates,
      families,
      allAssets,
      relations,
    };
  },
});
async function refresh() {
  return !(await query.refetch()).isError;
}
useHead(() => ({
  title: `Estructura · ${query.data.value?.asset.name ?? "Asset"} · RRII-Coach`,
}));
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton :to="`/assets/${id}`" color="neutral" variant="soft"
      >Volver al Asset</UButton
    >
    <h1>Estructura · {{ query.data.value?.asset.name ?? "Asset" }}</h1>
    <UButton color="neutral" variant="soft" @click="refresh"
      >Consultar registros actuales</UButton
    >
    <p v-if="query.isPending.value" role="status">Cargando estructura…</p>
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <template v-if="query.data.value"
      ><UButton
        v-if="
          query.data.value.revision.id !==
          query.data.value.asset.current_revision_id
        "
        :to="`/asset-structure/${id}?revision=${query.data.value.asset.current_revision_id}`"
        >Abrir revisión actual</UButton
      ><RelationsEditor
        :asset="query.data.value.asset"
        :families="query.data.value.families"
        :assets="query.data.value.allAssets"
        :relations="query.data.value.relations"
        :refresh="refresh" /><CompositionEditor
        :key="query.data.value.revision.id"
        :asset="query.data.value.asset"
        :revision="query.data.value.revision"
        :components="query.data.value.components"
        :updates="query.data.value.updates"
        :assets="query.data.value.allAssets"
        :refresh="refresh"
    /></template>
  </div>
</template>
