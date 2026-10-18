<script setup lang="ts">
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { commercialApi, type Schema } from "./api";
import { commercialDraft, quotePatch } from "./drafts";
import { useDraftGuard } from "~/features/shared/useDraftGuard";
import { usePending } from "~/features/shared/usePending";
import PendingStatus from "~/features/shared/PendingStatus.vue";
import { ApiError, errorMessage } from "~/features/shared/http";
import { commercialMessages as c } from "~/i18n/commercial";
const props = defineProps<{
  quote: Schema["QuoteRead"];
  refresh: () => Promise<unknown>;
}>();
const api = commercialApi(useRuntimeConfig().public.apiBaseUrl),
  cache = useQueryClient();
const editing = ref(false),
  busy = ref(false),
  error = ref(""),
  message = ref("");
const draft = ref(commercialDraft(props.quote)),
  original = ref(commercialDraft(props.quote));
const pricing = ref(false),
  approveConfirmed = ref(false),
  rejectConfirmed = ref(false),
  convertConfirmed = ref(false),
  reason = ref("");
const markSaved = useDraftGuard("commercial", () =>
  editing.value ? [draft.value, pricing.value] : null,
);
const destinations = useQuery({
  queryKey: ["quote-destination", props.quote.id],
  retry: false,
  enabled: computed(() => props.quote.status === "approved"),
  queryFn: async () => {
    const [orders, projects] = await Promise.all([
      api.orders(),
      api.projects(),
    ]);
    const order = orders.find((row) => row.source_quote_id === props.quote.id);
    if (order) return { url: `/orders/${order.id}`, code: order.code };
    const project = projects.find(
      (row) => row.source_quote_id === props.quote.id,
    );
    return project
      ? { url: `/projects/${project.id}`, code: project.code }
      : null;
  },
});
const conversion = usePending<
  { request_id: string },
  Schema["QuoteConversionRead"]
