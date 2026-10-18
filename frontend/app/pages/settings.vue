<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { installationApi } from "~/features/installation/api";
import {
  settingsLabels,
  policies,
  depositTypes,
} from "~/features/installation/fields";
import SettingsEditor from "~/features/installation/SettingsEditor.vue";
import { provideDraftGuard } from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
const api = installationApi(useRuntimeConfig().public.apiBaseUrl);
const query = useQuery({
  queryKey: ["installation-settings"],
  queryFn: api.get,
  retry: false,
});
provideDraftGuard(
  "Hay cambios de configuración sin guardar. ¿Salir de la pantalla?",
);
async function refresh() {
  return !(await query.refetch()).isError;
}
function display(key: string, value: string | null | undefined) {
  if (value === null || value === undefined || value === "")
    return "Sin definir";
  if (key === "deposit_policy")
    return policies[value as keyof typeof policies] ?? value;
  if (key === "deposit_type")
    return depositTypes[value as keyof typeof depositTypes] ?? value;
  return value;
}
useHead({ title: "Configuración de instalación · RRII-Coach" });
</script>
<template>
  <div class="asset-library catalog asset-form">
    <h1>Configuración de instalación</h1>
    <p>
      Datos del negocio, seña y parámetros de costos compartidos por esta
      instalación. La apariencia del navegador se configura desde el botón de la
      barra superior.
    </p>
    <UButton color="neutral" variant="soft" @click="refresh"
      >Consultar datos guardados</UButton
    >
    <p v-if="query.isPending.value" role="status">Cargando configuración…</p>
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <template v-if="query.data.value">
      <details class="asset-panel">
        <summary>Datos guardados</summary>
        <dl>
          <template v-for="(label, key) in settingsLabels" :key="key"
            ><dt>{{ label }}</dt>
            <dd>
              {{
                display(
                  key,
                  query.data.value[key as keyof typeof query.data.value],
                )
              }}
            </dd></template
          >
        </dl>
      </details>
      <SettingsEditor :settings="query.data.value" :refresh="refresh" />
    </template>
  </div>
</template>
