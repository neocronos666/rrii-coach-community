<script setup lang="ts">
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { productApi, type Schema } from "~/features/products/api";
import { newVariant, variantUpdate } from "~/features/products/drafts";
import { useCatalog } from "~/features/products/useCatalog";
import { useEditor } from "~/features/products/useEditor";
import { errorMessage } from "~/features/shared/http";
import { testPrintMessages as t } from "~/i18n/test-prints";
import { quickQuoteMessages as q } from "~/i18n/quick-quotes";
import { productMessages as p } from "~/i18n/products";
import VariantFields from "~/features/products/components/VariantFields.vue";
import ConfigurationEditor from "~/features/products/components/ConfigurationEditor.vue";
import RecipeEditor from "~/features/products/components/RecipeEditor.vue";
import RecipePreview from "~/features/products/components/RecipePreview.vue";
import {
  provideDraftGuard,
  useDraftGuard,
} from "~/features/products/useDraftGuard";
definePageMeta({ key: (route) => route.path });
const id = String(useRoute().params.id),
  api = productApi(useRuntimeConfig().public.apiBaseUrl),
  cache = useQueryClient();
const query = useQuery({
  queryKey: ["products", id],
  queryFn: () => api.get(id),
  retry: false,
});
const variants = useQuery({
  queryKey: ["product-variants", id],
  queryFn: () => api.variants(id),
  retry: false,
});
const configuration = useQuery({
  queryKey: ["product-configuration", id],
  queryFn: () => api.configuration(id),
  retry: false,
});
const catalog = useCatalog(api),
  name = ref(""),
  description = ref(""),
  active = ref(true),
  initialized = ref(false),
  version = ref(0);
const variant = ref(newVariant()),
  editing = ref(""),
  variantForm = ref(false);
