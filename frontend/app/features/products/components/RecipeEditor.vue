<script setup lang="ts">
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import type { ProductApi, Schema, Step, Configuration } from "../api";
import type { Catalog } from "../useCatalog";
import { newStep, stepDraft } from "../drafts";
import { useDraftGuard } from "../useDraftGuard";
import { useEditor } from "../useEditor";
import { errorMessage } from "~/features/shared/http";
import { productMessages as p } from "~/i18n/products";
import RecipeStepEditor from "./RecipeStepEditor.vue";
const props = defineProps<{
  api: ProductApi;
  productId: string;
  catalog: Catalog;
  configuration: Configuration;
}>();
const emit = defineEmits<{ saved: [] }>();
const cache = useQueryClient(),
  name = ref(""),
  description = ref(""),
  active = ref(true),
  steps = ref<Step[]>([]),
  ready = ref(false),
  assetHints = ref<Record<string, string>>({});
const { busy, failure, success, act } = useEditor();
const metadataReady = ref(false);
const markMetadataSaved = useDraftGuard("recipe-metadata", () => [
  name.value,
  description.value,
  active.value,
]);
const markPlanSaved = useDraftGuard("recipe-plan", () => steps.value);
const recipe = useQuery({
  queryKey: ["base-recipe", props.productId],
  queryFn: () => props.api.baseRecipe(props.productId),
  retry: false,
});
watch(
  recipe.data,
  (row) => {
    if (row && !metadataReady.value) {
      name.value = row.name;
      description.value = row.description ?? "";
      active.value = row.active;
      metadataReady.value = true;
      markMetadataSaved();
    }
  },
  { immediate: true },
);
const plan = useQuery({
  queryKey: computed(() => ["recipe-plan", recipe.data.value?.id]),
  queryFn: () => props.api.plan(recipe.data.value!.id),
  enabled: computed(() => !!recipe.data.value),
  retry: false,
});
function load(data: Schema["PlanRead"]) {
  steps.value = data.steps.map((row) => stepDraft(toRaw(row)));
  assetHints.value = Object.fromEntries(
    data.steps.flatMap((step) =>
      (step.resources ?? []).flatMap((resource) =>
        "asset_id" in resource
          ? [[resource.asset_revision_id, resource.asset_id]]
          : [],
      ),
    ),
  );
  ready.value = true;
  markPlanSaved();
}
watch(
  plan.data,
  (data) => {
    if (data && !ready.value) load(data);
  },
  { immediate: true },
);
function saveRecipe() {
  return act(async () => {
    const body = {
      name: name.value,
      description: description.value || null,
      active: active.value,
    };
    const row = recipe.data.value
      ? await props.api.updateRecipe(recipe.data.value.id, body)
      : await props.api.createRecipe(props.productId, body);
    cache.setQueryData(["base-recipe", props.productId], row);
    markMetadataSaved();
    emit("saved");
  });
}
function savePlan() {
  return act(async () => {
    const row = await props.api.savePlan(recipe.data.value!.id, {
      steps: steps.value,
    });
    load(row);
    cache.setQueryData(["recipe-plan", row.recipe_id], row);
    emit("saved");
  });
}
function addStep() {
  let n = steps.value.length + 1;
  while (steps.value.some((row) => row.key === `step_${n}`)) n++;
  steps.value.push(newStep(`step_${n}`));
}
const serviceName = ref(""),
  serviceTemplate = ref(""),
  serviceInstructions = ref("");
function createService() {
  return act(async () => {
    await props.api.createService({
      name: serviceName.value,
      action_template: serviceTemplate.value || null,
      instructions: serviceInstructions.value || null,
      active: true,
    });
    await cache.invalidateQueries({ queryKey: ["product-editor-catalog"] });
    serviceName.value = "";
    serviceTemplate.value = "";
    serviceInstructions.value = "";
  });
}
</script>
<template>
  <UButton to="/services" color="neutral" variant="soft"
    >Administrar servicios reutilizables</UButton
  >
  <section class="asset-panel asset-form">
    <h2>{{ p.recipe }}</h2>
    <p v-if="recipe.isPending.value" role="status">{{ p.loading }}</p>
    <div v-else-if="recipe.error.value" role="alert">
      {{ errorMessage(recipe.error.value)
      }}<UButton @click="recipe.refetch()">{{ p.retry }}</UButton>
    </div>
    <template v-else
      ><p v-if="!recipe.data.value">{{ p.noRecipe }}</p>
      <form class="asset-form" @submit.prevent="saveRecipe">
        <fieldset :disabled="busy">
          <label
            >{{ p.recipeName
            }}<input v-model="name" required maxlength="255" /></label
          ><label>{{ p.description }}<textarea v-model="description" /></label
          ><label class="catalog-check"
            ><input v-model="active" type="checkbox" />{{ p.active }}</label
          ><UButton type="submit">{{
            recipe.data.value ? p.saveRecipe : p.createRecipe
          }}</UButton>
        </fieldset>
      </form>
      <template v-if="recipe.data.value"
        ><h3>{{ p.plan }}</h3>
        <p>{{ p.planHelp }}</p>
        <p v-if="plan.isPending.value" role="status">{{ p.loading }}</p>
        <div v-if="plan.error.value" role="alert">
          {{ errorMessage(plan.error.value)
          }}<UButton @click="plan.refetch()">{{ p.retry }}</UButton>
        </div>
        <form v-if="ready" class="asset-form" @submit.prevent="savePlan">
          <fieldset :disabled="busy">
            <section
              v-for="(step, index) in steps"
              :key="index"
              class="catalog-group asset-form"
              :aria-label="`${p.plan} ${index + 1}`"
            >
              <h4>{{ index + 1 }} · {{ step.title || p.stepTitle }}</h4>
              <RecipeStepEditor
                v-model="steps[index]!"
                :api="api"
                :catalog="catalog"
                :configuration="configuration"
                :steps="steps"
                :asset-hints="assetHints"
              /><UButton
                color="neutral"
                variant="soft"
                @click="steps.splice(index, 1)"
                >{{ p.remove }} {{ p.stepTitle }}</UButton
              >
            </section>
            <div class="asset-actions">
              <UButton color="neutral" variant="soft" @click="addStep">{{
                p.addStep
              }}</UButton
              ><UButton type="submit" :loading="busy">{{ p.savePlan }}</UButton>
            </div>
          </fieldset>
        </form>
      </template></template
    >
    <details>
      <summary>{{ p.newService }}</summary>
      <form class="asset-form" @submit.prevent="createService">
        <fieldset :disabled="busy">
          <label
            >{{ p.serviceName
            }}<input v-model="serviceName" required maxlength="255" /></label
          ><label
            >{{ p.actionTemplate }}<textarea v-model="serviceTemplate" /></label
          ><label
            >{{ p.instructions
            }}<textarea v-model="serviceInstructions" /></label
          ><UButton type="submit">{{ p.createService }}</UButton>
        </fieldset>
      </form>
    </details>
    <p v-if="failure" role="alert">{{ failure }}</p>
    <p v-if="success" role="status">{{ success }}</p>
  </section>
</template>
