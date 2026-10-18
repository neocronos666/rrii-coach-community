<script setup lang="ts">
import { useQueryClient } from "@tanstack/vue-query";
import {
  quickQuoteApi,
  type Schema,
  type Definition,
} from "~/features/quick-quotes/api";
import { usePending } from "~/features/quick-quotes/usePending";
import { provideDraftGuard } from "~/features/shared/useDraftGuard";
import { quickQuoteMessages as q } from "~/i18n/quick-quotes";
import QuoteForm from "~/features/quick-quotes/components/QuoteForm.vue";
import PendingStatus from "~/features/shared/PendingStatus.vue";
const api = quickQuoteApi(useRuntimeConfig().public.apiBaseUrl),
  cache = useQueryClient(),
  form = ref<InstanceType<typeof QuoteForm>>();
const productId =
  typeof useRoute().query.product === "string"
    ? String(useRoute().query.product)
    : undefined;
provideDraftGuard(q.unsaved);
const mutation = usePending<
  Schema["QuickQuoteCreate"],
  Schema["QuickQuoteRead"]
>("create", api.create);
async function save(definition?: Definition) {
  const result = await mutation.run(definition);
  if (result) {
    form.value?.markSaved();
    await cache.invalidateQueries({ queryKey: ["quick-quotes"] });
    await navigateTo(`/quick-quotes/${result.id}`);
  }
}
useHead({ title: `${q.new} · RRII-Coach` });
</script>
<template>
  <div class="asset-library catalog">
    <UButton to="/quick-quotes" color="neutral" variant="soft">{{
      q.back
    }}</UButton>
    <h1>{{ q.new }}</h1>
    <PendingStatus
      :pending="!!mutation.pending.value"
      :busy="mutation.busy.value"
      :error="mutation.error.value"
      :persistent="mutation.persistent.value"
      :invalid="mutation.invalid.value"
      @retry="save()"
      @clear="mutation.clearInvalid"
    /><QuoteForm
      ref="form"
      :product-id="productId"
      :locked="
        !mutation.ready.value ||
        mutation.busy.value ||
        !!mutation.pending.value ||
        mutation.invalid.value
      "
      :submit-label="q.save"
      @save="save"
    />
  </div>
</template>
