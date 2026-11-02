import { Button } from "@gravity-ui/uikit";

import { uploadGroupImage } from "../../services/api/groupsApi";
import ImagePicker from "../hub/ImagePicker";
import { Markdown } from "../hub/SafeContent";
import { GroupSelect, GroupText } from "./GroupFields";
import { groupCategories } from "./labels";

export default function GroupContentFields({ group, section, draft, update }) {
  return (
    <>
      {section === "identity" && (
        <>
          <GroupText
            label="Название"
            value={draft.name}
            onChange={(v) => update("name", v)}
            required
            maxLength={120}
          />
          <GroupText
            label="Короткое описание"
            value={draft.short_description}
            onChange={(v) => update("short_description", v)}
            multiline
            required
            maxLength={280}
            rows={3}
          />
          <GroupSelect
            label="Тип объединения"
            value={draft.category}
            options={groupCategories}
            onChange={(v) => update("category", v)}
          />
        </>
      )}
      {section === "description" && (
        <>
          <GroupText
            label="Чем занимаемся"
            value={draft.description}
            onChange={(v) => update("description", v)}
            multiline
            maxLength={12000}
            rows={10}
          />
          <details>
            <summary>Предпросмотр</summary>
            <Markdown>{draft.description}</Markdown>
          </details>
        </>
      )}
      {section === "welcome" && (
        <>
          <GroupText
            label="Первый шаг после вступления"
            value={draft.welcome}
            onChange={(v) => update("welcome", v)}
            multiline
            maxLength={3000}
            rows={6}
          />
          <p className="hub-muted">
            Это приветствие увидят участники: куда написать и с чего начать.
          </p>
        </>
      )}
      {section === "appearance" && (
        <div className="hub-grid">
          <ImagePicker
            label="Логотип"
            value={draft.logo_url}
            upload={(file) => uploadGroupImage(group.slug, file)}
            onChange={(v) => update("logo_url", v)}
          />
          <ImagePicker
            label="Обложка"
            cover
            value={draft.cover_url}
            upload={(file) => uploadGroupImage(group.slug, file)}
            onChange={(v) => update("cover_url", v)}
          />
        </div>
      )}
      {section === "contacts" && (
        <>
          {draft.contacts.map((contact, index) => {
            const change = (key, value) =>
              update(
                "contacts",
                draft.contacts.map((item, i) =>
                  i === index ? { ...item, [key]: value } : item,
                ),
              );
            return (
              <fieldset className="hub-panel" key={index}>
                <legend>Контакт {index + 1}</legend>
                <GroupSelect
                  label="Сервис"
                  value={contact.type}
                  options={{
                    discord: "Discord",
                    telegram: "Telegram",
                    vk: "VK",
                  }}
                  onChange={(v) => change("type", v)}
                />
                <GroupText
                  label="Назначение контакта"
                  value={contact.label}
                  onChange={(v) => change("label", v)}
                  required
                  maxLength={100}
                  placeholder="Общий чат"
                />
                <GroupText
                  label="Ссылка"
                  type="url"
                  value={contact.url}
                  onChange={(v) => change("url", v)}
                  required
                  maxLength={500}
                />
                <GroupSelect
                  label="Кому виден контакт"
                  value={contact.visibility}
                  options={{ public: "Всем", members: "Участникам" }}
                  onChange={(v) => change("visibility", v)}
                />
                <Button
                  view="flat-danger"
                  onClick={() =>
                    update(
                      "contacts",
                      draft.contacts.filter((_, i) => i !== index),
                    )
                  }
                >
                  Убрать контакт
                </Button>
              </fieldset>
            );
          })}
          {draft.contacts.length < 8 && (
            <Button
              onClick={() =>
                update("contacts", [
                  ...draft.contacts,
                  {
                    type: "discord",
                    label: "",
                    url: "",
                    visibility: "members",
                  },
                ])
              }
            >
              Добавить контакт
            </Button>
          )}
          <p className="hub-muted">
            Публикуйте ссылки на чат или контакт организаторов с их согласия.
          </p>
        </>
      )}
    </>
  );
}
