<script setup lang="ts">
import type { RunOptions } from "./run-options";
const model = defineModel<RunOptions>({ required: true });
</script>
<template>
  <details class="asset-panel asset-form">
    <summary>Opciones de ejecución</summary>
    <p>
      Vacío usa la hora del servidor y los parámetros guardados. La fecha
      ingresada usa la zona horaria de este navegador.
    </p>
    <label
      >Inicio real (opcional)<input
        v-model="model.startedAt"
        type="datetime-local"
        step="1"
    /></label>
    <label class="catalog-check"
      ><input v-model="model.override" type="checkbox" />Reemplazar parámetros
      para este intento</label
    >
    <label v-if="model.override"
      >Parámetros del intento (objeto JSON)<textarea
        v-model="model.parameters"
        rows="4"
      />
    </label>
  </details>
</template>
