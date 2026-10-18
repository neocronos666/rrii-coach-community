<script setup lang="ts">
import { structureApi, type Schema } from "./api";
import { useRecordedWrite } from "~/features/inventory/useRecordedWrite";
import WriteStatus from "~/features/inventory/WriteStatus.vue";
import { useDraftGuard } from "~/features/shared/useDraftGuard";
const props = defineProps<{
  family?: Schema["FamilyRead"];
  refresh: () => Promise<boolean>;
}>();
const emit = defineEmits<{ saved: [id: string] }>();
const api = structureApi(useRuntimeConfig().public.apiBaseUrl);
const body = ref({
  name: props.family?.name ?? "",
  description: props.family?.description ?? (null as string | null),
});
const original = { ...body.value },
  confirmed = ref(false),
  markSaved = useDraftGuard("family", () => body.value);
const state = useRecordedWrite(
  `family:${props.family?.id ?? "new"}`,
  props.refresh,
);
async function save() {
  if (!confirmed.value) return;
  const payload = {
    ...body.value,
    description: body.value.description || null,
  };
  const row = await state.run(payload.name, () =>
    props.family
      ? api.updateFamily(
          props.family.id,
          Object.fromEntries(
            Object.entries(payload).filter(
              ([key, value]) =>
                value !== original[key as keyof typeof original],
            ),
          ),
        )
      : api.createFamily(payload),
  );
  if (row) {
    Object.assign(original, payload);
    confirmed.value = false;
    markSaved();
    emit("saved", row.id);
  }
}
</script>
<template>
  <section class="asset-panel asset-form">
    <h2>Datos de la familia</h2>
    <WriteStatus :state="state" />
    <form class="asset-form" @submit.prevent="save">
      <fieldset :disabled="state.locked.value">
        <label
          >Nombre<input v-model="body.name" maxlength="255" required /></label
        ><label
          >Descripción<textarea v-model="body.description" maxlength="10000" />
        </label>
        <label class="catalog-check"
          ><input v-model="confirmed" type="checkbox" required />Confirmo los
          datos de la familia.</label
        ><UButton type="submit">Guardar familia</UButton>
      </fieldset>
    </form>
  </section>
</template>
