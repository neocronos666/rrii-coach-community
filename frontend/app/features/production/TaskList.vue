<script setup lang="ts">
import type { Schema } from "./api";
import {
  productionMessages as p,
  productionStates,
  productionPriorities,
} from "~/i18n/production";
import { testPrintMessages as t } from "~/i18n/test-prints";
defineProps<{ tasks: Schema["ProductionTaskRead"][] }>();
</script>
<template>
  <p v-if="!tasks.length">{{ p.empty }}</p>
  <ul class="asset-grid">
    <li v-for="task in tasks" :key="task.id" class="asset-panel asset-form">
      <h2>
        <NuxtLink :to="`/production/tasks/${task.id}`"
          >{{ task.code }} · {{ task.title }}</NuxtLink
        >
      </h2>
      <p>
        {{ productionStates[task.status] }} ·
        {{ productionPriorities[task.priority] }}
      </p>
      <p>{{ t.target }}: {{ task.planned_quantity }} {{ task.planned_unit }}</p>
      <p v-if="task.recipe_step_key">
        {{ t.step }}: {{ task.recipe_step_key }}
      </p>
      <UButton
        v-if="task.production_plan_id"
        :to="`/production/plans/${task.production_plan_id}`"
        color="neutral"
        variant="soft"
        >{{ p.planLink }}</UButton
      >
    </li>
  </ul>
</template>
