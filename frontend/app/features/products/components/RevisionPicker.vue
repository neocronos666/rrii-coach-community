<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import type { ProductApi, Schema } from "../api";
import { errorMessage } from "~/features/shared/http";
import { productMessages as p } from "~/i18n/products";
const model = defineModel<string>({ required: true });
const props = defineProps<{
  api: ProductApi;
  assets: Schema["AssetRead"][];
  assetHint?: string;
}>();
const asset = ref(props.assetHint || "");
const query = useQuery({
  queryKey: computed(() => ["asset-revisions", asset.value]),
  queryFn: () => props.api.revisions(asset.value),
  enabled: computed(() => !!asset.value),
  retry: false,
});
</script>
<template>
  <div class="catalog-row">
    <label
      >{{ p.asset
      }}<select v-model="asset" @change="model = ''" required>
        <option value="">{{ p.choose }}</option>
        <option v-for="row in assets" :key="row.id" :value="row.id">
          {{ row.name }}
        </option>
      </select></label
    ><label
      >{{ p.revision
      }}<select v-model="model" required>
        <option value="">{{ p.choose }}</option>
        <option
          v-if="model && !query.data.value?.some((row) => row.id === model)"
          :value="model"
        >
          {{ model }}
        </option>
        <option v-for="row in query.data.value" :key="row.id" :value="row.id">
          {{ row.number }} · {{ row.note }}
        </option>
      </select></label
    >
    <div v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value)
      }}<UButton @click="query.refetch()">{{ p.retry }}</UButton>
    </div>
  </div>
</template>
