<script setup lang="ts">
import type { Schema } from "../api";
import { quickQuoteMessages as q } from "~/i18n/quick-quotes";
defineProps<{ preview: Schema["PricingPreviewRead"]; heading: string }>();
</script>
<template>
  <section class="asset-panel asset-form" :aria-label="heading">
    <h2>{{ heading }}</h2>
    <p>{{ preview.complete ? q.complete : q.incomplete }}</p>
    <p v-if="preview.multi_currency">{{ q.multi }}</p>
    <h3>{{ q.technical }}</h3>
    <dl>
      <template
        v-for="(amount, currency) in preview.totals_by_currency"
        :key="currency"
        ><dt>{{ currency }}</dt>
        <dd>{{ amount }}</dd></template
      >
    </dl>
    <p v-if="!Object.keys(preview.totals_by_currency).length">
      {{ q.unknown }}
    </p>
    <h3>{{ q.suggested }}</h3>
    <p>
      {{
        preview.suggested_price === null
          ? q.noPrice
          : `${preview.suggested_currency} ${preview.suggested_price}`
      }}
    </p>
    <p>{{ q.markup }}: {{ preview.markup_percentage ?? q.unknown }}</p>
    <div v-if="preview.warnings.length">
      <h3>{{ q.warnings }}</h3>
      <ul>
        <li v-for="warning in preview.warnings" :key="warning">
          {{ warning }}
        </li>
      </ul>
    </div>
    <p>{{ q.omitted }}: {{ preview.omitted_step_keys.join(", ") || q.none }}</p>
    <h3>{{ q.lines }}</h3>
    <p v-if="!preview.lines.length">{{ q.noLines }}</p>
    <article
      v-for="(line, index) in preview.lines"
      :key="index"
      class="catalog-group"
    >
      <h4>{{ line.description }}</h4>
      <p>
        {{ q.step }}: {{ line.step_key }} ·
        {{ line.complete ? q.complete : q.incomplete }}
      </p>
      <dl>
        <dt>{{ q.lineQuantity }}</dt>
        <dd>{{ line.quantity }} {{ line.unit }}</dd>
        <dt>{{ q.unitCost }}</dt>
        <dd>{{ line.unit_cost ?? q.unknown }} {{ line.currency }}</dd>
        <dt>{{ q.subtotal }}</dt>
        <dd>{{ line.subtotal ?? q.unknown }} {{ line.currency }}</dd>
        <dt>{{ q.source }}</dt>
        <dd>{{ line.source }}</dd>
      </dl>
      <details
        v-if="line.source_reference || line.purchase_id || line.movement_id"
      >
        <summary>{{ q.reference }}</summary>
        <p>{{ line.source_reference }}</p>
        <p>{{ line.purchase_id }}</p>
        <p>{{ line.movement_id }}</p>
      </details>
    </article>
    <div
      v-for="step in preview.planned_steps"
      :key="step.key"
      class="catalog-group"
    >
      <h4>{{ step.key }}</h4>
      <dl>
        <dt>{{ q.demand }}</dt>
        <dd>{{ step.required_quantity }} {{ step.unit }}</dd>
        <dt>{{ q.batches }}</dt>
        <dd>{{ step.batches }}</dd>
        <dt>{{ q.capacity }}</dt>
        <dd>{{ step.planned_capacity }}</dd>
      </dl>
    </div>
  </section>
</template>
