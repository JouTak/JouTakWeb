import { Button } from "@gravity-ui/uikit";
import { useState } from "react";

import { createCity } from "../../services/api/moderationApi";
import { extractErrorMessage } from "../../services/errors";
import { TextField } from "./CityEditorFields";

export default function CityCreateForm({ onCreated }) {
  const [draft, setDraft] = useState({
    name: "",
    slug: "",
    community_slug: "itmocraft",
    manager_username: "",
    short_description: "",
    status: "draft",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const update = (key, value) => setDraft((d) => ({ ...d, [key]: value }));
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      onCreated(await createCity(draft));
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className="hub-panel hub-form" onSubmit={submit}>
      <h2>Новый город</h2>
      <TextField
        label="Название города"
        value={draft.name}
        onChange={(v) => update("name", v)}
        required
        maxLength={120}
      />
      <TextField
        label="Адрес города · slug"
        value={draft.slug}
        onChange={(v) => update("slug", v)}
        pattern="[a-z0-9]+(-[a-z0-9]+)*"
        required
        maxLength={80}
      />
      <TextField
        label="Сообщество · slug"
        value={draft.community_slug}
        onChange={(v) => update("community_slug", v)}
        required
        maxLength={80}
      />
      <TextField
        label="Username управляющего"
        value={draft.manager_username}
        onChange={(v) => update("manager_username", v)}
        required
        maxLength={150}
      />
      <p className="hub-muted">
        При создании управляющий будет включён в сообщество, если ещё не состоит
        в нём.
      </p>
      <TextField
        label="Короткое описание"
        value={draft.short_description}
        onChange={(v) => update("short_description", v)}
        required
        maxLength={280}
      />
      <label>
        Публикация
        <select
          value={draft.status}
          onChange={(e) => update("status", e.target.value)}
        >
          <option value="draft">Черновик</option>
          <option value="active">Опубликовать</option>
        </select>
      </label>
      {error && (
        <p role="alert" className="hub-error">
          {error}
        </p>
      )}
      <Button type="submit" view="action" loading={busy}>
        Создать город
      </Button>
    </form>
  );
}
