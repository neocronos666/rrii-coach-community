<script setup lang="ts">
import { compositionApi, type Schema } from "./api";
import CalculationView from "./CalculationView.vue";
import { useRecordedWrite } from "~/features/inventory/useRecordedWrite";
import WriteStatus from "~/features/inventory/WriteStatus.vue";
import { useDraftGuard } from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
const props = defineProps<{
  quote?: Schema["QuoteRead"];
  refresh: () => Promise<boolean>;
}>();
const api = compositionApi(useRuntimeConfig().public.apiBaseUrl);
const items = ref(
  (props.quote?.items ?? []).map((item) => ({
    key: crypto.randomUUID(),
    cost_calculation_id: item.cost_calculation_id,
    description: item.description,
    quantity: item.quantity,
    notes: item.notes ?? "",
  })),
);
const title = ref(""),
  lookup = ref(""),
  lookupError = ref(""),
  inspecting = ref(false),
  confirmed = ref(false);
const calculation = shallowRef<Schema["CostCalculationRead"]>();
const state = useRecordedWrite(
  `quote-items:${props.quote?.id ?? "new"}`,
  props.refresh,
);
const markSaved = useDraftGuard("quote-items", () => ({
  title: title.value,
  items: items.value,
}));
const editable = computed(
  () =>
    !props.quote ||
    (props.quote.status === "draft" && !props.quote.source_quick_quote_id),
);
async function inspect() {
  if (inspecting.value) return;
  inspecting.value = true;
  lookupError.value = "";
  calculation.value = undefined;
  const id = lookup.value.trim();
  try {
    const row = await api.calculation(id);
    if (lookup.value.trim() === id) calculation.value = row;
  } catch (e) {
    lookupError.value = errorMessage(e);
  } finally {
    inspecting.value = false;
  }
}
watch(lookup, () => {
  calculation.value = undefined;
});
function add() {
  if (!calculation.value?.complete || calculation.value.multi_currency) return;
  items.value.push({
    key: crypto.randomUUID(),
    cost_calculation_id: calculation.value.id,
    description: "",
    quantity: "1",
    notes: "",
  });
}
async function save() {
  if (!confirmed.value || !editable.value || !items.value.length) return;
  const body = items.value.map(({ key, ...item }) => ({
    ...item,
    notes: item.notes || null,
  }));
  const row = await state.run(props.quote?.code ?? title.value, () =>
    props.quote
      ? api.update(props.quote.id, body)
      : api.create({ title: title.value, items: body }),
  );
  if (row) {
    markSaved();
    await navigateTo(`/quotes/${row.id}`);
  }
}
</script>
<template>
  <section class="asset-form">
    <WriteStatus :state="state" />
    <p v-if="!editable" role="status">
      Los ítems de este presupuesto son inmutables.
    </p>
    <template v-else>
      <p>
        Seleccioná snapshots técnicos guardados. La cantidad multiplica el costo
        técnico del cálculo completo. No se recalculan fuentes ni se reserva
        stock. Los totales se consultan después de guardar.
      </p>
      <NuxtLink to="/calculations/new" target="_blank"
        >Crear cálculo técnico (otra pestaña)</NuxtLink
      >
      <form class="asset-panel asset-form" @submit.prevent="inspect">
        <label
          >Identificador del cálculo<input v-model="lookup" required
        /></label>
        <UButton type="submit" :disabled="inspecting"
          >Consultar cálculo</UButton
        >
      </form>
      <p v-if="lookupError" role="alert">{{ lookupError }}</p>
      <CalculationView v-if="calculation" :calculation="calculation" />
      <UButton
        v-if="calculation"
        :disabled="
          state.locked.value ||
          !calculation.complete ||
          calculation.multi_currency
        "
        @click="add"
        >Agregar cálculo a los ítems</UButton
      >
      <form class="asset-form" @submit.prevent="save">
        <fieldset :disabled="state.locked.value">
          <label v-if="!quote"
            >Título del presupuesto<input
              v-model="title"
              maxlength="255"
              required
          /></label>
          <section
            v-for="(item, index) in items"
            :key="item.key"
            class="asset-panel asset-form"
          >
            <h2>Ítem {{ index + 1 }}</h2>
            <NuxtLink
              :to="`/calculations/${item.cost_calculation_id}`"
              target="_blank"
              >Consultar snapshot técnico</NuxtLink
            >
            <label
              >Descripción del ítem<input
                v-model="item.description"
                required
                maxlength="255"
            /></label>
            <label
              >Cantidad comercial<input
                v-model="item.quantity"
                required
                inputmode="decimal"
            /></label>
            <label>Notas del ítem<textarea v-model="item.notes" /></label>
            <UButton
              color="neutral"
              variant="soft"
              @click="items.splice(index, 1)"
              >Quitar ítem {{ index + 1 }}</UButton
            >
          </section>
          <label class="catalog-check"
            ><input v-model="confirmed" type="checkbox" required />Confirmo los
            ítems y sus cantidades.</label
          >
          <UButton type="submit" :disabled="!items.length">{{
            quote ? "Guardar composición" : "Crear presupuesto"
          }}</UButton>
        </fieldset>
      </form>
    </template>
  </section>
</template>
