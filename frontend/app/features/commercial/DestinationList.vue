<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { commercialApi } from "./api";
import { errorMessage } from "~/features/shared/http";
import { commercialMessages as c } from "~/i18n/commercial";
const props = defineProps<{ kind: "orders" | "projects" }>();
const api = commercialApi(useRuntimeConfig().public.apiBaseUrl);
const query = useQuery({
  queryKey: [props.kind],
  queryFn: async () =>
    props.kind === "orders" ? api.orders() : api.projects(),
  retry: false,
});
useHead({ title: `${c[props.kind]} · RRII-Coach` });
</script>
<template>
  <div class="asset-library catalog">
    <h1>{{ c[kind] }}</h1>
    <nav class="asset-actions" aria-label="Gestión comercial">
      <UButton to="/quotes" color="neutral" variant="soft">{{
        c.quotes
      }}</UButton>
      <UButton
        :to="kind === 'orders' ? '/projects' : '/orders'"
        color="neutral"
        variant="soft"
        >{{ kind === "orders" ? c.projects : c.orders }}</UButton
      >
    </nav>
    <p v-if="query.isPending.value" role="status">{{ c.loading }}</p>
    <div v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value)
      }}<UButton @click="query.refetch()">{{ c.retry }}</UButton>
    </div>
    <template v-if="query.data.value">
      <p v-if="!query.data.value.length">{{ c.empty }}</p>
      <ul class="asset-grid">
        <li v-for="row in query.data.value" :key="row.id" class="asset-panel">
          <h2>
            <NuxtLink :to="`/${kind}/${row.id}`"
              >{{ row.code }} · {{ row.title }}</NuxtLink
            >
          </h2>
          <p>{{ row.status === "pending" ? c.pending : c.cancelled }}</p>
          <p>{{ row.currency }} {{ row.quoted_final_price }}</p>
        </li>
      </ul>
    </template>
  </div>
</template>
