import { Button, SegmentedRadioGroup } from "@gravity-ui/uikit";
import { useState } from "react";

import { getGameData, saveGameData } from "../../services/api/profilesApi";
import { TextField } from "../cities/CityEditorFields";
import EditDialog from "../hub/EditDialog";
import UnsavedChangesGuard from "../hub/UnsavedChangesGuard";
import ProfileDraftStatus from "./ProfileDraftStatus";
import useProfileDraft from "./useProfileDraft";

const sections = {
  game: ["minecraft_nick", "minecraft_has_license"],
  social: ["vk_username"],
  itmo: ["is_itmo_student", "itmo_isu"],
};
const labels = {
  minecraft_nick: "Ник Minecraft",
  minecraft_has_license: "Лицензия",
  vk_username: "Учётный VK",
  is_itmo_student: "Студент ИТМО",
  itmo_isu: "ИСУ",
};
export default function GameDataEditor({ profile, section, onClose, onSaved }) {
  const [busy, setBusy] = useState(false);
  const editor = useProfileDraft({
    initial: profile,
    fields: sections[section],
    load: getGameData,
    save: saveGameData,
    onSaved,
    onBusyChange: setBusy,
  });
  const { draft, update } = editor;
  const choice = (key, caption) => (
    <fieldset>
      <legend>{caption}</legend>
      <SegmentedRadioGroup
        value={draft[key] === null ? undefined : String(draft[key])}
        onUpdate={(value) => {
          update(key, value === "true");
          if (key === "is_itmo_student" && value === "false")
            update("itmo_isu", "");
        }}
        options={[
          { value: "true", content: "Да" },
          { value: "false", content: "Нет" },
        ]}
      />
    </fieldset>
  );
  return (
    <EditDialog
      title={
        section === "game"
          ? "Minecraft"
          : section === "social"
            ? "Учётные данные VK"
            : "Данные ИТМО"
      }
      dirty={editor.dirty}
      busy={busy}
      onClose={onClose}
    >
      <form className="hub-form" onSubmit={editor.submit}>
        <UnsavedChangesGuard dirty={editor.dirty} />
        <fieldset disabled={busy} className="hub-editor-fields">
          {section === "game" && (
            <>
              <TextField
                label="Ник Minecraft"
                value={draft.minecraft_nick || ""}
                onChange={(v) => update("minecraft_nick", v)}
                required
                pattern="[A-Za-z0-9_]{3,16}"
                maxLength={16}
              />
              {choice("minecraft_has_license", "Есть лицензия Minecraft?")}
            </>
          )}
          {section === "social" && (
            <>
              <p>
                Это значение прежней анкеты аккаунта. Контакт для других игроков
                и его аудитория настраиваются в «Контактах для связи».
              </p>
              <TextField
                label="Учётное имя VK"
                value={draft.vk_username || ""}
                onChange={(v) => update("vk_username", v)}
                maxLength={100}
              />
            </>
          )}
          {section === "itmo" && (
            <>
              {choice("is_itmo_student", "Учитесь в ИТМО?")}
              {draft.is_itmo_student === true && (
                <TextField
                  label="Номер ИСУ · виден только вам"
                  value={draft.itmo_isu || ""}
                  onChange={(v) => update("itmo_isu", v)}
                  required
                  pattern="[0-9]{5,20}"
                  maxLength={20}
                />
              )}
            </>
          )}
        </fieldset>
        <ProfileDraftStatus editor={editor} labels={labels} />
        <Button
          type="submit"
          view="action"
          disabled={!editor.dirty || editor.conflict}
          loading={busy}
        >
          Сохранить
        </Button>
      </form>
    </EditDialog>
  );
}
