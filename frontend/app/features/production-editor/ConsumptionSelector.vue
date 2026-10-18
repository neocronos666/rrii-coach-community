<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { productApi } from "../products/api";
import { errorMessage } from "../shared/http";
const emit = defineEmits<{ supply: [id: string]; variant: [id: string] }>();
const api = productApi(useRuntimeConfig().public.apiBaseUrl),
  supply = ref(""),
  product = ref(""),
  variant = ref("");
const query = useQuery({
  queryKey: ["manual-consumption-catalog"],
  queryFn: async () => ({
    supplies: await api.supplies(),
    products: await api.products(),
  }),
  retry: false,
});
const variants = useQuery({
  queryKey: computed(() => ["manual-consumption-variants", product.value]),
  enabled: computed(() => !!product.value),
  queryFn: () => api.variants(product.value),
  retry: false,
});
watch(product, () => {
  variant.value = "";
});
</script>
<template>
  <section class="asset-panel asset-form">
    <h5>Agregar consumos reales</h5>
    <p>
      Seleccioná los insumos y componentes realmente utilizados. Las cantidades
      se expresan en su unidad base.
    </p>
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <UButton v-if="query.error.value" @click="query.refetch()"
      >Reintentar catálogos</UButton
    >
    <label
      >Insumo consumido<select v-model="supply">
        <option value="">Elegir insumo</option>
        <option
          v-for="row in query.data.value?.supplies"
          :key="row.id"
          :value="row.id"
        >
          {{ row.name }} · {{ row.base_unit }}
        </option>
      </select></label
    ><UButton :disabled="!supply" @click="emit('supply', supply)"
      >Agregar consumo de insumo</UButton
    >
    <label
      >Producto consumido<select v-model="product">
        <option value="">Elegir producto</option>
        <option
          v-for="row in query.data.value?.products"
          :key="row.id"
          :value="row.id"
        >
          {{ row.name }}
        </option>
      </select></label
    >
    <p v-if="variants.error.value" role="alert">
      {{ errorMessage(variants.error.value) }}
    </p>
    <label v-if="product"
      >Variante consumida<select v-model="variant">
        <option value="">Elegir variante</option>
        <option
          v-for="row in variants.data.value"
          :key="row.id"
          :value="row.id"
        >
          {{ row.name }} · {{ row.base_unit }}
        </option>
      </select></label
    ><UButton :disabled="!variant" @click="emit('variant', variant)"
      >Agregar consumo de componente</UButton
    >
  </section>
</template>
