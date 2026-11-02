import { Button, SegmentedRadioGroup } from "@gravity-ui/uikit";
import { useState } from "react";

import { parseCityMapLink } from "../../services/api/citiesApi";
import { extractErrorMessage } from "../../services/errors";
import { TextField } from "./CityEditorFields";
export default function CityLocationFields({ location, onChange, slug }) {
  const [mode, setMode] = useState("coordinates");
  const [link, setLink] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const update = (key, value) => onChange({ ...location, [key]: value });
  async function importLink() {
    setBusy(true);
    setError("");
    try {
      onChange(await parseCityMapLink(slug, link));
      setMode("coordinates");
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <SegmentedRadioGroup
        value={mode}
        onUpdate={setMode}
        options={[
          { value: "coordinates", content: "Координаты" },
          { value: "link", content: "Ссылка BlueMap" },
        ]}
      />
      {mode === "link" ? (
        <>
          <TextField
            label="Ссылка на место в BlueMap"
            type="url"
            value={link}
            onChange={setLink}
            placeholder="https://map.joutak.ru/#…"
          />
          <p className="hub-muted">
            Откройте карту, выберите место и скопируйте адрес из браузера. Перед
            сохранением вы увидите координаты.
          </p>
          <Button onClick={importLink} loading={busy} disabled={!link.trim()}>
            Подставить координаты
          </Button>
        </>
      ) : location ? (
        <>
          <p>Основной мир · JouTak SMP</p>
          <div className="hub-coordinate-fields">
            {["x", "z", "y"].map((key) => (
              <TextField
                key={key}
                label={
                  key === "y" ? "Y · высота, необязательно" : key.toUpperCase()
                }
                type="number"
                step="1"
                min={-30000000}
                max={30000000}
                required={key !== "y"}
                value={location[key]}
                onChange={(v) => update(key, v === "" ? null : Number(v))}
              />
            ))}
          </div>
          <p className="hub-muted">
            X и Z — положение на карте. Можно указать центр города или точку
            прибытия.
          </p>
          <Button onClick={() => onChange(null)}>Убрать местоположение</Button>
        </>
      ) : (
        <Button
          onClick={() =>
            onChange({
              world: "overworld",
              x: null,
              z: null,
              y: null,
              map_id: "",
            })
          }
        >
          Указать координаты
        </Button>
      )}
      {error && (
        <p role="alert" className="hub-error">
          {error}
        </p>
      )}
    </>
  );
}
