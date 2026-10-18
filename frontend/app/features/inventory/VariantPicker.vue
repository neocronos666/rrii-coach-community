<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { productApi } from "~/features/products/api";
import { errorMessage } from "~/features/shared/http";
import { testPrintMessages as t } from "~/i18n/test-prints";
const variant = defineModel<string>({ required: true });
const product = ref(""),
  api = productApi(useRuntimeConfig().public.apiBaseUrl);
const products = useQuery({
  queryKey: ["inventory-products"],
  queryFn: api.products,
  retry: false,
});
const variants = useQuery({
  queryKey: computed(() => ["inventory-variants", product.value]),
  queryFn: () => api.variants(product.value),
  enabled: computed(() => !!product.value),
  retry: false,
});
watch(
  product,
  () => {
    variant.value = "";
  },
  { flush: "sync" },
);
</script>
<template>
  <div class="asset-form">
    <div v-if="products.error.value || variants.error.value" role="alert">
      {{ errorMessage(products.error.value || variants.error.value)
      }}<UButton
        @click="
          products.refetch();
          variants.refetch();
        "
        >{{ t.retry }}</UButton
      >
    </div>
    <label
      >Producto<select v-model="product" required>
        <option value="">{{ t.choose }}</option>
        <option
          v-for="row in products.data.value"
          :key="row.id"
          :value="row.id"
        >
          {{ row.name }}
        </option>
      </select></label
    >
    <label
      >{{ t.variant
      }}<select v-model="variant" required>
        <option value="">{{ t.choose }}</option>
        <option
          v-for="row in variants.data.value"
          :key="row.id"
          :value="row.id"
        >
          {{ row.name }} · {{ row.base_unit }}
        </option>
      </select></label
    >
  </div>
</template>
