import { Button } from "@gravity-ui/uikit";
import { useState } from "react";

import { saveCity } from "../../services/api/citiesApi";
import { extractErrorMessage } from "../../services/errors";
import { cityStatuses } from "../hub/labels";
import { ConfirmDialog } from "../ui/primitives";
export default function CityPublication({ city, onSaved }) {
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save() {
    setBusy(true);
    setError("");
    try {
      onSaved(await saveCity(city.slug, { version: city.version, status }));
      setStatus(null);
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="hub-panel">
      <h2>Публикация города</h2>
      <p>Сейчас: {cityStatuses[city.status]}</p>
      <p>Архивирование скроет страницу и сохранит историю.</p>
      <div className="hub-actions">
        {city.status !== "active" && (
          <Button onClick={() => setStatus("active")}>Опубликовать</Button>
        )}
        {city.status !== "archived" && (
          <Button view="outlined-danger" onClick={() => setStatus("archived")}>
            Архивировать
          </Button>
        )}
      </div>
      <ConfirmDialog
        open={!!status}
        title={
          status === "archived" ? "Архивировать город?" : "Опубликовать город?"
        }
        loading={busy}
        onCancel={() => setStatus(null)}
        onConfirm={save}
      >
        <p>
          {status === "archived"
            ? "Город исчезнет из каталога и кабинетов жителей. Управляющие потеряют доступ к редактированию. Восстановить город сможет модератор."
            : "Страница города станет доступна в каталоге."}
        </p>
        {error && <p role="alert">{error}</p>}
      </ConfirmDialog>
    </section>
  );
}
