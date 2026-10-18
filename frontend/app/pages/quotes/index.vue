<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { quickQuoteApi } from "~/features/quick-quotes/api";
import { errorMessage } from "~/features/shared/http";
import {
  quickQuoteMessages as q,
  quoteStatusLabels,
} from "~/i18n/quick-quotes";
import { commercialMessages as c } from "~/i18n/commercial";
const api = quickQuoteApi(useRuntimeConfig().public.apiBaseUrl),
  query = useQuery({
    queryKey: ["quotes"],
    queryFn: () => api.quotes(),
    retry: false,
  });
useHead({ title: `${q.formalQuotes} · RRII-Coach` });
</script>
<template>
  <div class="asset-library catalog">
    <h1>{{ q.formalQuotes }}</h1>
    <div class="asset-actions">
      <UButton to="/quotes/new">Presupuesto con ítems técnicos</UButton>
      <UButton to="/calculations/new" color="neutral" variant="soft"
        >Cálculo técnico</UButton
      >
      <UButton to="/orders" color="neutral" variant="soft">{{
        c.orders
      }}</UButton>
      <UButton to="/projects" color="neutral" variant="soft">{{
        c.projects
      }}</UButton>
      <UButton to="/quick-quotes/new">{{ q.new }}</UButton
      ><UButton to="/quick-quotes" color="neutral" variant="soft">{{
        q.viewDrafts
      }}</UButton>
    </div>
    <p v-if="query.isPending.value" role="status">{{ q.loading }}</p>
    <div v-else-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value)
      }}<UButton @click="query.refetch()">{{ q.retry }}</UButton>
    </div>
    <template v-else
      ><p v-if="!query.data.value?.length">{{ q.emptyQuotes }}</p>
      <ul class="asset-grid">
        <li v-for="row in query.data.value" :key="row.id" class="asset-panel">
          <p>{{ row.code }} · {{ quoteStatusLabels[row.status] }}</p>
          <h2>
            <NuxtLink :to="`/quotes/${row.id}`">{{ row.title }}</NuxtLink>
          </h2>
          <p>{{ row.currency }} {{ row.breakdown.final_price }}</p>
        </li>
      </ul></template
    >
  </div>
</template>
