<script setup lang="ts">
import { structureApi, type Schema } from "./api";
import { useRecordedWrite } from "~/features/inventory/useRecordedWrite";
import WriteStatus from "~/features/inventory/WriteStatus.vue";
import { useDraftGuard } from "~/features/shared/useDraftGuard";
const props = defineProps<{
  asset: Schema["AssetRead"];
  assets: Schema["AssetRead"][];
  families: Schema["FamilyRead"][];
  relations: Schema["RelatedAssetRead"][];
  refresh: () => Promise<boolean>;
}>();
const api = structureApi(useRuntimeConfig().public.apiBaseUrl),
  family = ref(props.asset.family_id),
  other = ref(""),
  confirmed = ref(false);
const markFamilySaved = useDraftGuard("asset-family", () => family.value);
const markOtherSaved = useDraftGuard("asset-compatibility", () => other.value);
const state = useRecordedWrite(
  `asset-relations:${props.asset.id}`,
  props.refresh,
);
async function assign() {
  if (!confirmed.value) return;
  const result = await state.run("Cambiar familia del Asset", () =>
    api.assignFamily(props.asset.id, family.value),
  );
  if (result) {
    confirmed.value = false;
    markFamilySaved();
  }
}
async function relate() {
  if (!other.value || !confirmed.value) return;
  const result = await state.run("Registrar compatibilidad positiva", () =>
    api.relate(props.asset.id, other.value),
  );
  if (result) {
    other.value = "";
    confirmed.value = false;
    markOtherSaved();
  }
}
async function remove(id: string) {
  if (
    !window.confirm(
      "¿Retirar esta compatibilidad positiva? No declara incompatibilidad ni elimina Assets.",
    )
  )
    return;
  await state.run("Retirar compatibilidad positiva", () =>
    api.unrelate(props.asset.id, id),
  );
}
</script>
<template>
  <section class="asset-panel asset-form">
    <h2>Familia y compatibilidades actuales</h2>
    <p>
      Son relaciones del Asset, no de la revisión histórica seleccionada. Una
      familia no implica compatibilidad. La ausencia de relación no significa
      incompatibilidad.
    </p>
    <p>Familia guardada: {{ families.find(row => row.id === asset.family_id)?.name ?? asset.family_id ?? "Sin familia" }}</p>
    <WriteStatus :state="state" />
    <fieldset :disabled="state.locked.value">
      <label
        >Familia de diseño<select v-model="family">
          <option :value="null">Sin familia</option>
          <option v-for="row in families" :key="row.id" :value="row.id">
            {{ row.name }}
          </option>
        </select></label
      ><NuxtLink to="/families">Administrar familias</NuxtLink>
      <label class="catalog-check"
        ><input v-model="confirmed" type="checkbox" />Confirmo el cambio de
        relación indicado.</label
      ><UButton :disabled="!confirmed" @click="assign"
        >Guardar familia del Asset</UButton
      >
      <label
        >Asset compatible<select v-model="other">
          <option value="">Elegir Asset</option>
          <option v-for="row in assets" :key="row.id" :value="row.id">
            {{ row.code }} · {{ row.name
            }}{{ row.archived ? " · Archivado" : "" }}
          </option>
        </select></label
      ><UButton :disabled="!confirmed || !other" @click="relate"
        >Registrar compatibilidad</UButton
      >
      <ul>
        <li v-for="row in relations" :key="row.id">
          <NuxtLink :to="`/assets/${row.id}`">{{ row.name }}</NuxtLink> ·
          {{ row.archived ? "Archivado" : "Activo" }}
          <UButton color="neutral" variant="soft" @click="remove(row.id)"
            >Retirar compatibilidad · {{ row.name }}</UButton
          >
        </li>
      </ul>
      <p v-if="!relations.length">
        Sin compatibilidades positivas registradas.
      </p>
    </fieldset>
  </section>
</template>
