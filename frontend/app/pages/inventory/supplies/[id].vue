<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { inventoryApi, type Schema } from "~/features/inventory/api";
import StockSummary from "~/features/inventory/StockSummary.vue";
import SupplyEditor from "~/features/inventory/SupplyEditor.vue";
import WriteStatus from "~/features/inventory/WriteStatus.vue";
import { useRecordedWrite } from "~/features/inventory/useRecordedWrite";
import { localDateTime, utcDateTime } from "~/features/inventory/values";
import {
  provideDraftGuard,
  useDraftGuard,
} from "~/features/shared/useDraftGuard";
import { errorMessage } from "~/features/shared/http";
import {
  inventoryMessages as i,
  supplyUnits,
  movementLabels,
} from "~/i18n/inventory";
import { testPrintMessages as t } from "~/i18n/test-prints";
definePageMeta({ key: (route) => route.path });
const id = String(useRoute().params.id),
  api = inventoryApi(useRuntimeConfig().public.apiBaseUrl);
const query = useQuery({
  queryKey: ["inventory-supply", id],
  retry: false,
  queryFn: async () => {
    const [supply, presentations, purchases, movements, availability, cost] =
      await Promise.all([
        api.supply(id),
        api.presentations(id),
        api.purchases(id),
        api.movements(id),
        api.availability(id),
        api.cost(id),
      ]);
    return { supply, presentations, purchases, movements, availability, cost };
  },
});
const data = computed(() => query.data.value);
async function refresh() {
  return !(await query.refetch()).isError;
}
const state = useRecordedWrite(`supply-operations:${id}`, refresh);
const presentation = reactive({
  name: "",
  quantity: "",
  unit: "unit" as Schema["SupplyUnit"],
  purchase_price: "",
  currency: "",
});
const purchase = reactive({
  quantity: "",
  presentation_id: "",
  total_cost: "",
  currency: "ARS",
  date: localDateTime(),
  notes: "",
});
const adjustment = reactive({
  direction: "in" as Schema["AdjustmentDirection"],
  quantity: "",
  reason: "",
  date: localDateTime(),
});
const presentationConfirmed = ref(false),
  purchaseConfirmed = ref(false),
  adjustmentConfirmed = ref(false);
const registry = provideDraftGuard(i.unsaved);
const presentationSaved = useDraftGuard(
    "presentation",
    () => presentation,
    registry,
  ),
  purchaseSaved = useDraftGuard("purchase", () => purchase, registry),
  adjustmentSaved = useDraftGuard("adjustment", () => adjustment, registry);
