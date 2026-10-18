<script setup lang="ts">
import { machinesApi, type Schema } from "./api";
import { machineTypes, optionalFields, machineChanges } from "./fields";
import { useRecordedWrite } from "~/features/inventory/useRecordedWrite";
import WriteStatus from "~/features/inventory/WriteStatus.vue";
import { useDraftGuard } from "~/features/shared/useDraftGuard";
const props = defineProps<{
  machine?: Schema["MachineRead"];
  refresh: () => Promise<boolean>;
}>();
const emit = defineEmits<{ saved: [id: string] }>();
const api = machinesApi(useRuntimeConfig().public.apiBaseUrl);
const body = ref<Schema["MachineCreate"]>({
  name: props.machine?.name ?? "",
  machine_type: props.machine?.machine_type ?? "fdm_printer",
  manufacturer: props.machine?.manufacturer ?? null,
  model: props.machine?.model ?? null,
  purchase_date: props.machine?.purchase_date ?? null,
  purchase_price: props.machine?.purchase_price ?? null,
  currency: props.machine?.currency ?? null,
  rated_power_w: props.machine?.rated_power_w ?? null,
  useful_life_hours: props.machine?.useful_life_hours ?? null,
  active: props.machine?.active ?? true,
  notes: props.machine?.notes ?? null,
});
const original = structuredClone(toRaw(body.value));
const state = useRecordedWrite(
  `machine:${props.machine?.id ?? "new"}`,
  props.refresh,
);
const confirmed = ref(false),
  markSaved = useDraftGuard("machine", () => body.value);
async function save() {
  if (!confirmed.value) return;
  const payload = { ...body.value };
  for (const { key } of optionalFields)
    if (payload[key] === "") payload[key] = null;
  payload.notes ||= null;
  // Alta: null permite usar la moneda de instalación. PATCH no permite null.
  if (!props.machine) payload.currency ||= null;
  const result = await state.run(
    `${payload.name} · ${payload.active ? "Activa" : "Inactiva"}`,
    () =>
      props.machine
        ? api.update(props.machine.id, machineChanges(payload, original))
        : api.create(payload),
  );
  if (result) {
    Object.assign(original, payload);
    markSaved();
    confirmed.value = false;
    emit("saved", result.id);
  }
}
</script>
<template>
  <section class="asset-panel asset-form">
    <h2>{{ machine ? "Editar máquina" : "Registrar máquina" }}</h2>
    <p>
      Community admite dos máquinas activas. El servidor valida el límite al
      crear o reactivar. Desactivar conserva el historial.
    </p>
    <p>
      Potencia y vida útil son estimaciones, no mediciones. Dejá vacíos los
      datos desconocidos; no se reemplazan por cero ni recalculan presupuestos
      históricos.
    </p>
    <WriteStatus :state="state" />
    <form class="asset-form" @submit.prevent="save">
      <fieldset :disabled="state.locked.value">
        <label
          >Nombre<input v-model="body.name" required maxlength="255"
        /></label>
        <label
          >Tipo<select v-model="body.machine_type">
            <option
              v-for="(label, value) in machineTypes"
              :key="value"
              :value="value"
            >
              {{ label }}
            </option>
          </select></label
        >
        <label v-for="field in optionalFields" :key="field.key"
          >{{ field.label
          }}<input
            v-model="body[field.key]"
            :type="field.type"
            :maxlength="field.type === 'text' ? 255 : undefined"
        /></label>
        <label
          >Moneda<input
            v-model="body.currency"
            :required="!!machine"
            minlength="3"
            maxlength="3"
        /></label>
        <p v-if="!machine">
          Sin moneda indicada, el servidor utiliza la moneda de instalación.
        </p>
        <label>Notas<textarea v-model="body.notes" /></label>
        <label class="catalog-check"
          ><input v-model="body.active" type="checkbox" />Activa</label
        >
        <label class="catalog-check"
          ><input v-model="confirmed" required type="checkbox" />Confirmo los
          datos y el estado de la máquina.</label
        >
        <UButton type="submit">Guardar máquina</UButton>
      </fieldset>
    </form>
  </section>
</template>
