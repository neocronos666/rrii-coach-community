<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { quickQuoteApi } from "~/features/quick-quotes/api";
import { quickQuoteMessages as q } from "~/i18n/quick-quotes";
import { errorMessage } from "~/features/shared/http";
const api = quickQuoteApi(useRuntimeConfig().public.apiBaseUrl),
  offset = ref(0);
const query = useQuery({
  queryKey: computed(() => ["quick-quotes", offset.value]),
  queryFn: () => api.list(offset.value),
  retry: false,
});
useHead({ title: `${q.title} · RRII-Coach` });
</script>
<template>
  <div class="asset-library catalog">
    <header class="asset-heading">
      <div>
        <h1>{{ q.title }}</h1>
        <p>{{ q.description }}</p>
      </div>
      <UButton to="/quick-quotes/new">{{ q.new }}</UButton>
    </header>
    <UButton to="/quotes" color="neutral" variant="soft">{{
      q.formalQuotes
    }}</UButton>
    <p v-if="query.isPending.value" role="status">{{ q.loading }}</p>
    <div v-else-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value)
      }}<UButton @click="query.refetch()">{{ q.retry }}</UButton>
    </div>
    <template v-else
      ><p v-if="!query.data.value?.length">{{ q.empty }}</p>
      <ul class="asset-grid">
        <li
          v-for="row in query.data.value?.slice(0, 24)"
          :key="row.id"
          class="asset-panel"
        >
          <h2>
            <NuxtLink :to="`/quick-quotes/${row.id}`">{{
              row.definition.title
            }}</NuxtLink>
          </h2>
          <p>
            {{ row.evaluation.product_name }} ·
            {{ row.evaluation.variant_name }}
          </p>
          <p>
            {{ q.revision }} {{ row.revision }} ·
            {{ row.evaluation.preview.complete ? q.complete : q.incomplete }}
          </p>
        </li>
      </ul>
      <nav class="asset-actions" :aria-label="q.title">
        <UButton
          color="neutral"
          variant="soft"
          :disabled="!offset"
          @click="offset = Math.max(0, offset - 24)"
          >{{ q.previous }}</UButton
        ><UButton
          color="neutral"
          variant="soft"
          :disabled="!query.data.value || query.data.value.length <= 24"
          @click="offset += 24"
          >{{ q.next }}</UButton
        >
      </nav></template
    >
  </div>
</template>
