import { Button } from "@gravity-ui/uikit";
import { useEffect, useState } from "react";

import { saveCity } from "../../services/api/citiesApi";
import { extractErrorMessage } from "../../services/errors";
import { HubImage, Markdown } from "../hub/SafeContent";
import UnsavedChangesGuard from "../hub/UnsavedChangesGuard";
import { CityContactsEditor, CityGeneralFields } from "./CityEditorFields";
import CityLocationFields from "./CityLocationFields";

const fields = [
  "name",
  "short_description",
  "description",
  "how_to_join",
  "logo_url",
  "cover_url",
  "recruitment_status",
  "founded_at",
  "region",
  "language",
  "contacts",
  "location",
];
function cityDraft(city) {
  const draft = Object.fromEntries(
    fields.map((key) => [
      key,
      city[key] ??
        (key === "contacts"
          ? []
          : key === "location" || key === "founded_at"
            ? null
            : ""),
    ]),
  );
  if (draft.location) {
    const { map_url: _mapUrl, ...location } = draft.location;
    draft.location = location;
  }
  return draft;
}
export default function CityEditor({
  city,
  onSaved,
  onDirtyChange,
  section = "about",
}) {
  const [baseline, setBaseline] = useState(() => cityDraft(city));
  const [draft, setDraft] = useState(baseline);
  const [version, setVersion] = useState(city.version);
  const [preview, setPreview] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const changed = fields.filter(
    (key) => JSON.stringify(draft[key]) !== JSON.stringify(baseline[key]),
  );
  const dirty = changed.length > 0;
  useEffect(() => onDirtyChange?.(dirty), [dirty, onDirtyChange]);

  function update(key, value) {
    setDraft((d) => ({ ...d, [key]: value }));
    setSaved(false);
  }
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const updated = await saveCity(city.slug, {
        version,
        ...Object.fromEntries(changed.map((key) => [key, draft[key]])),
      });
      setVersion(updated.version);
      setBaseline(cityDraft(updated));
      // Preserve newer typing if a request completes while the user edits.
      setDraft((current) =>
        JSON.stringify(current) === JSON.stringify(draft)
          ? cityDraft(updated)
          : current,
      );
      setSaved(true);
      onSaved?.(updated);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <UnsavedChangesGuard dirty={dirty} />
      <form onSubmit={submit} className="hub-form">
        <fieldset className="hub-editor-fields" disabled={busy}>
          <CityGeneralFields
            draft={draft}
            update={update}
            section={section}
            city={city}
          />
          {section === "location" && city.capabilities.manage_location && (
            <CityLocationFields
              slug={city.slug}
              location={draft.location}
              onChange={(v) => update("location", v)}
            />
          )}
          {section === "contacts" && (
            <CityContactsEditor
              contacts={draft.contacts}
              onChange={(v) => update("contacts", v)}
            />
          )}
        </fieldset>
        {error && (
          <p role="alert" className="hub-error">
            {error}
          </p>
        )}
        <p role="status">
          {dirty
            ? "Есть несохранённые изменения."
            : saved
              ? city.status === "active"
                ? "Изменения опубликованы."
                : "Изменения сохранены."
              : ""}
        </p>
        <div className="hub-actions">
          <Button type="submit" view="action" loading={busy} disabled={!dirty}>
            {city.status === "active"
              ? "Сохранить и опубликовать"
              : "Сохранить изменения"}
          </Button>
          <Button onClick={() => setPreview((v) => !v)}>
            {preview ? "Скрыть предпросмотр" : "Предпросмотр"}
          </Button>
          <Button
            disabled={busy || !dirty}
            onClick={() => {
              setDraft(baseline);
              setError("");
            }}
          >
            Отменить изменения
          </Button>
        </div>
      </form>
      {preview && (
        <section className="hub-form">
          <h2>Предпросмотр страницы</h2>
          {section === "appearance" ? (
            <>
              <HubImage src={draft.cover_url} alt="Обложка" cover />
              <HubImage src={draft.logo_url} alt={draft.name} />
            </>
          ) : (
            <>
              <h3>{draft.name}</h3>
              <p>{draft.short_description}</p>
              <Markdown>
                {section === "join" ? draft.how_to_join : draft.description}
              </Markdown>
            </>
          )}
        </section>
      )}
    </>
  );
}
