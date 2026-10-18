<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { compositionApi, type Schema } from "~/features/quote-composition/api";
import CalculationView from "~/features/quote-composition/CalculationView.vue";
import { productApi } from "~/features/products/api";
import { testPrintApi } from "~/features/test-prints/api";
import { useRecordedWrite } from "~/features/inventory/useRecordedWrite";
import WriteStatus from "~/features/inventory/WriteStatus.vue";
import {
  provideDraftGuard,
  useDraftGuard,
} from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
const base = useRuntimeConfig().public.apiBaseUrl,
  api = compositionApi(base);
const references = useQuery({
  queryKey: ["calculation-references"],
  queryFn: async () => ({
    supplies: await productApi(base).supplies(),
    machines: await testPrintApi(base).machines(),
  }),
  retry: false,
});
const body = ref<Schema["CostCalculationRequest"]>({
  machine_id: null,
  machine_duration_minutes: null,
  energy_kwh: null,
  supplies: [],
  labor: [],
  extras: [],
});
const registry = provideDraftGuard("Hay un cálculo sin guardar. ¿Salir?");
const markSaved = useDraftGuard("calculation-new", () => body.value, registry);
const calculation = shallowRef<Schema["CostCalculationRead"]>(),
  confirmed = ref(false);
// No existe listado ni clave idempotente de cálculos. Una respuesta perdida
// no permite determinar qué snapshot se creó: nunca habilitar reenvío automático.
const state = useRecordedWrite(
  "calculation-new",
  async () => !!calculation.value,
);
const laborTypes: { value: Schema["LaborType"]; label: string }[] = [
  { value: "design", label: "Diseño" },
  { value: "preproduction", label: "Preproducción" },
  { value: "postproduction", label: "Posproducción" },
  { value: "assembly", label: "Ensamblado" },
  { value: "support", label: "Soporte" },
  { value: "training", label: "Capacitación" },
  { value: "pretransport", label: "Pretransporte" },
];
async function save() {
  if (!confirmed.value) return;
  const row = await state.run("Nuevo cálculo técnico", () =>
    api.calculate({
      ...body.value,
      machine_duration_minutes: body.value.machine_duration_minutes || null,
      energy_kwh: body.value.energy_kwh || null,
    }),
  );
  if (row) {
    calculation.value = row;
    markSaved();
    confirmed.value = false;
  }
}
useHead({ title: "Crear cálculo técnico · RRII-Coach" });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <NuxtLink to="/quotes">Presupuestos</NuxtLink>
    <h1>Crear cálculo técnico</h1>
    <p>
      Guardá un snapshot de costos para seleccionarlo después por su
      identificador. Los importes y fuentes se resuelven en el servidor; no se
      consume ni reserva stock. Cada cálculo representa una unidad comercial
      completa.
    </p>
    <WriteStatus :state="state" />
    <p v-if="state.review.value && !state.busy.value" role="status">
      Si se perdió la respuesta no es posible localizar automáticamente el
      cálculo: la API no ofrece listado. No vuelvas a enviar esta operación sin
      comprobar su resultado.
    </p>
    <p v-if="references.error.value" role="alert">
      {{ errorMessage(references.error.value) }}
    </p>
    <UButton v-if="references.error.value" @click="references.refetch()"
      >Reintentar catálogos</UButton
    >
    <form class="asset-form" @submit.prevent="save">
      <fieldset :disabled="state.locked.value || !!calculation">
        <label
          >Máquina<select v-model="body.machine_id">
            <option :value="null">Sin máquina</option>
            <option
              v-for="machine in references.data.value?.machines"
              :key="machine.id"
              :value="machine.id"
            >
              {{ machine.name }}
            </option>
          </select></label
        >
        <label
          >Duración de máquina (minutos)<input
            v-model.number="body.machine_duration_minutes"
            type="number"
            min="1"
            step="1"
        /></label>
        <label
          >Energía (kWh)<input v-model="body.energy_kwh" inputmode="decimal"
        /></label>
        <h2>Insumos</h2>
        <section
          v-for="(supply, index) in body.supplies"
          :key="index"
          class="asset-panel asset-form"
        >
          <label
            >Insumo<select v-model="supply.supply_id" required>
              <option
                v-for="row in references.data.value?.supplies"
                :key="row.id"
                :value="row.id"
              >
                {{ row.name }} · {{ row.base_unit }}
              </option>
            </select></label
          >
          <label
            >Cantidad de insumo<input
              v-model="supply.quantity"
              required
              inputmode="decimal"
          /></label>
          <label
            >Unidad<select v-model="supply.unit">
              <option
                v-for="unit in [
                  'g',
                  'kg',
                  'ml',
                  'l',
                  'mm',
                  'cm',
                  'm',
                  'm2',
                  'm3',
                  'unit',
                ]"
                :key="unit"
                :value="unit"
              >
                {{ unit }}
              </option>
            </select></label
          >
          <UButton @click="body.supplies?.splice(index, 1)"
            >Quitar insumo</UButton
          >
        </section>
        <UButton
          @click="
            body.supplies?.push({ supply_id: '', quantity: '1', unit: 'unit' })
          "
          >Agregar insumo</UButton
        >
        <h2>Trabajo</h2>
        <section
          v-for="(labor, index) in body.labor"
          :key="index"
          class="asset-panel asset-form"
        >
          <label
            >Tipo de trabajo<select v-model="labor.labor_type">
              <option
                v-for="type in laborTypes"
                :key="type.value"
                :value="type.value"
              >
                {{ type.label }}
              </option>
            </select></label
          >
          <label
            >Duración del trabajo (minutos)<input
              v-model.number="labor.duration_minutes"
              required
              type="number"
              min="1"
              step="1"
          /></label>
          <UButton @click="body.labor?.splice(index, 1)"
            >Quitar trabajo</UButton
          >
        </section>
        <UButton
          @click="
            body.labor?.push({ labor_type: 'design', duration_minutes: 1 })
          "
          >Agregar trabajo</UButton
        >
        <h2>Extras</h2>
        <section
          v-for="(extra, index) in body.extras"
          :key="index"
          class="asset-panel asset-form"
        >
          <label
            >Descripción del extra<input v-model="extra.description" required
          /></label>
          <label
            >Importe del extra<input
              v-model="extra.amount"
              required
              inputmode="decimal"
          /></label>
          <label
            >Moneda del extra<input
              v-model="extra.currency"
              required
              minlength="3"
              maxlength="3"
          /></label>
          <UButton @click="body.extras?.splice(index, 1)">Quitar extra</UButton>
        </section>
        <UButton
          @click="
            body.extras?.push({ description: '', amount: '', currency: 'ARS' })
          "
          >Agregar extra</UButton
        >
        <label class="catalog-check"
          ><input v-model="confirmed" required type="checkbox" />Confirmo la
          creación del snapshot técnico.</label
        >
        <UButton type="submit">Guardar cálculo técnico</UButton>
      </fieldset>
    </form>
    <CalculationView v-if="calculation" :calculation="calculation" />
    <NuxtLink v-if="calculation" :to="`/calculations/${calculation.id}`"
      >Abrir snapshot permanente</NuxtLink
    >
    <NuxtLink to="/quotes/new">Crear presupuesto con ítems</NuxtLink>
  </div>
</template>
