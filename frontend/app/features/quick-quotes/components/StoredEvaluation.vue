<script setup lang="ts">
import type { Schema } from "../api";
import { quickQuoteMessages as q } from "~/i18n/quick-quotes";
import PricingResult from "./PricingResult.vue";
defineProps<{ row: Schema["QuickQuoteRead"] }>();
</script>
<template>
  <div class="asset-form">
    <section class="asset-panel asset-form">
      <h2>{{ q.revision }} {{ row.revision }} · {{ row.definition.title }}</h2>
      <p>{{ q.stored }}</p>
      <p>
        {{ row.evaluation.product_name }} · {{ row.evaluation.variant_name }} ·
        {{ row.evaluation.recipe_name }}
      </p>
      <p>
        {{ q.quantity }}: {{ row.evaluation.preview.target_quantity }}
        {{ row.evaluation.variant_unit }}
      </p>
      <time :datetime="row.created_at">{{
        new Date(row.created_at).toLocaleString("es-AR")
      }}</time>
      <p>{{ row.definition.notes }}</p>
    </section>
    <PricingResult
      :preview="row.evaluation.preview"
      :heading="`${q.history} · ${row.revision}`"
    />
    <details class="asset-panel asset-form">
      <summary>{{ q.resolvedPlan }}</summary>
      <article
        v-for="step in row.evaluation.plan.steps"
        :key="step.key"
        class="catalog-group"
      >
        <h3>{{ step.title }}</h3>
        <p>{{ step.instructions }}</p>
        <p>{{ step.service_action }}</p>
        <p>{{ step.service_instructions }}</p>
        <ul>
          <li v-for="resource in step.resources" :key="resource.key">
            <template v-if="'name' in resource"
              >{{ resource.name }} · {{ q.revision }}
              {{ resource.revision_number }} ·
              {{ resource.quantity_per_batch }}</template
            >
          </li>
        </ul>
      </article>
    </details>
    <details v-if="row.evaluation.configuration" class="asset-panel asset-form">
      <summary>{{ q.configuration }}</summary>
      <article
        v-for="selection in row.evaluation.configuration.selections"
        :key="selection.definition_id"
      >
        <h3>{{ selection.definition_id }}</h3>
        <ul>
          <li v-for="value in selection.values" :key="value.value_id">
            {{ value.value_id }} · {{ q.selectedQuantity }} {{ value.quantity }}
            <p v-if="value.revision_id">
              {{ q.revision }}: {{ value.revision_id }}
            </p>
          </li>
        </ul>
      </article>
    </details>
  </div>
</template>
