import { Button, Loader } from "@gravity-ui/uikit";
import { useState } from "react";

import { extractErrorMessage } from "../../services/errors";
import { HubImage } from "./SafeContent";

export default function ImagePicker({
  label,
  value,
  onChange,
  upload,
  cover = false,
  onBusyChange,
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function select(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > 3 * 1024 * 1024) {
      setError("Выберите изображение до 3 МБ.");
      return;
    }
    setBusy(true);
    onBusyChange?.(true);
    setError("");
    try {
      onChange((await upload(file)).url);
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setBusy(false);
      onBusyChange?.(false);
    }
  }
  return (
    <div className="hub-image-picker">
      <HubImage key={value} src={value} alt={label} cover={cover} />
      <label>
        {label}
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp"
          disabled={busy}
          onChange={select}
        />
      </label>
      <small className="hub-muted">
        PNG, JPEG или WebP · до 3 МБ. Изображение доступно по ссылке.
      </small>
      {busy && <Loader size="s" />}
      {value && (
        <Button size="s" onClick={() => onChange("")} disabled={busy}>
          Убрать изображение
        </Button>
      )}
      {error && (
        <p role="alert" className="hub-error">
          {error}
        </p>
      )}
    </div>
  );
}
