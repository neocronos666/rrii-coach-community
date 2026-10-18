<script setup lang="ts">
import { taskEditorApi, type Schema } from "./api";
import { productionApi } from "../production/api";
import { useRecordedWrite } from "../inventory/useRecordedWrite";
import WriteStatus from "../inventory/WriteStatus.vue";
const props = defineProps<{
  task: Schema["ProductionTaskRead"];
  refresh: () => Promise<void>;
}>();
const base = useRuntimeConfig().public.apiBaseUrl,
  api = taskEditorApi(base),
  production = productionApi(base),
  confirmed = ref(false);
const state = useRecordedWrite(`legacy-task:${props.task.id}`, async () => {
  await props.refresh();
  await production.task(props.task.id);
  return true;
});
async function action(
  value: "start" | "pause" | "resume" | "finish" | "cancel",
) {
  if (!confirmed.value) return;
  const row = await state.run(`${value} · ${props.task.code}`, () =>
    value === "start" || value === "finish"
      ? api.legacy(props.task.id, value)
      : production.action(props.task.id, value),
  );
  if (row) confirmed.value = false;
}
</script>
<template>
  <section class="asset-panel asset-form">
    <h2>Operación de tarea histórica</h2>
    <p>
      La finalización confirma el fin físico; no cierra el pedido ni registra
      una ejecución nueva.
    </p>
    <WriteStatus :state="state" />
    <fieldset
      v-if="['queued', 'in_progress', 'paused'].includes(task.status)"
      :disabled="state.locked.value"
    >
      <label class="catalog-check"
        ><input v-model="confirmed" type="checkbox" />Confirmo el cambio de
        estado de la tarea histórica.</label
      >
      <UButton
        v-if="task.status === 'queued'"
        :disabled="!confirmed"
        @click="action('start')"
        >Iniciar tarea histórica</UButton
      >
      <UButton
        v-if="task.status === 'in_progress'"
        :disabled="!confirmed"
        @click="action('pause')"
        >Pausar tarea histórica</UButton
      >
      <UButton
        v-if="task.status === 'paused'"
        :disabled="!confirmed"
        @click="action('resume')"
        >Reanudar tarea histórica</UButton
      >
      <UButton
        v-if="task.status === 'in_progress'"
        :disabled="!confirmed"
        @click="action('finish')"
        >Finalizar físicamente</UButton
      >
      <UButton :disabled="!confirmed" @click="action('cancel')"
        >Cancelar tarea histórica</UButton
      >
    </fieldset>
  </section>
</template>
