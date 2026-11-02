import { Button, TextArea, TextInput } from "@gravity-ui/uikit";
import { useId } from "react";

import { uploadCityImage } from "../../services/api/citiesApi";
import ImagePicker from "../hub/ImagePicker";
import { recruitmentLabels, visibilityLabels } from "../hub/labels";

export function TextField({
  label,
  value,
  onChange,
  multiline = false,
  ...props
}) {
  const id = useId();
  const Input = multiline ? TextArea : TextInput;
  return (
    <label htmlFor={id}>
      {label}
      <Input id={id} value={value ?? ""} onUpdate={onChange} {...props} />
    </label>
  );
}
export function CityGeneralFields({ draft, update, section, city }) {
  return (
    <>
      {section === "identity" && (
        <>
          <TextField
            label="Название"
            value={draft.name}
            onChange={(v) => update("name", v)}
            required
            maxLength={120}
          />
          <TextField
            label="Короткое описание"
            value={draft.short_description}
            onChange={(v) => update("short_description", v)}
            required
            maxLength={280}
            multiline
            rows={3}
          />
        </>
      )}
      {section === "about" && (
        <>
          <TextField
            label="Описание города"
            value={draft.description}
            onChange={(v) => update("description", v)}
            multiline
            rows={12}
            maxLength={12000}
          />
          <p className="hub-muted">
            Расскажите о городе, его районах и проектах. Можно использовать
            заголовки, списки и ссылки Markdown.
          </p>
        </>
      )}
      {section === "join" && (
        <>
          <TextField
            label="Условия вступления"
            value={draft.how_to_join}
            onChange={(v) => update("how_to_join", v)}
            multiline
            rows={6}
            maxLength={2000}
          />
          {city.capabilities.manage_location && (
            <label>
              Набор жителей
              <select
                value={draft.recruitment_status}
                onChange={(e) => update("recruitment_status", e.target.value)}
              >
                {Object.entries(recruitmentLabels).map(([v, label]) => (
                  <option key={v} value={v}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          )}
        </>
      )}
      {section === "facts" && (
        <>
          <TextField
            label="Дата основания"
            type="date"
            value={draft.founded_at}
            onChange={(v) => update("founded_at", v || null)}
          />
          <TextField
            label="Регион"
            value={draft.region}
            onChange={(v) => update("region", v)}
            maxLength={120}
          />
        </>
      )}
      {section === "appearance" && (
        <>
          <ImagePicker
            label="Логотип города"
            value={draft.logo_url}
            onChange={(v) => update("logo_url", v)}
            upload={(file) => uploadCityImage(city.slug, file)}
          />
          <ImagePicker
            label="Обложка города"
            value={draft.cover_url}
            onChange={(v) => update("cover_url", v)}
            upload={(file) => uploadCityImage(city.slug, file)}
            cover
          />
        </>
      )}
    </>
  );
}
const contactTypes = {
  discord: "Discord · приглашение",
  telegram: "Telegram",
  vk: "VK",
};
export function CityContactsEditor({ contacts, onChange }) {
  const update = (index, key, value) =>
    onChange(
      contacts.map((c, i) => (i === index ? { ...c, [key]: value } : c)),
    );
  return (
    <>
      <p className="hub-muted">
        Где связаться с администрацией или познакомиться с жителями.
      </p>
      {contacts.map((c, index) => (
        <fieldset key={index}>
          <legend>Контакт {index + 1}</legend>
          <label>
            Сервис
            <select
              value={c.type}
              onChange={(e) => update(index, "type", e.target.value)}
            >
              {!contactTypes[c.type] && (
                <option value={c.type}>Старая ссылка — выберите сервис</option>
              )}
              {Object.entries(contactTypes).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <TextField
            label="Подпись"
            value={c.label}
            required
            maxLength={100}
            onChange={(v) => update(index, "label", v)}
          />
          <TextField
            label={
              c.type === "discord"
                ? "Ссылка-приглашение Discord"
                : "Ссылка на страницу"
            }
            value={c.url}
            required
            type="url"
            maxLength={500}
            placeholder={
              c.type === "discord"
                ? "https://discord.gg/…"
                : c.type === "telegram"
                  ? "https://t.me/…"
                  : "https://vk.com/…"
            }
            onChange={(v) => update(index, "url", v)}
          />
          <label>
            Кому доступен контакт
            <select
              value={c.visibility}
              onChange={(e) => update(index, "visibility", e.target.value)}
            >
              {Object.entries(visibilityLabels).map(([v, label]) => (
                <option key={v} value={v}>
                  {v === "private" ? "Только редакторам города" : label}
                </option>
              ))}
            </select>
          </label>
          <Button
            onClick={() => onChange(contacts.filter((_, i) => i !== index))}
          >
            Убрать контакт
          </Button>
        </fieldset>
      ))}
      <Button
        disabled={contacts.length >= 20}
        onClick={() =>
          onChange([
            ...contacts,
            {
              type: "discord",
              label: "Discord города",
              url: "",
              visibility: "public",
            },
          ])
        }
      >
        Добавить контакт
      </Button>
    </>
  );
}
