<script setup lang="ts">
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import {
  quickQuoteApi,
  type Schema,
  type Definition,
} from "~/features/quick-quotes/api";
import { usePending } from "~/features/quick-quotes/usePending";
import { provideDraftGuard } from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
import { quickQuoteMessages as q } from "~/i18n/quick-quotes";
import QuoteForm from "~/features/quick-quotes/components/QuoteForm.vue";
import StoredEvaluation from "~/features/quick-quotes/components/StoredEvaluation.vue";
import FormalizeQuote from "~/features/quick-quotes/components/FormalizeQuote.vue";
import PendingStatus from "~/features/shared/PendingStatus.vue";
definePageMeta({ key: (route) => route.path });
const route = useRoute(),
  id = String(route.params.id),
  api = quickQuoteApi(useRuntimeConfig().public.apiBaseUrl),
  cache = useQueryClient();
provideDraftGuard(q.unsaved);
const selected = ref(Number(route.query.revision) || 0),
  editing = shallowRef<Schema["QuickQuoteRead"]>(),
  form = ref<InstanceType<typeof QuoteForm>>(),
  saved = ref(false);
const latest = useQuery({
  queryKey: ["quick-quote", id],
  queryFn: () => api.get(id),
  retry: false,
});
const history = useQuery({
  queryKey: ["quick-quote-history", id],
  queryFn: () => api.history(id),
  retry: false,
});
watch(
  history.data,
  (rows) => {
    if (!selected.value && rows?.length) selected.value = rows[0]!.revision;
  },
  { immediate: true },
);
const row = computed(() =>
  history.data.value?.find((row) => row.revision === selected.value),
);
const replace = usePending<
  Schema["QuickQuoteReplace"],
  Schema["QuickQuoteRead"]
>(`replace:${id}`, (body) => api.replace(id, body));
const recalculate = usePending<
  Schema["QuickQuoteRecalculate"],
  Schema["QuickQuoteRead"]
>(`recalculate:${id}`, (body) => api.recalculate(id, body));
const blocked = computed(
  () =>
    replace.busy.value ||
    recalculate.busy.value ||
    !!replace.pending.value ||
    !!recalculate.pending.value ||
    replace.invalid.value ||
    recalculate.invalid.value ||
    !replace.ready.value ||
    !recalculate.ready.value,
);
async function refresh() {
  await Promise.all([
    cache.invalidateQueries({ queryKey: ["quick-quote", id] }),
    cache.invalidateQueries({ queryKey: ["quick-quote-history", id] }),
    cache.invalidateQueries({ queryKey: ["quick-quotes"] }),
  ]);
}
async function finish(result?: Schema["QuickQuoteRead"]) {
  if (result) {
    form.value?.markSaved();
    editing.value = undefined;
    selected.value = result.revision;
    saved.value = true;
    await refresh();
  }
}
async function save(definition?: Definition) {
  await finish(
    await replace.run(
      definition && editing.value
        ? { ...definition, expected_revision: editing.value.revision }
        : undefined,
    ),
  );
}
async function recalc() {
  if (latest.data.value)
    await finish(
      await recalculate.run({ expected_revision: latest.data.value.revision }),
    );
  else await finish(await recalculate.run());
}
function edit() {
  if (latest.data.value) {
    editing.value = JSON.parse(JSON.stringify(latest.data.value));
    saved.value = false;
  }
}
useHead(() => ({
  title: `${latest.data.value?.definition.title || q.title} · RRII-Coach`,
}));
</script>
<template>
  <div class="asset-library catalog">
    <UButton to="/quick-quotes" color="neutral" variant="soft">{{
      q.back
    }}</UButton>
    <h1>{{ latest.data.value?.definition.title || q.title }}</h1>
    <p v-if="saved" role="status">{{ q.saved }}</p>
    <p v-if="latest.isPending.value || history.isPending.value" role="status">
      {{ q.loading }}
    </p>
    <div v-if="latest.error.value || history.error.value" role="alert">
      {{ errorMessage(latest.error.value || history.error.value) }}
    </div>
    <UButton
      color="neutral"
      variant="soft"
      :disabled="blocked"
      @click="refresh"
      >{{ q.refresh }}</UButton
    ><label
      >{{ q.revision
      }}<select v-model.number="selected">
        <option
          v-for="revision in history.data.value"
          :key="revision.revision"
          :value="revision.revision"
        >
          {{ revision.revision }} ·
          {{
            revision.revision === latest.data.value?.revision
              ? q.latest
              : q.historical
          }}
        </option>
      </select></label
    ><StoredEvaluation v-if="row" :row="row" />
    <section class="asset-panel asset-form">
      <h2>{{ q.edit }}</h2>
      <p>{{ q.conflict }}</p>
      <UButton
        v-if="!editing"
        color="neutral"
        variant="soft"
        :disabled="blocked || !latest.data.value"
        @click="edit"
        >{{ q.edit }}</UButton
      ><UButton
        v-if="editing"
        color="neutral"
        variant="soft"
        :disabled="blocked"
        @click="editing = undefined"
        >{{ q.discard }}</UButton
      ><PendingStatus
        :pending="!!replace.pending.value"
        :busy="replace.busy.value"
        :error="replace.error.value"
        :persistent="replace.persistent.value"
        :invalid="replace.invalid.value"
        @retry="save()"
        @clear="replace.clearInvalid"
      /><QuoteForm
        v-if="editing"
        :key="editing.revision"
        ref="form"
        :initial="editing.definition"
        :product-id="editing.evaluation.product_id"
        :locked="blocked"
        :submit-label="q.replace"
        @save="save"
      />
    </section>
    <section class="asset-panel asset-form">
      <h2>{{ q.recalculate }}</h2>
      <p>{{ q.recalculateHelp }}</p>
      <UButton
        :disabled="blocked || !!editing || !latest.data.value"
        @click="recalc"
        >{{ q.recalculate }}</UButton
      ><PendingStatus
        :pending="!!recalculate.pending.value"
        :busy="recalculate.busy.value"
        :error="recalculate.error.value"
        :persistent="recalculate.persistent.value"
        :invalid="recalculate.invalid.value"
        @retry="recalc"
        @clear="recalculate.clearInvalid"
      />
    </section>
    <FormalizeQuote v-if="row" :api="api" :id="id" :revision="row.revision" />
  </div>
</template>
