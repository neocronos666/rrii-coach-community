<script setup lang="ts">
import { installationApi, type Settings } from "./api";
import {
  identityFields,
  costFields,
  policies,
  depositTypes,
  settingsPayload,
  sameSettings,
} from "./fields";
import { useRecordedWrite } from "~/features/inventory/useRecordedWrite";
import WriteStatus from "~/features/inventory/WriteStatus.vue";
import { useDraftGuard } from "~/features/shared/useDraftGuard";
import { ApiError } from "~/features/shared/http";
const props = defineProps<{
  settings: Settings;
  refresh: () => Promise<boolean>;
}>();
const api = installationApi(useRuntimeConfig().public.apiBaseUrl);
const body = ref<Settings>(structuredClone(toRaw(props.settings)));
let original = structuredClone(toRaw(props.settings));
const confirmed = ref(false),
  loading = ref(false);
const state = useRecordedWrite("installation-settings", props.refresh);
const markSaved = useDraftGuard("installation", () => body.value);
async function reloadForm() {
  if (
    state.locked.value ||
    loading.value ||
    !window.confirm(
      "¿Reemplazar el formulario por los valores guardados y descartar los cambios locales?",
    )
  )
    return;
  loading.value = true;
  try {
    if (!(await props.refresh())) return;
    await nextTick();
    body.value = structuredClone(toRaw(props.settings));
    original = structuredClone(toRaw(props.settings));
    confirmed.value = false;
    state.error.value = "";
    markSaved();
  } finally {
    loading.value = false;
  }
}
async function save() {
  if (!confirmed.value || loading.value) return;
  const payload = settingsPayload(body.value);
  const result = await state.run(
    "Configuración completa de instalación",
    async () => {
      const current = await api.get();
      if (!sameSettings(current, original))
        throw new ApiError(
          "La configuración cambió desde que abriste el formulario. Revisá los datos guardados y cargalos en el formulario antes de editar nuevamente.",
          409,
        );
      return api.save(payload);
    },
  );
  if (result) {
    body.value = structuredClone(result);
    original = structuredClone(result);
    confirmed.value = false;
    markSaved();
  }
}
</script>
<template>
  <section class="asset-panel asset-form">
    <h2>Editar configuración</h2>
    <p>
      Guardar reemplaza todos los valores de instalación. Los cambios se
      utilizarán en operaciones futuras; los costos y presupuestos históricos
      conservan sus snapshots.
    </p>
    <p>
      Consultar los datos guardados no modifica este formulario. Para incorporar
      cambios de otra sesión, usá «Cargar valores guardados».
    </p>
    <WriteStatus :state="state" />
    <UButton
      color="neutral"
      variant="soft"
      :disabled="state.locked.value || loading"
      @click="reloadForm"
      >Cargar valores guardados</UButton
    >
    <form class="asset-form" @submit.prevent="save">
      <fieldset :disabled="state.locked.value || loading">
        <legend>Instalación</legend>
        <label v-for="field in identityFields" :key="field.key"
          >{{ field.label
          }}<input
            v-model="body[field.key]"
            :required="field.required"
            :maxlength="field.max"
        /></label>
        <p>
          La zona horaria se valida como identificador IANA, por ejemplo
          America/Argentina/Buenos_Aires. El idioma guardado no cambia las
          traducciones disponibles de esta interfaz, que sigue en castellano.
        </p>
        <p>
          Cambiar moneda no convierte importes. Revisá las tarifas y señas fijas
          antes de guardar.
        </p>
      </fieldset>
      <fieldset :disabled="state.locked.value || loading">
        <legend>Seña predeterminada</legend>
        <label
          >Política de seña<select v-model="body.deposit_policy">
            <option
              v-for="(label, value) in policies"
              :key="value"
              :value="value"
            >
              {{ label }}
            </option>
          </select></label
        >
        <label
          >Tipo de seña<select v-model="body.deposit_type">
            <option :value="null">Sin tipo</option>
            <option
              v-for="(label, value) in depositTypes"
              :key="value"
              :value="value"
            >
              {{ label }}
            </option>
          </select></label
        >
        <label
          >Valor de seña<input v-model="body.deposit_value" inputmode="decimal"
        /></label>
        <p>
          Sin seña requiere tipo y valor vacíos. Opcional u obligatoria
          requieren ambos. El servidor valida la combinación y los porcentajes;
          este formulario no cobra ni calcula señas.
        </p>
      </fieldset>
      <fieldset :disabled="state.locked.value || loading">
        <legend>Costos y markup</legend>
        <p>
          Tarifas monetarias en {{ body.currency }}. Usá punto decimal. Vacío
          significa desconocido; cero es un valor explícito. Markup es un
          porcentaje, no margen.
        </p>
        <label v-for="field in costFields" :key="field.key"
          >{{ field.label
          }}<input v-model="body[field.key]" inputmode="decimal"
        /></label>
        <label class="catalog-check"
          ><input v-model="confirmed" required type="checkbox" />Confirmo el
          reemplazo completo de la configuración.</label
        >
        <UButton type="submit">Guardar configuración</UButton>
      </fieldset>
    </form>
  </section>
</template>