>(`convert:${props.quote.id}`, () => api.convert(props.quote.id), "commercial");
function edit() {
  draft.value = commercialDraft(props.quote);
  original.value = commercialDraft(props.quote);
  pricing.value = false;
  editing.value = true;
  error.value = "";
  message.value = "";
  markSaved();
}
function discard() {
  editing.value = false;
  markSaved();
}
async function refresh() {
  await props.refresh();
  await cache.invalidateQueries({ queryKey: ["quotes"] });
}
async function perform(operation: () => Promise<unknown>, saved = false) {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  message.value = "";
  try {
    await operation();
    if (saved) {
      discard();
      message.value = c.saved;
    }
    approveConfirmed.value = false;
    rejectConfirmed.value = false;
    await refresh();
  } catch (failure) {
    error.value = errorMessage(failure);
    if (
      !(failure instanceof ApiError) ||
      failure.status >= 500 ||
      failure.status === 408
    )
      error.value += ` ${c.uncertain}`;
    await refresh();
  } finally {
    busy.value = false;
  }
}
async function save() {
  const body = quotePatch(draft.value, original.value, pricing.value);
  if (!Object.keys(body).length) {
    discard();
    return;
  }
  await perform(() => api.update(props.quote.id, body), true);
}
async function convert() {
  const result = await conversion.run({});
  if (result) {
    await cache.invalidateQueries({
      queryKey: ["quote-destination", props.quote.id],
    });
    await cache.invalidateQueries({
      queryKey: [result.target_type === "order" ? "orders" : "projects"],
    });
    await navigateTo(
      `/${result.target_type === "order" ? "orders" : "projects"}/${result.target_id}`,
    );
  }
}
</script>
<template>
  <section class="asset-panel asset-form" :aria-label="c.actions">
    <h2>{{ c.actions }}</h2>
    <p v-if="error" role="alert">{{ error }}</p>
    <p v-if="message" role="status">{{ message }}</p>
    <UButton color="neutral" variant="soft" :disabled="busy" @click="refresh">{{
      c.history
    }}</UButton>
    <template v-if="quote.status === 'draft' && !editing">
      <UButton color="neutral" variant="soft" :disabled="busy" @click="edit">{{
        c.edit
      }}</UButton>
      <p>{{ c.decisionHelp }}</p>
      <form
        class="asset-form"
        @submit.prevent="perform(() => api.approve(quote.id))"
      >
        <fieldset :disabled="busy">
          <label class="catalog-check"
            ><input v-model="approveConfirmed" type="checkbox" required />{{
              c.approveConfirm
            }}</label
          >
          <UButton type="submit" :disabled="!approveConfirmed">{{
            c.approve
          }}</UButton>
        </fieldset>
      </form>
      <form
        class="asset-form"
        @submit.prevent="
          perform(() => api.reject(quote.id, { reason: reason || null }))
        "
      >
        <fieldset :disabled="busy">
          <label>{{ c.reason }}<textarea v-model="reason" /></label>
          <label class="catalog-check"
            ><input v-model="rejectConfirmed" type="checkbox" required />{{
              c.rejectConfirm
            }}</label
          >
          <UButton
            type="submit"
            color="neutral"
            variant="soft"
            :disabled="!rejectConfirmed"
            >{{ c.reject }}</UButton
          >
        </fieldset>
      </form>
    </template>
    <form v-if="editing" class="asset-form" @submit.prevent="save">
      <fieldset :disabled="busy || quote.status !== 'draft'">
        <label
          >{{ c.title }}<input v-model="draft.title" required maxlength="255"
        /></label>
        <label
          >{{ c.description }}<textarea v-model="draft.description" />
        </label>
        <label>{{ c.notes }}<textarea v-model="draft.notes" /></label>
        <label
          >{{ c.validity }}<input v-model="draft.valid_until" type="date"
        /></label>
        <label class="catalog-check"
          ><input v-model="pricing" type="checkbox" />{{ c.pricing }}</label
        >
        <template v-if="pricing">
          <p>{{ c.pricingHelp }}</p>
          <label
            >{{ c.markup
            }}<input
              v-model="draft.markup_percentage"
              inputmode="decimal"
              required
          /></label>
          <label class="catalog-check"
            ><input v-model="draft.manual" type="checkbox" />{{
              c.manual
            }}</label
          >
          <label v-if="draft.manual"
            >{{ c.final
            }}<input v-model="draft.final_price" inputmode="decimal" required
          /></label>
          <section
            v-for="(adjustment, index) in draft.adjustments"
            :key="index"
            class="asset-panel asset-form"
          >
            <label
              >{{ c.adjustment
              }}<input
                v-model="adjustment.description"
                required
                maxlength="1000"
            /></label>
            <label
              >{{ c.type
              }}<select v-model="adjustment.adjustment_type">
                <option value="surcharge">{{ c.surcharge }}</option>
                <option value="discount">{{ c.discount }}</option>
              </select></label
            >
            <label
              >{{ c.valueType
              }}<select v-model="adjustment.value_type">
                <option value="fixed">{{ c.fixed }}</option>
                <option value="percentage">{{ c.percentage }}</option>
              </select></label
            >
            <label
              >{{ c.value
              }}<input v-model="adjustment.value" inputmode="decimal" required
            /></label>
            <UButton
              type="button"
              color="neutral"
              variant="soft"
              @click="draft.adjustments.splice(index, 1)"
              >{{ c.remove }}</UButton
            >
          </section>
          <UButton
            type="button"
            color="neutral"
            variant="soft"
            @click="
              draft.adjustments.push({
                description: '',
                adjustment_type: 'surcharge',
                value_type: 'fixed',
                value: '0',
              })
            "
            >{{ c.add }}</UButton
          >
        </template>
        <UButton type="submit">{{ c.save }}</UButton>
      </fieldset>
      <UButton
        type="button"
        color="neutral"
        variant="soft"
        :disabled="busy"
        @click="discard"
        >{{ c.discard }}</UButton
      >
    </form>
    <p v-if="quote.rejection_reason">
      {{ c.reason }}: {{ quote.rejection_reason }}
    </p>
    <template v-if="quote.status === 'approved'">
      <p>{{ c.convertHelp }}</p>
      <p v-if="destinations.isPending.value" role="status">{{ c.loading }}</p>
      <div v-if="destinations.error.value" role="alert">
        {{ errorMessage(destinations.error.value)
        }}<UButton @click="destinations.refetch()">{{ c.retry }}</UButton>
      </div>
      <UButton v-if="destinations.data.value" :to="destinations.data.value.url"
        >{{ c.open }} · {{ destinations.data.value.code }}</UButton
      >
      <PendingStatus
        :pending="!!conversion.pending.value"
        :busy="conversion.busy.value"
        :error="conversion.error.value"
        :persistent="conversion.persistent.value"
        :invalid="conversion.invalid.value"
        @retry="convert"
        @clear="conversion.clearInvalid"
      />
      <form
        v-if="!destinations.data.value && !conversion.pending.value"
        class="asset-form"
        @submit.prevent="convert"
      >
        <fieldset
          :disabled="
            !conversion.ready.value ||
            conversion.busy.value ||
            conversion.invalid.value ||
            editing
          "
        >
          <label class="catalog-check"
            ><input v-model="convertConfirmed" type="checkbox" required />{{
              c.convertConfirm
            }}</label
          >
          <UButton type="submit" :disabled="!convertConfirmed">{{
            c.convert
          }}</UButton>
        </fieldset>
      </form>
    </template>
  </section>
</template>
