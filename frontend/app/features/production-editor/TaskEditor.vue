<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { taskEditorApi, type Schema } from "./api";
import { taskDraft, taskChanges, parameters } from "./fields";
import type { Destination } from "../production/api";
import { testPrintApi } from "../test-prints/api";
import { productApi } from "../products/api";
import { useRecordedWrite } from "../inventory/useRecordedWrite";
import WriteStatus from "../inventory/WriteStatus.vue";
import { useDraftGuard } from "../shared/useDraftGuard";
import { errorMessage } from "../shared/http";
const props = defineProps<{
  task?: Schema["ProductionTaskRead"];
  destination?: Destination;
  refresh: () => Promise<boolean>;
}>();
const base = useRuntimeConfig().public.apiBaseUrl,
  api = taskEditorApi(base),
  products = productApi(base);
const refs = useQuery({
  queryKey: ["task-editor-references"],
  queryFn: async () => ({
    machines: await testPrintApi(base).machines(),
    products: await products.products(),
  }),
  retry: false,
});
const product = ref(""),
  output = ref<string | null>(null);
const variants = useQuery({
  queryKey: computed(() => ["task-editor-variants", product.value]),
  queryFn: () => products.variants(product.value),
  enabled: computed(() => !!product.value),
  retry: false,
});
watch(product, () => {
  output.value = null;
});
const body = ref(taskDraft(props.task));
let original = taskDraft(props.task);
const taskType = ref<Schema["ProductionTaskType"]>("manual"),
  unit = ref("unit"),
  confirmed = ref(false),
  error = ref("");
const state = useRecordedWrite(
  `task-editor:${props.task?.id ?? props.destination?.id ?? "new"}`,
  props.refresh,
);
const markSaved = useDraftGuard("task-editor", () => [
  body.value,
  taskType.value,
  unit.value,
  output.value,
]);
const terminal = computed(
  () =>
    !!props.task &&
    ["cancelled", "physically_completed"].includes(props.task.status),
);
const planning = computed(
  () => !props.task || ["queued", "paused"].includes(props.task.status),
);
const quantity = computed(
  () =>
    !props.task ||
    (props.task.status === "queued" && props.task.origin !== "recipe"),
);
async function save() {
  if (!confirmed.value || terminal.value) return;
  error.value = "";
  let patch: Schema["ProductionTaskUpdate"];
  try {
    patch = taskChanges(body.value, original);
    parameters(body.value.production_parameters);
  } catch (e) {
    error.value = errorMessage(e);
    return;
  }
  const row = await state.run(body.value.title, () =>
    props.task
      ? api.update(props.task.id, patch)
      : api.create(props.destination!, {
          ...body.value,
          description: body.value.description || null,
          notes: body.value.notes || null,
          production_parameters: parameters(body.value.production_parameters),
          task_type: taskType.value,
          planned_unit: unit.value || null,
          output_variant_id: output.value,
        }),
  );
  if (row) {
    body.value = taskDraft(row);
    original = taskDraft(row);
    markSaved();
    confirmed.value = false;
    await navigateTo(`/production/tasks/${row.id}`);
  }
}
</script>
<template>
  <section class="asset-form">
    <WriteStatus :state="state" />
    <p v-if="error" role="alert">{{ error }}</p>
    <p v-if="refs.error.value" role="alert">
      {{ errorMessage(refs.error.value) }}
    </p>
    <UButton v-if="refs.error.value" @click="refs.refetch()"
      >Reintentar catálogos</UButton
    >
    <p v-if="terminal">La tarea está cerrada y no admite edición.</p>
    <form v-else class="asset-form" @submit.prevent="save">
      <fieldset :disabled="state.locked.value">
        <fieldset :disabled="!planning">
          <label
            >Título de tarea<input
              v-model="body.title"
              required
              maxlength="255"
          /></label>
          <label>Descripción<textarea v-model="body.description" /></label>
          <label
            >Prioridad<select v-model="body.priority">
              <option value="low">Baja</option>
              <option value="normal">Normal</option>
              <option value="high">Alta</option>
              <option value="urgent">Urgente</option>
            </select></label
          >
          <label
            >Posición de cola<input
              v-model.number="body.queue_position"
              type="number"
              required
              min="0"
              step="1"
          /></label>
          <label
            >Máquina asignada<select v-model="body.machine_id">
              <option :value="null">Sin máquina</option>
              <option
                v-if="
                  body.machine_id &&
                  !refs.data.value?.machines.some(
                    (row) => row.id === body.machine_id,
                  )
                "
                :value="body.machine_id"
              >
                Asignación actual · {{ body.machine_id }}
              </option>
              <option
                v-for="machine in refs.data.value?.machines"
                :key="machine.id"
                :value="machine.id"
              >
                {{ machine.name }}
              </option>
            </select></label
          >
        </fieldset>
        <label
          >Cantidad planificada<input
            v-model="body.planned_quantity"
            :disabled="!quantity"
            inputmode="decimal"
            required
        /></label>
        <template v-if="!task">
          <label
            >Tipo de tarea<select v-model="taskType">
              <option value="manual">Manual</option>
              <option value="fdm_print">Impresión FDM</option>
              <option value="sla_print">Impresión SLA</option>
              <option value="cnc">CNC</option>
              <option value="laser">Láser</option>
              <option value="postprocessing">Posprocesado</option>
              <option value="assembly">Ensamblado</option>
              <option value="other">Otro</option>
            </select></label
          >
          <label
            >Unidad planificada<input v-model="unit" maxlength="30"
          /></label>
          <label
            >Producto de salida (opcional)<select v-model="product">
              <option value="">Sin producto</option>
              <option
                v-for="row in refs.data.value?.products"
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
            >Variante de salida<select v-model="output">
              <option :value="null">Sin salida a stock</option>
              <option
                v-for="row in variants.data.value"
                :key="row.id"
                :value="row.id"
              >
                {{ row.name }} · {{ row.base_unit }}
              </option>
            </select></label
          >
          <p>
            Si elegís salida, indicá su unidad base. El cierre de ejecuciones
            registra las unidades buenas en stock según las reglas del servidor.
          </p>
        </template>
        <label>Notas operativas<textarea v-model="body.notes" /></label>
        <label
          >Parámetros técnicos (objeto JSON)<textarea
            v-model="body.production_parameters"
            rows="5"
          />
        </label>
        <p>No incluyas secretos en los parámetros.</p>
        <label class="catalog-check"
          ><input v-model="confirmed" required type="checkbox" />Confirmo la
          planificación de la tarea.</label
        >
        <UButton type="submit">{{
          task ? "Guardar tarea" : "Crear tarea manual"
        }}</UButton>
      </fieldset>
    </form>
  </section>
</template>
