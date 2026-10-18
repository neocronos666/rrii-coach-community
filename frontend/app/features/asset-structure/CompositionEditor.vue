<script setup lang="ts">
import { structureApi, type Schema } from "./api";
import ComponentFields from "./ComponentFields.vue";
import { useRecordedWrite } from "~/features/inventory/useRecordedWrite";
import WriteStatus from "~/features/inventory/WriteStatus.vue";
import { useDraftGuard } from "~/features/shared/useDraftGuard";
const props = defineProps<{
  asset: Schema["AssetRead"];
  revision: Schema["RevisionRead"];
  components: Schema["ComponentRead"][];
  updates: Schema["ComponentUpdateRead"][];
  assets: Schema["AssetRead"][];
  refresh: () => Promise<boolean>;
}>();
const api = structureApi(useRuntimeConfig().public.apiBaseUrl);
const rows = ref(
    props.components.map((row) => ({
      key: crypto.randomUUID(),
      body: {
        child_asset_id: row.child_asset_id,
        child_revision_id: row.child_revision_id,
        quantity: row.quantity,
      } as Schema["ComponentInput"],
    })),
  ),
  note = ref(""),
  confirmed = ref(false);
const state = useRecordedWrite(`composition:${props.asset.id}`, props.refresh);
const markSaved = useDraftGuard("composition", () => [rows.value, note.value]);
const current = computed(
  () => props.asset.current_revision_id === props.revision.id,
);
function add() {
  rows.value.push({
    key: crypto.randomUUID(),
    body: { child_asset_id: "", child_revision_id: "", quantity: "1" },
  });
}
function adopt(update: Schema["ComponentUpdateRead"]) {
  const row = rows.value.find(
    (row) => row.body.child_asset_id === update.child_asset_id,
  );
  if (row) row.body.child_revision_id = update.current_revision_id;
}
async function publish() {
  if (!confirmed.value || !current.value) return;
  const result = await state.run(
    `Publicar composición desde revisión ${props.revision.number}`,
    () =>
      api.publish(props.asset.id, {
        base_revision_id: props.revision.id,
        components: rows.value.map((row) => ({ ...row.body })),
        note: note.value || null,
      }),
  );
  if (result) {
    markSaved();
    confirmed.value = false;
    await navigateTo(
      `/asset-structure/${props.asset.id}?revision=${result.id}`,
    );
  }
}
</script>
<template>
  <section class="asset-panel asset-form">
    <h2>Composición de la revisión {{ revision.number }}</h2>
    <p>
      Publicar crea una nueva revisión del padre y conserva sus archivos. Cada
      hijo queda fijado a una revisión concreta. Lista vacía retira todos los
      hijos en la nueva revisión; no altera el historial.
    </p>
    <p v-if="!current">
      Esta revisión ya no es la actual. Consultala sin modificarla y abrí la
      revisión vigente para publicar.
    </p>
    <WriteStatus :state="state" />
    <ul>
      <li v-for="update in updates" :key="update.child_asset_id">
        {{ update.name }} · fijada {{ update.pinned_revision_number }} · actual
        {{ update.current_revision_number
        }}{{ update.archived ? " · Archivado" : "" }}
        <UButton
          v-if="update.update_available"
          :disabled="!current || state.locked.value"
          @click="adopt(update)"
          >Adoptar revisión actual · {{ update.name }}</UButton
        >
      </li>
    </ul>
    <form class="asset-form" @submit.prevent="publish">
      <fieldset :disabled="!current || state.locked.value">
        <fieldset
          v-for="(row, index) in rows"
          :key="row.key"
          class="asset-panel"
        >
          <legend>Componente {{ index + 1 }}</legend>
          <ComponentFields v-model="row.body" :assets="assets" /><UButton
            color="neutral"
            variant="soft"
            @click="rows.splice(index, 1)"
            >Quitar componente {{ index + 1 }}</UButton
          >
        </fieldset>
        <UButton color="neutral" variant="soft" @click="add"
          >Agregar componente</UButton
        ><label
          >Nota de revisión<textarea v-model="note" maxlength="10000" /></label
        ><label class="catalog-check"
          ><input v-model="confirmed" type="checkbox" required />Confirmo
          publicar la lista completa de componentes en una revisión
          nueva.</label
        ><UButton type="submit">Publicar composición</UButton>
      </fieldset>
    </form>
  </section>
</template>
