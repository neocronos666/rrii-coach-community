<script setup lang="ts">
import type { Schema } from "./api";
defineProps<{ calculation: Schema["CostCalculationRead"] }>();
</script>
<template>
  <section class="asset-panel asset-form">
    <h2>Cálculo técnico guardado</h2>
    <p>
      Identificador: <span class="record-id">{{ calculation.id }}</span>
    </p>
    <p>
      {{
        calculation.complete
          ? "Completo"
          : "Incompleto: faltan fuentes de costo"
      }}
      · {{ calculation.multi_currency ? "Varias monedas" : "Monomoneda" }}
    </p>
    <p>{{ calculation.calculated_at }} · {{ calculation.calculation_type }}</p>
    <p v-if="calculation.demand_quantity">
      Demanda: {{ calculation.demand_quantity }} {{ calculation.demand_unit }}
    </p>
    <p v-for="warning in calculation.warnings" :key="warning" role="status">
      {{ warning }}
    </p>
    <ul>
      <li v-for="line in calculation.lines" :key="line.id">
        {{ line.description }} · {{ line.quantity }} {{ line.unit }} ·
        {{ line.currency }} {{ line.subtotal ?? "Costo desconocido" }}
      </li>
    </ul>
    <p
      v-for="(total, currency) in calculation.totals_by_currency"
      :key="currency"
    >
      Total técnico: {{ currency }} {{ total }}
    </p>
  </section>
</template>
