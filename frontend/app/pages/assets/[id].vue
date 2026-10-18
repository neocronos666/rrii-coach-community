<script setup lang="ts">
import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { assetApi, errorMessage, type FileRole } from "~/features/assets/api";
import type { MessageKey } from "~/i18n/es";
definePageMeta({ key: (route) => route.path });
const { t } = useI18n();
const id = String(useRoute().params.id);
const api = assetApi(useRuntimeConfig().public.apiBaseUrl);
const cache = useQueryClient();
const selected = ref("");
const other = ref("");
const compareTarget = ref("");
const note = ref("");
const busy = ref(false);
const failure = ref("");
const success = ref("");
const uploadInput = ref<HTMLInputElement>();
const file = shallowRef<File>();
const filename = ref("");
const role = ref<FileRole>("manufacturing");
const previewFailed = ref(false);
const roles: Record<FileRole, MessageKey> = {
  manufacturing: "assets.manufacturing",
  source: "assets.source",
  documentation: "assets.documentation",
  reference: "assets.reference",
  media: "assets.media",
  thumbnail: "assets.thumbnailRole",
};
const assetQuery = useQuery({
  queryKey: ["assets", id],
  queryFn: () => api.get(id),
  retry: false,
});
const asset = computed(() => assetQuery.data.value);
const revisionsQuery = useQuery({
  queryKey: ["asset-revisions", id],
  queryFn: () => api.revisions(id),
  enabled: computed(() => !!asset.value),
  retry: false,
});
const revisions = computed(() => revisionsQuery.data.value ?? []);
watch([asset, revisions], () => {
  if (!selected.value && asset.value)
    selected.value = asset.value.current_revision_id;
});
const filesQuery = useQuery({
  queryKey: computed(() => ["asset-files", id, selected.value]),
  queryFn: () => api.files(id, selected.value),
  enabled: computed(() => !!selected.value),
  retry: false,
});
const files = computed(() => filesQuery.data.value ?? []);
const thumbnail = computed(() =>
  files.value.find((entry) => entry.role === "thumbnail"),
);
const revision = computed(() =>
  revisions.value.find((row) => row.id === selected.value),
);
const comparisonQuery = useQuery({
  queryKey: computed(() => [
    "asset-diff",
    id,
    selected.value,
    compareTarget.value,
  ]),
  queryFn: () => api.compare(id, selected.value, compareTarget.value),
  enabled: computed(() => !!selected.value && !!compareTarget.value),
  retry: false,
});
const differences = [
  "added",
  "removed",
  "content_changed",
  "role_changed",
] as const;
watch(selected, () => {
  other.value = "";
  compareTarget.value = "";
  failure.value = "";
  success.value = "";
  previewFailed.value = false;
  file.value = undefined;
  filename.value = "";
  if (uploadInput.value) uploadInput.value.value = "";
});
watch(role, () => {
  filename.value =
    role.value === "thumbnail" ? "preview.png" : (file.value?.name ?? "");
});
function chooseFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0];
  filename.value =
    role.value === "thumbnail" ? "preview.png" : (file.value?.name ?? "");
}
async function act(action: () => Promise<void>) {
  busy.value = true;
  failure.value = "";
  success.value = "";
  try {
    await action();
  } catch (error) {
    failure.value = errorMessage(error);
  } finally {
    busy.value = false;
  }
}
async function refresh() {
  await Promise.all([
    cache.invalidateQueries({ queryKey: ["assets"] }),
    cache.invalidateQueries({ queryKey: ["asset-revisions", id] }),
  ]);
}
function createRevision(restore: boolean) {
  const source = selected.value;
  return act(async () => {
    const result = restore
      ? await api.restore(id, source, note.value)
      : await api.newRevision(id, note.value);
    await refresh();
    selected.value = result.id;
    note.value = "";
    await nextTick();
    success.value = t("assets.restored");
  });
}
function archive() {
  return act(async () => {
    await api.archive(id, !asset.value?.archived);
    await refresh();
    success.value = t("assets.saved");
  });
}
function upload() {
  const revisionId = selected.value;
  const source = file.value;
  if (!source) return;
  return act(async () => {
    await api.upload(id, revisionId, source, filename.value, role.value);
    await Promise.all([
      cache.invalidateQueries({ queryKey: ["asset-files", id, revisionId] }),
      cache.invalidateQueries({ queryKey: ["asset-diff", id] }),
    ]);
    previewFailed.value = false;
    file.value = undefined;
    filename.value = "";
    if (uploadInput.value) uploadInput.value.value = "";
    success.value = t("assets.uploaded");
  });
}
useHead(() => ({
  title: `${asset.value?.name ?? t("assets.title")} · ${t("brand.name")}`,
}));
</script>
<template>
  <UButton
    v-if="asset"
    :to="`/asset-details/${id}`"
    color="neutral"
    variant="soft"
    >Editar datos del Asset</UButton
  >
  <UButton
    v-if="asset && selected"
    :to="`/asset-structure/${id}?revision=${selected}`"
    color="neutral"
    variant="soft"
    >Familia, compatibilidades y composición</UButton
  >
  <div class="asset-library">
    <UButton to="/assets" color="neutral" variant="soft">{{
      t("assets.back")
    }}</UButton>
    <p v-if="assetQuery.isPending.value" role="status">
      {{ t("assets.loading") }}
    </p>
    <div v-else-if="assetQuery.error.value" role="alert">
      <h1>{{ t("assets.title") }}</h1>
      <p>{{ errorMessage(assetQuery.error.value) }}</p>
      <UButton @click="assetQuery.refetch()">{{ t("assets.retry") }}</UButton>
    </div>
    <template v-if="asset">
      <header class="asset-heading">
        <div>
          <p class="eyebrow">{{ asset.code }}</p>
          <h1>{{ asset.name }}</h1>
          <p>{{ asset.description }}</p>
        </div>
        <UButton
          color="neutral"
          variant="soft"
          :disabled="busy"
          @click="archive"
          >{{
            t(asset.archived ? "assets.unarchive" : "assets.archive")
          }}</UButton
        >
      </header>
      <p v-if="asset.archived" role="status">
        {{ t("assets.archivedNotice") }}
      </p>
      <p v-if="failure" role="alert" class="asset-error">{{ failure }}</p>
      <p v-if="success" role="status">{{ success }}</p>
      <section class="asset-panel asset-form">
        <h2>{{ t("assets.revisions") }}</h2>
        <p v-if="revisionsQuery.isPending.value" role="status">
          {{ t("assets.loading") }}
        </p>
        <div v-if="revisionsQuery.error.value" role="alert">
          <p>{{ errorMessage(revisionsQuery.error.value) }}</p>
          <UButton @click="revisionsQuery.refetch()">{{
            t("assets.retry")
          }}</UButton>
        </div>
        <label for="asset-revision">{{ t("assets.revision") }}</label
        ><select
          id="asset-revision"
          v-model="selected"
          :disabled="busy || !revisions.length"
        >
          <option v-for="row in revisions" :key="row.id" :value="row.id">
            {{ row.number }} ·
            {{
              t(
                row.id === asset.current_revision_id
                  ? "assets.current"
                  : "assets.historical",
              )
            }}
          </option>
        </select>
        <p v-if="revision?.note">{{ revision.note }}</p>
        <time v-if="revision" :datetime="revision.created_at">{{
          new Date(revision.created_at).toLocaleString("es-AR")
        }}</time>
        <label for="revision-note">{{ t("assets.note") }}</label
        ><textarea
          id="revision-note"
          v-model="note"
          maxlength="10000"
          :disabled="busy"
        />
        <p>{{ t("assets.newRevisionHelp") }}</p>
        <UButton :disabled="busy" @click="createRevision(false)">{{
          t("assets.newRevision")
        }}</UButton>
        <details>
          <summary>{{ t("assets.restore") }}</summary>
          <p>{{ t("assets.restoreHelp") }}</p>
          <UButton
            :disabled="busy || !selected"
            color="neutral"
            variant="soft"
            @click="createRevision(true)"
            >{{ t("assets.restore") }}</UButton
          >
        </details>
      </section>
      <section class="asset-panel asset-form">
        <h2>{{ t("assets.files") }}</h2>
        <p v-if="filesQuery.isPending.value" role="status">
          {{ t("assets.loading") }}
        </p>
        <div v-else-if="filesQuery.error.value" role="alert">
          <p>{{ errorMessage(filesQuery.error.value) }}</p>
          <UButton @click="filesQuery.refetch()">{{
            t("assets.retry")
          }}</UButton>
        </div>
        <template v-else>
          <img
            v-if="thumbnail && !previewFailed"
            :key="thumbnail.id"
            class="asset-thumbnail"
            :src="api.thumbnail(id, selected)"
            :alt="t('assets.thumbnail')"
            @error="previewFailed = true"
          />
          <p v-if="previewFailed" role="alert">
            {{ t("assets.previewUnavailable") }}
          </p>
          <p v-if="!files.length">{{ t("assets.noFiles") }}</p>
          <ul class="asset-file-list">
            <li v-for="entry in files" :key="entry.id">
              <div>
                <strong>{{ entry.filename }}</strong>
                <p>{{ t(roles[entry.role]) }} · {{ entry.size_bytes }} B</p>
              </div>
              <UButton
                :href="api.download(id, selected, entry.id)"
                color="neutral"
                variant="soft"
                :aria-label="`${t('assets.download')} ${entry.filename}`"
                >{{ t("assets.download") }}</UButton
              >
            </li>
          </ul>
        </template>
        <form @submit.prevent="upload">
          <fieldset :disabled="busy || !selected">
            <p>{{ t("assets.uploadHelp") }}</p>
            <label for="file-role">{{ t("assets.role") }}</label
            ><select id="file-role" v-model="role">
              <option
                v-for="(label, value) in roles"
                :key="value"
                :value="value"
              >
                {{ t(label) }}
              </option>
            </select>
            <p v-if="role === 'thumbnail'" id="thumbnail-help">
              {{ t("assets.thumbnailHelp") }}
            </p>
            <label for="asset-file">{{ t("assets.file") }}</label
            ><input
              id="asset-file"
              ref="uploadInput"
              type="file"
              required
              :accept="
                role === 'thumbnail' ? 'image/png,image/jpeg' : undefined
              "
              :aria-describedby="
                role === 'thumbnail' ? 'thumbnail-help' : undefined
              "
              @change="chooseFile"
            />
            <label for="file-name">{{ t("assets.filename") }}</label
            ><input
              id="file-name"
              v-model="filename"
              required
              maxlength="255"
            />
            <UButton type="submit" :loading="busy" :disabled="!file">{{
              t("assets.upload")
            }}</UButton>
          </fieldset>
        </form>
      </section>
      <section class="asset-panel asset-form">
        <h2>{{ t("assets.compare") }}</h2>
        <label for="compare-revision">{{ t("assets.compareWith") }}</label
        ><select id="compare-revision" v-model="other" :disabled="busy">
          <option value="">—</option>
          <option
            v-for="row in revisions.filter((row) => row.id !== selected)"
            :key="row.id"
            :value="row.id"
          >
            {{ row.number }}
          </option></select
        ><UButton :disabled="!other || busy" @click="compareTarget = other">{{
          t("assets.compare")
        }}</UButton>
        <p v-if="comparisonQuery.isFetching.value" role="status">
          {{ t("assets.loading") }}
        </p>
        <div v-if="comparisonQuery.error.value" role="alert">
          <p>{{ errorMessage(comparisonQuery.error.value) }}</p>
          <UButton @click="comparisonQuery.refetch()">{{
            t("assets.retry")
          }}</UButton>
        </div>
        <div v-if="comparisonQuery.data.value">
          <p>{{ t("assets.comparison") }}</p>
          <div v-for="kind in differences" :key="kind">
            <h3>
              {{ t(`assets.${kind}`) }} ({{
                comparisonQuery.data.value[kind].length
              }})
            </h3>
            <ul>
              <li
                v-for="entry in comparisonQuery.data.value[kind]"
                :key="entry.filename"
              >
                {{ entry.filename }}
              </li>
            </ul>
          </div>
          <h3>
            {{ t("assets.unchanged") }} ({{
              comparisonQuery.data.value.unchanged.length
            }})
          </h3>
          <ul>
            <li
              v-for="entry in comparisonQuery.data.value.unchanged"
              :key="entry"
            >
              {{ entry }}
            </li>
          </ul>
        </div>
      </section>
    </template>
  </div>
</template>
