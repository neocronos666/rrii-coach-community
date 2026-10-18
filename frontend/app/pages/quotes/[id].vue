<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { quickQuoteApi } from "~/features/quick-quotes/api";
import { errorMessage } from "~/features/shared/http";
import {
  quickQuoteMessages as q,
  quoteStatusLabels,
} from "~/i18n/quick-quotes";
import QuoteActions from "~/features/commercial/QuoteActions.vue";
import { provideDraftGuard } from "~/features/shared/useDraftGuard";
import { commercialMessages as c } from "~/i18n/commercial";
provideDraftGuard(c.unsaved);
definePageMeta({ key: (route) => route.path });
const id = String(useRoute().params.id),
  api = quickQuoteApi(useRuntimeConfig().public.apiBaseUrl),
  query = useQuery({
    queryKey: ["quote", id],
    queryFn: () => api.quote(id),
    retry: false,
  }),
  quote = computed(() => query.data.value);
useHead(() => ({
  title: `${quote.value?.code || q.formalQuotes} · RRII-Coach`,
}));
</script>
<template>
  <div class="asset-library catalog">
    <UButton to="/quotes" color="neutral" variant="soft">{{
      q.formalQuotes
    }}</UButton>
    <p v-if="query.isPending.value" role="status">{{ q.loading }}</p>
    <div v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value)
      }}<UButton @click="query.refetch()">{{ q.retry }}</UButton>
    </div>
    <template v-if="quote"
      ><h1>{{ quote.code }} · {{ quote.title }}</h1>
      <p>{{ q.formalStatus }}: {{ quoteStatusLabels[quote.status] }}</p>
      <p>{{ quote.description }}</p>
      <section class="asset-panel asset-form">
        <h2>{{ q.final }}</h2>
        <p data-testid="formal-total">
          {{ quote.currency }} {{ quote.breakdown.final_price }}
        </p>
        <dl>
          <dt>{{ q.technical }}</dt>
          <dd>{{ quote.currency }} {{ quote.breakdown.technical_cost }}</dd>
          <dt>{{ q.markup }}</dt>
          <dd>{{ quote.breakdown.markup_percentage }}</dd>
          <dt>{{ q.suggested }}</dt>
          <dd>{{ quote.currency }} {{ quote.breakdown.suggested_price }}</dd>
          <dt>{{ q.deposit }}</dt>
          <dd>{{ quote.breakdown.deposit_amount ?? q.none }}</dd>
        </dl>
        <p>{{ q.validUntil }}: {{ quote.valid_until || q.none }}</p>
        <ul>
          <li
            v-for="adjustment in quote.breakdown.adjustments"
            :key="adjustment.id"
          >
            {{ adjustment.description }} · {{ adjustment.amount }}
            {{ quote.currency }}
          </li>
        </ul>
      </section>
      <section v-for="item in quote.items" :key="item.id" class="asset-panel">
        <h2>{{ item.description }}</h2>
        <p>{{ q.quantity }}: {{ item.quantity }}</p>
        <p>
          {{ q.technical }}: {{ item.currency }} {{ item.technical_total_cost }}
        </p>
        <p>{{ item.notes }}</p>
      </section>
      <p>{{ quote.notes }}</p>
      <UButton
        v-if="quote.status === 'draft' && !quote.source_quick_quote_id"
        :to="`/quote-items/${quote.id}`"
        >Editar ítems técnicos</UButton
      >
      <QuoteActions :quote="quote" :refresh="query.refetch" />
      <UButton
        v-if="quote.source_quick_quote_id"
        :to="`/quick-quotes/${quote.source_quick_quote_id}?revision=${quote.source_quick_quote_revision}`"
        color="neutral"
        variant="soft"
        >{{ q.sourceRevision }} {{ quote.source_quick_quote_revision }}</UButton
      ></template
    >
  </div>
</template>
