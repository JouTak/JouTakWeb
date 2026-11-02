import { Button, TextArea, TextInput } from "@gravity-ui/uikit";
import { useEffect, useState } from "react";

import {
  getSelfProfile,
  saveCommunityProfile,
  uploadProfileImage,
} from "../../services/api/profilesApi";
import ImagePicker from "../hub/ImagePicker";
import { visibilityLabels } from "../hub/labels";
import UnsavedChangesGuard from "../hub/UnsavedChangesGuard";
import ProfileDraftStatus from "./ProfileDraftStatus";
import ProfileHero from "./ProfileHero";
import useProfileDraft from "./useProfileDraft";

const visibilityFields = {
  visibility: "Кто видит профиль",
  minecraft_visibility: "Данные Minecraft: ник и стаж",
  itmo_visibility: "Статус студента ИТМО",
  memberships_visibility: "Сообщества и города",
  connections_visibility: "Подписчики, друзья и подписки",
};
export default function ProfileEditor({
  profile,
  section = "about",
  onSaved,
  onDirtyChange,
  onBusyChange,
}) {
  const fields =
    section === "about"
      ? ["display_name", "bio", "avatar_url"]
      : Object.keys(visibilityFields);
  const [uploading, setUploading] = useState(false);
  const editor = useProfileDraft({
    initial: profile,
    fields,
    load: getSelfProfile,
    save: saveCommunityProfile,
    onSaved,
    onDirtyChange,
  });
  useEffect(
    () => onBusyChange?.(editor.busy || uploading),
    [editor.busy, uploading, onBusyChange],
  );
  const { draft, dirty, busy, update } = editor;
  return (
    <form
      className="hub-form"
      onSubmit={(event) => {
        if (uploading) event.preventDefault();
        else editor.submit(event);
      }}
    >
      <UnsavedChangesGuard dirty={dirty} />
      <fieldset className="hub-editor-fields" disabled={busy}>
        {section === "about" && (
          <>
            <label htmlFor="profile-display_name">
              Отображаемое имя
              <TextInput
                id="profile-display_name"
                value={draft.display_name}
                maxLength={100}
                onUpdate={(v) => update("display_name", v)}
              />
            </label>
            <label htmlFor="profile-bio">
              О себе
              <TextArea
                id="profile-bio"
                value={draft.bio}
                maxLength={2000}
                rows={4}
                onUpdate={(v) => update("bio", v)}
              />
            </label>
            <ImagePicker
              label="Аватар"
              value={draft.avatar_url}
              onChange={(v) => update("avatar_url", v)}
              upload={uploadProfileImage}
              onBusyChange={setUploading}
            />
            <p className="hub-muted">
              Загруженный аватар появится в профиле после сохранения. Имя
              необязательно и не должно быть настоящим ФИО.
            </p>
            <details>
              <summary>Предпросмотр оформления</summary>
              <ProfileHero profile={{ ...profile, ...draft }} />
            </details>
          </>
        )}
        {section === "privacy" && (
          <>
            <p>
              Общая видимость профиля ограничивает и его отдельные поля. Email и
              номер ИСУ всегда закрыты. «Участники серверов» — люди из общих
              действующих серверных сообществ; дружба и общий клуб этот доступ
              не дают. Аудитория каждого контакта выбирается в разделе
              контактов.
            </p>
            <fieldset>
              <legend>Видимость</legend>
              {Object.entries(visibilityFields).map(([key, label]) => (
                <label key={key}>
                  {label}
                  <select
                    value={draft[key]}
                    onChange={(e) => update(key, e.target.value)}
                  >
                    {Object.entries(visibilityLabels).map(([value, text]) => (
                      <option key={value} value={value}>
                        {text}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
            </fieldset>
          </>
        )}
      </fieldset>
      <ProfileDraftStatus
        editor={editor}
        labels={{
          ...visibilityFields,
          display_name: "Имя",
          bio: "О себе",
          avatar_url: "Аватар",
        }}
      />
      <div className="hub-actions">
        <Button
          type="submit"
          view="action"
          loading={busy}
          disabled={!dirty || editor.conflict || uploading}
        >
          {section === "about" ? "Сохранить описание" : "Сохранить приватность"}
        </Button>
        <Button disabled={!dirty || busy} onClick={editor.reset}>
          Отменить изменения
        </Button>
      </div>
    </form>
  );
}
