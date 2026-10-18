<script setup lang="ts">
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import type { QuickQuoteApi, Schema } from "../api";
import { usePending } from "../usePending";
import { useDraftGuard } from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
import { quickQuoteMessages as q } from "~/i18n/quick-quotes";
import PendingStatus from "~/features/shared/PendingStatus.vue";
const props = defineProps<{
  api: QuickQuoteApi;
  id: string;
  revision: number;
}>();
const cache = useQueryClient(),
  title = ref(""),
  validUntil = ref(""),
  finalPrice = ref(""),
  adjustments = ref<Schema["QuoteAdjustmentInput"][]>([]);
const link = useQuery({
  queryKey: ["quick-quote-formalization", props.id],
  queryFn: () => props.api.formalization(props.id),
  retry: false,
});
const mutation = usePending<
  Schema["QuickQuoteFormalize"],
  Schema["QuickQuoteFormalizationRead"]
>(`formalize:${props.id}`, (body) => props.api.formalize(props.id, body));
const markSaved = useDraftGuard("quick-formalization", () => [
  title.value,
  validUntil.value,
  finalPrice.value,
  adjustments.value,
]);
async function save() {
  const result = await mutation.run({
    source_revision: props.revision,
    title: title.value || null,
    valid_until: validUntil.value || null,
    final_price: finalPrice.value || null,
    adjustments: adjustments.value,
  });
  if (result) {
    markSaved();
    cache.setQueryData(["quick-quote-formalization", props.id], result);
    await cache.invalidateQueries({ queryKey: ["quotes"] });
  }
}
</script>
<template>
  <section class="asset-panel asset-form" :aria-label="q.formalTitle">
    <h2>{{ q.formalTitle }}</h2>
    <p>{{ q.formalHelp }}</p>
    <p>{{ q.rounding }}</p>
    <p v-if="link.isPending.value" role="status">{{ q.loading }}</p>
    <div v-if="link.error.value" role="alert">
      {{ errorMessage(link.error.value) }}
    </div>
    <UButton
      color="neutral"
      variant="soft"
      :disabled="mutation.busy.value"
      @click="link.refetch()"
      >{{ q.viewLink }}</UButton
    ><template v-if="link.data.value"
      ><p role="status">{{ q.formalized }}</p>
      <p>{{ q.sourceRevision }}: {{ link.data.value.source_revision }}</p>
      <UButton :to="`/quotes/${link.data.value.quote_id}`">{{
        q.viewFormal
      }}</UButton></template
    >
    <PendingStatus
      :pending="!!mutation.pending.value"
      :busy="mutation.busy.value"
      :error="mutation.error.value"
      :persistent="mutation.persistent.value"
      :invalid="mutation.invalid.value"
      @retry="save"
      @clear="mutation.clearInvalid"
    />
    <form
      v-if="link.data.value === null"
      class="asset-form"
      @submit.prevent="save"
    >
      <p>
        {{ q.sourceRevision }}:
        {{ mutation.pending.value?.source_revision ?? revision }}
      </p>
      <fieldset
        :disabled="
          !mutation.ready.value ||
          mutation.busy.value ||
          !!mutation.pending.value ||
          mutation.invalid.value
        "
      >
        <label
          >{{ q.formalName }}<input v-model="title" maxlength="255" /></label
        ><label
          >{{ q.validUntil }}<input v-model="validUntil" type="date" /></label
        ><label
          >{{ q.finalOverride }}<input v-model="finalPrice" inputmode="decimal"
        /></label>
        <h3>{{ q.adjustments }}</h3>
        <section
          v-for="(adjustment, index) in adjustments"
          :key="index"
          class="catalog-group asset-form"
        >
          <label
            >{{ q.adjustmentDescription
            }}<input
              v-model="adjustment.description"
              required
              maxlength="1000" /></label
          ><label
            >{{ q.adjustmentType
            }}<select v-model="adjustment.adjustment_type">
              <option value="discount">{{ q.discount }}</option>
              <option value="surcharge">{{ q.surcharge }}</option>
            </select></label
          ><label
            >{{ q.valueType
            }}<select v-model="adjustment.value_type">
              <option value="fixed">{{ q.fixed }}</option>
              <option value="percentage">{{ q.percentage }}</option>
            </select></label
          ><label
            >{{ q.adjustmentValue
            }}<input
              v-model="adjustment.value"
              inputmode="decimal"
              required /></label
          ><UButton
            color="neutral"
            variant="soft"
            @click="adjustments.splice(index, 1)"
            >{{ q.remove }}</UButton
          >
        </section>
        <UButton
          color="neutral"
          variant="soft"
          @click="
            adjustments.push({
              description: '',
              adjustment_type: 'discount',
              value_type: 'fixed',
              value: '0',
            })
          "
          >{{ q.addAdjustment }}</UButton
        ><UButton type="submit">{{ q.formalize }}</UButton>
      </fieldset>
    </form>
  </section>
</template>
