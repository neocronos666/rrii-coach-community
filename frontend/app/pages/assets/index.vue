<script setup lang="ts">
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { assetApi, errorMessage } from "~/features/assets/api";
const { t } = useI18n();
const api = assetApi(useRuntimeConfig().public.apiBaseUrl);
const cache = useQueryClient();
const search = ref("");
const appliedSearch = ref("");
const archived = ref(false);
const offset = ref(0);
const creating = ref(false);
const busy = ref(false);
const message = ref("");
const name = ref("");
const description = ref("");
const category = ref("");
const { data, isPending, error, refetch } = useQuery({
  queryKey: computed(() => [
    "assets",
    "list",
    appliedSearch.value,
    archived.value,
    offset.value,
  ]),
  queryFn: () => api.list(appliedSearch.value, archived.value, offset.value),
  retry: false,
});
const categories = useQuery({
  queryKey: ["asset-categories"],
  queryFn: api.categories,
  retry: false,
});
const rows = computed(() => data.value?.slice(0, 24) ?? []);
function filter() {
  offset.value = 0;
  appliedSearch.value = search.value;
}
watch(archived, () => {
  offset.value = 0;
});
async function create() {
  busy.value = true;
  message.value = "";
  try {
    const result = await api.create({
      third_party: false,
      name: name.value,
      description: description.value || null,
      category_id: category.value || undefined,
    });
    await cache.invalidateQueries({ queryKey: ["assets"] });
    await navigateTo(`/assets/${result.id}`);
  } catch (error) {
    message.value = errorMessage(error);
  } finally {
    busy.value = false;
  }
}
useHead(() => ({ title: `${t("assets.title")} · ${t("brand.name")}` }));
</script>
<template>
  <UButton to="/asset-categories" color="neutral" variant="soft"
    >Administrar categorías</UButton
  >
  <div class="asset-library">
    <header class="asset-heading">
      <div>
        <h1>{{ t("assets.title") }}</h1>
        <p>{{ t("assets.description") }}</p>
      </div>
      <UButton @click="creating = !creating">{{ t("assets.create") }}</UButton>
    </header>
    <form
      v-if="creating"
      class="asset-panel asset-form"
      @submit.prevent="create"
    >
      <h2>{{ t("assets.create") }}</h2>
      <fieldset :disabled="busy">
        <label for="asset-name">{{ t("assets.name") }}</label
        ><input id="asset-name" v-model="name" required maxlength="255" />
        <label for="asset-description">{{ t("assets.descriptionLabel") }}</label
        ><textarea
          id="asset-description"
          v-model="description"
          maxlength="10000"
        />
        <label for="asset-category">{{ t("assets.category") }}</label
        ><select id="asset-category" v-model="category">
          <option value="">{{ t("assets.defaultCategory") }}</option>
          <option
            v-for="row in categories.data.value"
            :key="row.id"
            :value="row.id"
          >
            {{ row.name }}
          </option>
        </select>
        <p v-if="categories.error.value" role="alert">
          {{ errorMessage(categories.error.value) }}
        </p>
        <div class="asset-actions">
          <UButton type="submit" :loading="busy">{{ t("assets.save") }}</UButton
          ><UButton color="neutral" variant="soft" @click="creating = false">{{
            t("assets.cancel")
          }}</UButton>
        </div>
      </fieldset>
      <p v-if="message" role="alert">{{ message }}</p>
    </form>
    <form class="asset-search" @submit.prevent="filter">
      <div>
        <label for="asset-search">{{ t("assets.search") }}</label
        ><input
          id="asset-search"
          v-model="search"
          maxlength="255"
          type="search"
        />
      </div>
      <UButton type="submit">{{ t("assets.filter") }}</UButton
      ><label class="asset-checkbox"
        ><input v-model="archived" type="checkbox" />{{
          t("assets.archived")
        }}</label
      >
    </form>
    <p v-if="isPending" role="status">{{ t("assets.loading") }}</p>
    <div v-else-if="error" role="alert">
      <p>{{ errorMessage(error) }}</p>
      <UButton @click="refetch()">{{ t("assets.retry") }}</UButton>
    </div>
    <template v-else>
      <p v-if="!rows.length" role="status">{{ t("assets.empty") }}</p>
      <ul class="asset-grid">
        <li v-for="asset in rows" :key="asset.id" class="asset-panel">
          <p class="eyebrow">{{ asset.code }}</p>
          <h2>
            <NuxtLink :to="`/assets/${asset.id}`">{{ asset.name }}</NuxtLink>
          </h2>
          <p v-if="asset.description">{{ asset.description }}</p>
          <p v-if="asset.archived">{{ t("assets.archivedNotice") }}</p>
        </li>
      </ul>
      <nav class="asset-actions" :aria-label="t('assets.title')">
        <UButton
          color="neutral"
          variant="soft"
          :disabled="offset === 0"
          @click="offset = Math.max(0, offset - 24)"
          >{{ t("assets.previous") }}</UButton
        ><UButton
          color="neutral"
          variant="soft"
          :disabled="!data || data.length <= 24"
          @click="offset += 24"
          >{{ t("assets.next") }}</UButton
        >
      </nav>
    </template>
  </div>
</template>
