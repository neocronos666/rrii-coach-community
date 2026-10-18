<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { assetApi } from "~/features/assets/api";
import type { Schema } from "./api";
import { errorMessage } from "~/features/shared/http";
const props = defineProps<{ assets: Schema["AssetRead"][] }>();
const row = defineModel<Schema["ComponentInput"]>({ required: true });
const api = assetApi(useRuntimeConfig().public.apiBaseUrl);
const revisions = useQuery({
  queryKey: computed(() => [
    "composition-child-revisions",
    row.value.child_asset_id,
  ]),
  queryFn: () => api.revisions(row.value.child_asset_id),
  enabled: computed(() => !!row.value.child_asset_id),
  retry: false,
});
</script>
<template>
  <div class="asset-form">
    <label
      >Asset hijo<select
        v-model="row.child_asset_id"
        required
        @change="row.child_revision_id = ''"
      >
        <option value="">Elegir Asset</option>
        <option v-for="asset in props.assets" :key="asset.id" :value="asset.id">
          {{ asset.code }} · {{ asset.name
          }}{{ asset.archived ? " · Archivado" : "" }}
        </option>
      </select></label
    ><label
      >Revisión hija<select v-model="row.child_revision_id" required>
        <option value="">Elegir revisión</option>
        <option
          v-if="
            row.child_revision_id &&
            !revisions.data.value?.some((r) => r.id === row.child_revision_id)
          "
          :value="row.child_revision_id"
        >
          {{ row.child_revision_id }}
        </option>
        <option
          v-for="revision in revisions.data.value"
          :key="revision.id"
          :value="revision.id"
        >
          {{ revision.number }} · {{ revision.note }}
        </option>
      </select></label
    >
    <p v-if="revisions.error.value" role="alert">
      {{ errorMessage(revisions.error.value) }}
    </p>
    <UButton v-if="revisions.error.value" @click="revisions.refetch()"
      >Reintentar revisiones</UButton
    ><label
      >Cantidad del componente<input
        v-model="row.quantity"
        required
        inputmode="decimal"
    /></label>
  </div>
</template>
