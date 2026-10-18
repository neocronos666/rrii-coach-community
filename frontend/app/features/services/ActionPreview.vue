<script setup lang="ts">
import { servicesApi, type Schema } from "./api";
import { errorMessage } from "~/features/shared/http";
const props = defineProps<{
  service: Schema["ServiceDefinitionRead"];
  resetKey: number;
}>();
const api = servicesApi(useRuntimeConfig().public.apiBaseUrl);
const labels = {
  piece: "Pieza",
  design: "Diseño",
  product: "Producto",
  quantity: "Cantidad (etiqueta)",
} as const;
const values = reactive({ piece: "", design: "", product: "", quantity: "" });
const result = shallowRef<Schema["ServiceActionPreview"] | null>(null),
  error = ref(""),
  busy = ref(false);
let generation = 0;
function invalidate() {
  generation++;
  result.value = null;
  error.value = "";
  busy.value = false;
}
watch(
  [() => ({ ...values }), () => props.resetKey, () => props.service.updated_at],
  invalidate,
  { deep: true, flush: "sync" },
);
onBeforeUnmount(invalidate);
async function preview() {
  const token = ++generation;
  busy.value = true;
  result.value = null;
  error.value = "";
  try {
    const response = await api.preview(props.service.id, {
      values: Object.fromEntries(
        Object.entries(values).filter(([, value]) => value !== ""),
      ),
    });
    if (token === generation) result.value = response;
  } catch (failure) {
    if (token === generation) error.value = errorMessage(failure);
  } finally {
    if (token === generation) busy.value = false;
  }
}
</script>
<template>
  <section class="asset-panel asset-form" aria-label="Probar frase guardada">
    <h2>Probar frase guardada</h2>
    <p>
      Usa la plantilla guardada, no los cambios del formulario. Estos textos son
      ejemplos de contexto; no crean producción, consumos ni presupuestos. La
      resolución automática según opciones se prueba desde el producto.
    </p>
    <p>Plantilla guardada: {{ service.action_template ?? service.name }}</p>
    <form class="asset-form" @submit.prevent="preview">
      <label v-for="(label, key) in labels" :key="key"
        >{{ label }}<input v-model="values[key]" maxlength="1000"
      /></label>
      <UButton type="submit" :disabled="busy">Previsualizar frase</UButton>
    </form>
    <p v-if="busy" role="status">Consultando frase…</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <section v-if="result" aria-label="Resultado de frase">
      <p>{{ result.action }}</p>
      <p>{{ result.instructions }}</p>
    </section>
  </section>
</template>
