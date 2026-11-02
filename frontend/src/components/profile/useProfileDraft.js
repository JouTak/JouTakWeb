import { useEffect, useState } from "react";

import { extractErrorMessage } from "../../services/errors";

export default function useProfileDraft({
  initial,
  fields,
  load,
  save,
  onSaved,
  onDirtyChange,
  onBusyChange,
}) {
  const select = (value) =>
    Object.fromEntries(
      fields.map((key) => [key, value[key] === undefined ? "" : value[key]]),
    );
  const [saved, setSaved] = useState(() => select(initial));
  const [draft, setDraft] = useState(() => select(initial));
  const [version, setVersion] = useState(initial.version);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(false);
  const [latest, setLatest] = useState(null);
  const [message, setMessage] = useState("");
  const changed = Object.fromEntries(
    fields
      .filter(
        (key) => JSON.stringify(draft[key]) !== JSON.stringify(saved[key]),
      )
      .map((key) => [key, draft[key]]),
  );
  const dirty = Object.keys(changed).length > 0;
  useEffect(() => onDirtyChange?.(dirty), [dirty, onDirtyChange]);
  useEffect(() => onBusyChange?.(busy), [busy, onBusyChange]);
  const update = (key, value) => {
    setDraft((d) => ({ ...d, [key]: value }));
    setMessage("");
  };
  async function submit(event) {
    event.preventDefault();
    if (busy || conflict || !dirty) return;
    setBusy(true);
    setError("");
    try {
      const updated = await save({ version, ...changed });
      const normalized = select(updated);
      setSaved(normalized);
      setDraft(normalized);
      setVersion(updated.version);
      setConflict(false);
      setLatest(null);
      setMessage("Изменения сохранены.");
      onSaved?.(updated);
    } catch (err) {
      setError(extractErrorMessage(err));
      setConflict(err?.response?.status === 409);
    } finally {
      setBusy(false);
    }
  }
  async function compare() {
    if (busy) return;
    setBusy(true);
    try {
      setLatest(await load());
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }
  function resolve(keep) {
    const current = select(latest);
    setSaved(current);
    setDraft(keep ? { ...current, ...changed } : current);
    setVersion(latest.version);
    setLatest(null);
    setConflict(false);
    setError("");
  }
  return {
    draft,
    saved,
    changed,
    busy,
    error,
    conflict,
    latest,
    message,
    dirty,
    update,
    submit,
    compare,
    resolve,
    reset: () => {
      setDraft(saved);
      setError("");
      setMessage("");
    },
  };
}
