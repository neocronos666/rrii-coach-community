<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { productApi } from "~/features/products/api";
import { newVariant } from "~/features/products/drafts";
import VariantFields from "~/features/products/components/VariantFields.vue";
import { useEditor } from "~/features/products/useEditor";
import { errorMessage } from "~/features/shared/http";
import { productMessages as p } from "~/i18n/products";
import {
  provideDraftGuard,
  useDraftGuard,
} from "~/features/products/useDraftGuard";
const api = productApi(useRuntimeConfig().public.apiBaseUrl);
const search = ref(""),
  applied = ref(""),
  inactive = ref(false),
  offset = ref(0),
  creating = ref(false),
  name = ref(""),
  description = ref("");
const variant = ref(newVariant());
const { busy, failure, act } = useEditor();
const registry = provideDraftGuard();
const markSaved = useDraftGuard(
  "create",
  () =>
    creating.value ? [name.value, description.value, variant.value] : null,
  registry,
);
const query = useQuery({
  queryKey: computed(() => [
    "products",
    "list",
    applied.value,
    inactive.value,
    offset.value,
  ]),
  queryFn: () => api.list(applied.value, !inactive.value, offset.value),
  retry: false,
});
watch(inactive, () => (offset.value = 0));
function filter() {
  offset.value = 0;
  applied.value = search.value;
}
function create() {
  return act(async () => {
    const row = await api.create({
      name: name.value,
      description: description.value || null,
      active: true,
      initial_variant: variant.value,
    });
    markSaved();
    await navigateTo(`/products/${row.id}`);
  });
}
useHead({ title: `${p.title} · RRII-Coach` });
</script>
<template>
  <div class="asset-library catalog">
    <header class="asset-heading">
      <div>
        <h1>{{ p.title }}</h1>
        <p>{{ p.intro }}</p>
      </div>
      <UButton @click="creating = !creating">{{ p.create }}</UButton>
    </header>
    <form
      v-if="creating"
      class="asset-panel asset-form"
      @submit.prevent="create"
    >
      <h2>{{ p.create }}</h2>
      <fieldset :disabled="busy">
        <label
          >{{ p.name }}<input v-model="name" required maxlength="255" /></label
        ><label>{{ p.description }}<textarea v-model="description" /></label>
        <h3>{{ p.initialVariant }}</h3>
        <VariantFields v-model="variant" />
        <div class="asset-actions">
          <UButton type="submit" :loading="busy">{{ p.save }}</UButton
          ><UButton color="neutral" variant="soft" @click="creating = false">{{
            p.cancel
          }}</UButton>
        </div>
      </fieldset>
      <p v-if="failure" role="alert">{{ failure }}</p>
    </form>
    <form class="asset-search" @submit.prevent="filter">
      <label
        >{{ p.search
        }}<input v-model="search" type="search" maxlength="255" /></label
      ><UButton type="submit">{{ p.searchAction }}</UButton
      ><label class="catalog-check"
        ><input v-model="inactive" type="checkbox" />{{ p.inactive }}</label
      >
    </form>
    <p v-if="query.isPending.value" role="status">{{ p.loading }}</p>
    <div v-else-if="query.error.value" role="alert">
      <p>{{ errorMessage(query.error.value) }}</p>
      <UButton @click="query.refetch()">{{ p.retry }}</UButton>
    </div>
    <template v-else
      ><p v-if="!query.data.value?.length">{{ p.empty }}</p>
      <ul class="asset-grid">
        <li
          v-for="row in query.data.value?.slice(0, 24)"
          :key="row.id"
          class="asset-panel"
        >
          <h2>
            <NuxtLink :to="`/products/${row.id}`">{{ row.name }}</NuxtLink>
          </h2>
          <p>{{ row.description }}</p>
        </li>
      </ul>
      <nav class="asset-actions" :aria-label="p.title">
        <UButton
          color="neutral"
          variant="soft"
          :disabled="!offset"
          @click="offset = Math.max(0, offset - 24)"
          >{{ p.previous }}</UButton
        ><UButton
          color="neutral"
          variant="soft"
          :disabled="!query.data.value || query.data.value.length <= 24"
          @click="offset += 24"
          >{{ p.next }}</UButton
        >
      </nav></template
    >
  </div>
</template>
