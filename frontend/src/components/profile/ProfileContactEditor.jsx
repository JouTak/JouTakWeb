import { Button, TextInput } from "@gravity-ui/uikit";

import {
  getProfileContacts,
  saveProfileContacts,
} from "../../services/api/playersApi";
import { visibilityLabels } from "../hub/labels";
import UnsavedChangesGuard from "../hub/UnsavedChangesGuard";
import { contactNames } from "./contactLabels";
import ProfileDraftStatus from "./ProfileDraftStatus";
import useProfileDraft from "./useProfileDraft";

export default function ProfileContactEditor({
  initial,
  onSaved,
  onDirtyChange,
  onBusyChange,
}) {
  const editor = useProfileDraft({
    initial,
    fields: ["contacts"],
    load: getProfileContacts,
    save: saveProfileContacts,
    onSaved,
    onDirtyChange,
    onBusyChange,
  });
  const draft = editor.draft.contacts;
  const { busy, dirty } = editor;
  const setDraft = (change) => editor.update("contacts", change(draft));
  const update = (type, key, value) =>
    setDraft((items) =>
      items.map((c) => (c.type === type ? { ...c, [key]: value } : c)),
    );
  return (
    <form className="hub-form" onSubmit={editor.submit}>
      <UnsavedChangesGuard dirty={dirty} />
      <p>
        Выберите, чем поделиться. Общая видимость профиля также ограничивает
        доступ к контактам. Удалённый VK не заменится старым адресом из анкеты.
        Эти контакты не подтверждают владение внешним аккаунтом.
      </p>
      <fieldset className="hub-editor-fields" disabled={busy}>
        {draft.map((contact) => (
          <fieldset key={contact.type}>
            <legend>{contactNames[contact.type]}</legend>
            <label htmlFor={`contact-${contact.type}`}>
              {contact.type === "discord"
                ? "Имя Discord или ссылка на профиль"
                : "Имя пользователя или ссылка"}
              <TextInput
                id={`contact-${contact.type}`}
                value={contact.value}
                onUpdate={(v) => update(contact.type, "value", v)}
                maxLength={200}
                controlProps={{ required: true }}
              />
            </label>
            <label>
              Кто видит контакт
              <select
                value={contact.visibility}
                onChange={(e) =>
                  update(contact.type, "visibility", e.target.value)
                }
              >
                {Object.entries(visibilityLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <Button
              size="s"
              onClick={() =>
                setDraft((items) =>
                  items.filter((c) => c.type !== contact.type),
                )
              }
            >
              Убрать {contactNames[contact.type]}
            </Button>
          </fieldset>
        ))}
        <div className="hub-actions">
          {Object.entries(contactNames)
            .filter(([type]) => !draft.some((c) => c.type === type))
            .map(([type, label]) => (
              <Button
                key={type}
                onClick={() =>
                  setDraft((items) => [
                    ...items,
                    { type, value: "", visibility: "private" },
                  ])
                }
              >
                Добавить {label}
              </Button>
            ))}
        </div>
      </fieldset>
      <ProfileDraftStatus editor={editor} labels={{ contacts: "Контакты" }} />
      <Button
        type="submit"
        view="action"
        loading={busy}
        disabled={!dirty || editor.conflict}
      >
        Сохранить контакты
      </Button>
    </form>
  );
}
