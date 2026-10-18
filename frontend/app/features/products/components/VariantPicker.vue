<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import type { ProductApi, Schema } from "../api";
import { errorMessage } from "~/features/shared/http";
import { productMessages as p } from "~/i18n/products";
const model = defineModel<string | null | undefined>({ required: true });
const props = defineProps<{
  api: ProductApi;
  products: Schema["ProductRead"][];
  optional?: boolean;
  label: string;
}>();
const product = ref("");
const selected = useQuery({
  queryKey: computed(() => ["variant", model.value]),
  queryFn: () => props.api.variant(model.value!),
  enabled: computed(() => !!model.value),
  retry: false,
});
watch(
  selected.data,
  (row) => {
    if (row && row.id === model.value) product.value = row.product_id;
  },
  { immediate: true },
);
const variants = useQuery({
  queryKey: computed(() => ["product-variants", product.value]),
  queryFn: () => props.api.variants(product.value),
  enabled: computed(() => !!product.value),
  retry: false,
});
function changeProduct() {
  model.value = null;
}
</script>
<template>
  <div class="catalog-row">
    <label
      >{{ p.inputProduct
      }}<select v-model="product" @change="changeProduct">
        <option value="">{{ p.choose }}</option>
        <option v-for="row in products" :key="row.id" :value="row.id">
          {{ row.name }}
        </option>
      </select></label
    ><label
      >{{ label
      }}<select v-model="model" :required="!optional">
        <option :value="null">{{ optional ? p.none : p.choose }}</option>
        <option
          v-if="model && !variants.data.value?.some((row) => row.id === model)"
          :value="model"
        >
          {{ selected.data.value?.name || model }}
        </option>
        <option
          v-for="row in variants.data.value"
          :key="row.id"
          :value="row.id"
        >
          {{ row.name }} ({{ row.base_unit }})
        </option>
      </select></label
    >
    <div v-if="variants.error.value || selected.error.value" role="alert">
      {{ errorMessage(variants.error.value || selected.error.value)
      }}<UButton
        color="neutral"
        variant="soft"
        @click="
          variants.refetch();
          selected.refetch();
        "
        >{{ p.retry }}</UButton
      >
    </div>
  </div>
</template>