const { busy, failure, success, act } = useEditor();
const registry = provideDraftGuard();
const markProductSaved = useDraftGuard(
  "product",
  () => [name.value, description.value, active.value],
  registry,
);
const markVariantSaved = useDraftGuard(
  "variant",
  () => (variantForm.value ? variant.value : null),
  registry,
);
watch(
  query.data,
  (row) => {
    if (row && !initialized.value) {
      name.value = row.name;
      description.value = row.description || "";
      active.value = row.active;
      initialized.value = true;
      markProductSaved();
    }
  },
  { immediate: true },
);
function save() {
  return act(async () => {
    const row = await api.update(id, {
      name: name.value,
      description: description.value || null,
      active: active.value,
    });
    cache.setQueryData(["products", id], row);
    markProductSaved();
    await cache.invalidateQueries({ queryKey: ["products", "list"] });
    await cache.invalidateQueries({ queryKey: ["product-editor-catalog"] });
    version.value++;
  });
}
function editVariant(row?: Schema["VariantRead"]) {
  editing.value = row?.id || "";
  variant.value = row
    ? {
        ...variantUpdate(row),
        name: row.name,
        base_unit: row.base_unit,
        active: row.active,
        attributes: { ...row.attributes },
      }
    : newVariant();
  variantForm.value = true;
  markVariantSaved();
}
watch(
  variantForm,
  (open) => {
    if (!open) markVariantSaved();
  },
  { flush: "sync" },
);
function saveVariant() {
  return act(async () => {
    if (editing.value) {
      const { base_unit, ...body } = variant.value;
      await api.updateVariant(editing.value, body);
    } else await api.addVariant(id, variant.value);
    await cache.invalidateQueries({ queryKey: ["product-variants", id] });
    variantForm.value = false;
    version.value++;
  });
}
useHead(() => ({ title: `${query.data.value?.name || p.title} · RRII-Coach` }));
</script>
<template>
  <div class="asset-library catalog">
    <UButton to="/products" color="neutral" variant="soft">{{
      p.back
    }}</UButton>
    <p v-if="query.isPending.value" role="status">{{ p.loading }}</p>
    <div v-else-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value)
      }}<UButton @click="query.refetch()">{{ p.retry }}</UButton>
    </div>
    <template v-if="query.data.value">
      <h1>{{ query.data.value.name }}</h1>
      <UButton :to="`/quick-quotes/new?product=${id}`">{{
        q.newFromProduct
      }}</UButton>
      <nav class="asset-actions" :aria-label="p.title">
        <a href="#product-variants">{{ p.variants }}</a
        ><a href="#product-options">{{ p.options }}</a
        ><a href="#product-recipe">{{ p.recipe }}</a
        ><a href="#product-preview">{{ p.preview }}</a>
      </nav>
      <form class="asset-panel asset-form" @submit.prevent="save">
        <fieldset :disabled="busy">
          <label
            >{{ p.name
            }}<input v-model="name" required maxlength="255" /></label
          ><label>{{ p.description }}<textarea v-model="description" /></label
          ><label class="catalog-check"
            ><input v-model="active" type="checkbox" />{{ p.active }}</label
          ><UButton type="submit">{{ p.save }}</UButton>
        </fieldset>
      </form>
      <section id="product-variants" class="asset-panel asset-form">
        <h2>{{ p.variants }}</h2>
        <p v-if="variants.isPending.value" role="status">{{ p.loading }}</p>
        <div v-if="variants.error.value" role="alert">
          {{ errorMessage(variants.error.value)
          }}<UButton @click="variants.refetch()">{{ p.retry }}</UButton>
        </div>
        <ul class="asset-file-list">
          <li v-for="row in variants.data.value" :key="row.id">
            <div>
              <strong>{{ row.name }}</strong>
              <p>
                {{ row.sku }} · {{ row.base_unit }}
                {{ row.active ? "" : ` · ${p.inactiveLabel}` }}
              </p>
            </div>
            <UButton
              color="neutral"
              variant="soft"
              :disabled="busy"
              @click="editVariant(row)"
              >{{ p.editVariant }} · {{ row.name }}</UButton
            ><UButton
              :to="`/test-prints/new?variant=${row.id}`"
              color="neutral"
              variant="soft"
              >{{ t.fromVariant }} · {{ row.name }}</UButton
            ><UButton
              :to="`/test-prints?variant=${row.id}`"
              color="neutral"
              variant="soft"
              >{{ t.history }} · {{ row.name }}</UButton
            ><UButton
              :to="`/inventory/variants/${row.id}`"
              color="neutral"
              variant="soft"
              >Ver stock · {{ row.name }}</UButton
            >
          </li>
        </ul>
        <UButton
          color="neutral"
          variant="soft"
          :disabled="busy"
          @click="editVariant()"
          >{{ p.newVariant }}</UButton
        >
        <form
          v-if="variantForm"
          class="asset-form"
          @submit.prevent="saveVariant"
        >
          <fieldset :disabled="busy">
            <VariantFields v-model="variant" :existing="!!editing" />
            <div class="asset-actions">
              <UButton type="submit">{{ p.saveVariant }}</UButton
              ><UButton
                color="neutral"
                variant="soft"
                @click="variantForm = false"
                >{{ p.cancel }}</UButton
              >
            </div>
          </fieldset>
        </form>
      </section>
      <p v-if="failure" role="alert">{{ failure }}</p>
      <p v-if="success" role="status">{{ success }}</p>
      <p
        v-if="catalog.isPending.value || configuration.isPending.value"
        role="status"
      >
        {{ p.loading }}
      </p>
      <div v-if="catalog.error.value || configuration.error.value" role="alert">
        <p>{{ p.catalogError }}</p>
        <p>
          {{ errorMessage(catalog.error.value || configuration.error.value) }}
        </p>
        <UButton
          @click="
            catalog.refetch();
            configuration.refetch();
          "
          >{{ p.retry }}</UButton
        >
      </div>
      <template v-if="catalog.data.value && configuration.data.value"
        ><div id="product-options">
          <ConfigurationEditor
            :api="api"
            :product-id="id"
            :catalog="catalog.data.value"
            @saved="version++"
          />
        </div>
        <div id="product-recipe">
          <RecipeEditor
            :api="api"
            :product-id="id"
            :catalog="catalog.data.value"
            :configuration="configuration.data.value"
            @saved="version++"
          />
        </div>
        <div id="product-preview">
          <RecipePreview
            :api="api"
            :product-id="id"
            :catalog="catalog.data.value"
            :configuration="configuration.data.value"
            :variants="variants.data.value ?? []"
            :version="version"
          /></div
      ></template>
    </template>
  </div>
</template>