async function addPresentation() {
  if (!presentationConfirmed.value) return;
  const result = await state.run(
    `${i.addPresentation}: ${presentation.name} · ${presentation.quantity} ${presentation.unit}`,
    () =>
      api.addPresentation(id, {
        name: presentation.name,
        active: true,
        quantity: presentation.quantity,
        unit: presentation.unit,
        purchase_price: presentation.purchase_price || null,
        currency: presentation.currency || null,
      }),
  );
  if (result) {
    presentation.name = "";
    presentation.quantity = "";
    presentation.purchase_price = "";
    presentation.currency = "";
    presentationConfirmed.value = false;
    presentationSaved();
  }
}
async function buy() {
  if (!purchaseConfirmed.value) return;
  const result = await state.run(
    `${i.purchase}: ${purchase.quantity} ${purchase.presentation_id ? data.value?.presentations.find((row) => row.id === purchase.presentation_id)?.name : data.value?.supply.base_unit} · ${purchase.currency} ${purchase.total_cost} · ${purchase.date} · ${purchase.notes}`,
    () =>
      api.purchase(id, {
        quantity: purchase.quantity,
        presentation_id: purchase.presentation_id || null,
        total_cost: purchase.total_cost,
        currency: purchase.currency,
        purchased_at: utcDateTime(purchase.date),
        notes: purchase.notes || null,
      }),
  );
  if (result) {
    purchase.quantity = "";
    purchase.total_cost = "";
    purchase.notes = "";
    purchaseConfirmed.value = false;
    purchaseSaved();
  }
}
async function adjust() {
  if (!adjustmentConfirmed.value) return;
  const result = await state.run(
    `${i.adjust}: ${adjustment.direction === "in" ? i.incoming : i.outgoing} · ${adjustment.quantity} ${data.value?.supply.base_unit} · ${adjustment.reason} · ${adjustment.date}`,
    () =>
      api.adjust(id, {
        direction: adjustment.direction,
        quantity: adjustment.quantity,
        reason: adjustment.reason,
        occurred_at: utcDateTime(adjustment.date),
      }),
  );
  if (result) {
    adjustment.quantity = "";
    adjustment.reason = "";
    adjustmentConfirmed.value = false;
    adjustmentSaved();
  }
}
useHead(() => ({
  title: `${data.value?.supply.name || i.supplies} · RRII-Coach`,
}));
</script>
<template>
  <div class="asset-library catalog asset-form">
    <UButton to="/inventory" color="neutral" variant="soft">{{
      i.title
    }}</UButton>
    <h1>{{ data?.supply.name || i.supplies }}</h1>
    <p v-if="query.isPending.value" role="status">{{ t.loading }}</p>
    <p v-if="query.error.value" role="alert">
      {{ errorMessage(query.error.value) }}
    </p>
    <UButton color="neutral" variant="soft" @click="refresh">{{
      i.refresh
    }}</UButton>
    <template v-if="data">
      <p>
        {{ data.supply.sku }} · {{ data.supply.brand }} ·
        {{ data.supply.base_unit }} ·
        {{ data.supply.active ? "Activo" : "Inactivo" }}
      </p>
      <StockSummary :stock="data.availability" />
      <section class="asset-panel">
        <h2>{{ i.cost }}</h2>
        <p v-if="data.cost" data-testid="supply-cost">
          {{ data.cost.currency }} {{ data.cost.unit_cost }} /
          {{ data.cost.unit }}
        </p>
        <p v-else>{{ i.unknownCost }}</p>
        <p>{{ i.costHelp }}</p>
      </section>
      <details>
        <summary>{{ i.editSupply }}</summary>
        <SupplyEditor :supply="data.supply" :refresh="refresh" />
      </details>
      <WriteStatus :state="state" />
      <section class="asset-panel asset-form">
        <h2>{{ i.presentations }}</h2>
        <p v-if="!data.presentations.length">{{ i.empty }}</p>
        <ul>
          <li v-for="row in data.presentations" :key="row.id">
            {{ row.name }} · {{ row.quantity }} {{ row.unit
            }}<span v-if="row.purchase_price !== null">
              · {{ row.currency }} {{ row.purchase_price }}</span
            >
          </li>
        </ul>
        <details>
          <summary>{{ i.addPresentation }}</summary>
          <form class="asset-form" @submit.prevent="addPresentation">
            <fieldset :disabled="state.locked.value">
              <label
                >{{ i.presentationName
                }}<input
                  v-model="presentation.name"
                  required
                  maxlength="255" /></label
              ><label
                >{{ i.presentationQuantity
                }}<input
                  v-model="presentation.quantity"
                  inputmode="decimal"
                  required /></label
              ><label
                >{{ i.presentationUnit
                }}<select v-model="presentation.unit">
                  <option
                    v-for="(label, value) in supplyUnits"
                    :key="value"
                    :value="value"
                  >
                    {{ label }}
                  </option>
                </select></label
              ><label
                >{{ i.referencePrice
                }}<input
                  v-model="presentation.purchase_price"
                  inputmode="decimal" /></label
              ><label
                >{{ i.currency
                }}<input v-model="presentation.currency" maxlength="3" /></label
              ><label class="catalog-check"
                ><input
                  v-model="presentationConfirmed"
                  type="checkbox"
                  required
                />{{ i.confirm }}</label
              ><UButton type="submit">{{ i.addPresentation }}</UButton>
            </fieldset>
          </form>
        </details>
      </section>
      <section class="asset-panel asset-form" aria-label="Registrar compra">
        <h2>{{ i.purchase }}</h2>
        <p>{{ i.purchaseHelp }}</p>
        <form class="asset-form" @submit.prevent="buy">
          <fieldset :disabled="state.locked.value">
            <label
              >{{ i.presentation
              }}<select v-model="purchase.presentation_id">
                <option value="">
                  {{ i.basePurchase }} · {{ data.supply.base_unit }}
                </option>
                <option
                  v-for="row in data.presentations"
                  :key="row.id"
                  :value="row.id"
                >
                  {{ row.name }} · {{ row.quantity }} {{ row.unit }}
                </option>
              </select></label
            ><label
              >{{ i.purchaseQuantity
              }}<input
                v-model="purchase.quantity"
                inputmode="decimal"
                required /></label
            ><label
              >{{ i.totalCost
              }}<input
                v-model="purchase.total_cost"
                inputmode="decimal"
                required /></label
            ><label
              >{{ i.currency
              }}<input
                v-model="purchase.currency"
                required
                minlength="3"
                maxlength="3" /></label
            ><label
              >{{ i.date
              }}<input
                v-model="purchase.date"
                type="datetime-local"
                required /></label
            ><label>{{ i.notes }}<textarea v-model="purchase.notes" /></label
            ><label class="catalog-check"
              ><input v-model="purchaseConfirmed" type="checkbox" required />{{
                i.purchaseConfirm
              }}</label
            ><UButton type="submit">{{ i.purchase }}</UButton>
          </fieldset>
        </form>
      </section>
      <details class="asset-panel">
        <summary>{{ i.adjustments }}</summary>
        <p>{{ i.adjustmentHelp }}</p>
        <form class="asset-form" @submit.prevent="adjust">
          <fieldset :disabled="state.locked.value">
            <label
              >{{ i.direction
              }}<select v-model="adjustment.direction">
                <option value="in">{{ i.incoming }}</option>
                <option value="out">{{ i.outgoing }}</option>
              </select></label
            ><label
              >{{ i.quantity }} · {{ data.supply.base_unit
              }}<input
                v-model="adjustment.quantity"
                inputmode="decimal"
                required /></label
            ><label
              >{{ i.reason
              }}<textarea
                v-model="adjustment.reason"
                required
                maxlength="2000"
              /></label
            ><label
              >{{ i.date
              }}<input
                v-model="adjustment.date"
                type="datetime-local"
                required /></label
            ><label class="catalog-check"
              ><input
                v-model="adjustmentConfirmed"
                type="checkbox"
                required
              />{{ i.adjustmentConfirm }}</label
            ><UButton type="submit">{{ i.adjust }}</UButton>
          </fieldset>
        </form>
      </details>
      <section class="asset-panel" aria-label="Historial de compras">
        <h2>{{ i.purchases }}</h2>
        <p v-if="!data.purchases.length">{{ i.empty }}</p>
        <ul>
          <li
            v-for="row in data.purchases"
            :key="row.id"
            data-testid="purchase-row"
          >
            {{ new Date(row.purchased_at).toLocaleString("es-AR") }} ·
            {{ row.quantity }} {{ data.supply.base_unit }} · {{ row.currency }}
            {{ row.total_cost }} · {{ row.notes }}<small> · {{ row.id }}</small>
          </li>
        </ul>
      </section>
      <section class="asset-panel" aria-label="Movimientos registrados">
        <h2>{{ i.movements }}</h2>
        <p v-if="!data.movements.length">{{ i.empty }}</p>
        <ul>
          <li v-for="row in data.movements" :key="row.id">
            {{ movementLabels[row.movement_type] || row.movement_type }} ·
            {{ row.quantity }} {{ data.supply.base_unit }} ·
            {{ new Date(row.occurred_at).toLocaleString("es-AR") }} ·
            {{ row.notes
            }}<small v-if="row.purchase_id">
              · Compra {{ row.purchase_id }}</small
            ><small v-if="row.run_consumption_id">
              · Consumo {{ row.run_consumption_id }}</small
            >
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>
