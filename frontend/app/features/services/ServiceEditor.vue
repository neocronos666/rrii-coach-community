<script setup lang="ts">
import { servicesApi, type Schema } from "./api";
import { useRecordedWrite } from "~/features/inventory/useRecordedWrite";
import WriteStatus from "~/features/inventory/WriteStatus.vue";
import { useDraftGuard } from "~/features/shared/useDraftGuard";
const props = defineProps<{
  service?: Schema["ServiceDefinitionRead"];
  refresh: () => Promise<boolean>;
}>();
const emit = defineEmits<{ saved: [id: string]; changed: [] }>();
const api = servicesApi(useRuntimeConfig().public.apiBaseUrl);
const body = ref<Schema["ServiceDefinitionCreate"]>({
  name: props.service?.name ?? "",
  instructions: props.service?.instructions ?? null,
  action_template: props.service?.action_template ?? null,
  active: props.service?.active ?? true,
});
const original = structuredClone(toRaw(body.value));
const state = useRecordedWrite(
  `service:${props.service?.id ?? "new"}`,
  props.refresh,
);
const confirmed = ref(false),
  markSaved = useDraftGuard("service", () => body.value);
watch(body, () => emit("changed"), { deep: true, flush: "sync" });
async function save() {
  if (!confirmed.value) return;
  const payload = {
    ...body.value,
    instructions: body.value.instructions || null,
    action_template: body.value.action_template || null,
  };
  const response = await state.run(payload.name, () =>
    props.service
      ? api.update(
          props.service.id,
          Object.fromEntries(
            Object.entries(payload).filter(
              ([key, value]) =>
                value !== original[key as keyof typeof original],
            ),
          ),
        )
      : api.create(payload),
  );
  if (response) {
    Object.assign(original, payload);
    markSaved();
    confirmed.value = false;
    emit("saved", response.id);
  }
}
</script>
<template>
  <section class="asset-panel asset-form">
    <h2>{{ service ? "Editar servicio" : "Registrar servicio" }}</h2>
    <p>
      Catálogo compartido por recetas. Cambiar o desactivar un servicio no
      reescribe los snapshots históricos. No se elimina su identidad.
    </p>
    <WriteStatus :state="state" />
    <form class="asset-form" @submit.prevent="save">
      <fieldset :disabled="state.locked.value">
        <label
          >Nombre<input v-model="body.name" required maxlength="255"
        /></label>
        <label
          >Instrucciones<textarea
            v-model="body.instructions"
            maxlength="10000"
          />
        </label>
        <label
          >Plantilla de acción<textarea
            v-model="body.action_template"
            maxlength="10000"
          />
        </label>
        <p v-pre>
          Opcional. El servidor admite {piece}, {design}, {product} y
          {quantity}. Sin plantilla, se utiliza el nombre. No admite fórmulas ni
          formatos.
        </p>
        <label class="catalog-check"
          ><input v-model="body.active" type="checkbox" />Activo</label
        >
        <label class="catalog-check"
          ><input v-model="confirmed" type="checkbox" required />Confirmo los
          datos y el estado del servicio.</label
        >
        <UButton type="submit">Guardar servicio</UButton>
      </fieldset>
    </form>
  </section>
</template>
