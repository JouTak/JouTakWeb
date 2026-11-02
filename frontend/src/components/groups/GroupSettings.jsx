import { Button } from "@gravity-ui/uikit";
import { useState } from "react";

import { changeGroupLifecycle, saveGroup } from "../../services/api/groupsApi";
import UnsavedChangesGuard from "../hub/UnsavedChangesGuard";
import { ConfirmDialog } from "../ui/primitives";
import { GroupSelect, GroupText } from "./GroupFields";
import { groupAccess, groupModes, rosterVisibility } from "./labels";
import useGroupAction from "./useGroupAction";

export default function GroupSettings({ group, onSaved }) {
  const keys = [
    "access",
    "join_mode",
    "accepting",
    "roster_visibility",
    "rules",
    "application_question",
  ];
  const initial = Object.fromEntries(keys.map((key) => [key, group[key]]));
  const [draft, setDraft] = useState(initial);
  const [confirm, setConfirm] = useState(null);
  const action = useGroupAction(onSaved);
  const dirty = JSON.stringify(initial) !== JSON.stringify(draft);
  const update = (key, value) =>
    setDraft((old) => ({
      ...old,
      [key]: value,
      ...(key === "access" && value === "private"
        ? { join_mode: "invite_only" }
        : {}),
    }));
  const save = () =>
    action.run(
      () => saveGroup(group.slug, { version: group.version, ...draft }),
      "Условия участия сохранены",
      () => setConfirm(null),
    );
  const lifecycleText = {
    publish: "Опубликовать объединение",
    archive: "Отправить в архив",
    restore: "Восстановить объединение",
  };
  return (
    <div className="group-section">
      {group.status !== "archived" && (
        <form
          className="hub-panel hub-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (
              draft.access !== group.access ||
              draft.roster_visibility !== group.roster_visibility ||
              draft.join_mode !== group.join_mode ||
              draft.accepting !== group.accepting
            )
              setConfirm("settings");
            else save();
          }}
        >
          <UnsavedChangesGuard dirty={dirty} />
          <fieldset
            className="group-editor-fields"
            disabled={action.busy || !group.capabilities.configure}
          >
            <h2>Доступ и набор</h2>
            <GroupSelect
              label="Кому доступна страница"
              value={draft.access}
              options={groupAccess}
              onChange={(v) => update("access", v)}
            />
            <p className="hub-muted">
              {draft.access === "private"
                ? "Только участники. Приглашённый получит лишь краткое предложение."
                : draft.access === "unlisted"
                  ? "Доступна любому по ссылке. В общем каталоге не показывается; ссылка не является секретом."
                  : "Страница появится в общем каталоге после публикации."}
            </p>
            <GroupSelect
              label="Способ вступления"
              value={draft.join_mode}
              options={
                draft.access === "private"
                  ? { invite_only: groupModes.invite_only }
                  : groupModes
              }
              onChange={(v) => update("join_mode", v)}
            />
            <GroupSelect
              label="Приём участников"
              value={String(draft.accepting)}
              options={{ true: "Принимать", false: "На паузе" }}
              onChange={(v) => update("accepting", v === "true")}
            />
            <GroupSelect
              label="Кто видит состав"
              value={draft.roster_visibility}
              options={rosterVisibility}
              onChange={(v) => update("roster_visibility", v)}
            />
            <p className="hub-muted">
              Личные настройки участников продолжают действовать. Закрытые
              профили не станут публичными.
            </p>
            <GroupText
              label="Условия участия"
              value={draft.rules}
              onChange={(v) => update("rules", v)}
              multiline
              rows={5}
              maxLength={3000}
            />
            {draft.join_mode === "approval" && (
              <GroupText
                label="Один вопрос для заявки (необязательно)"
                value={draft.application_question}
                onChange={(v) => update("application_question", v)}
                maxLength={300}
              />
            )}
            <Button
              view="action"
              type="submit"
              loading={action.busy}
              disabled={!dirty || !group.capabilities.configure}
            >
              Сохранить условия
            </Button>
          </fieldset>
        </form>
      )}
      <section className="hub-panel">
        <h2>Публикация</h2>
        <p>
          {group.status === "draft"
            ? "Черновик пока виден руководству. Проверьте публичный вид и условия."
            : group.status === "archived"
              ? "История сохранена. При восстановлении набор останется на паузе."
              : "Изменения страницы публикуются после сохранения и остаются в истории."}
        </p>
        <Button
          disabled={!group.capabilities.configure || dirty}
          onClick={() =>
            setConfirm(
              group.status === "draft"
                ? "publish"
                : group.status === "active"
                  ? "archive"
                  : "restore",
            )
          }
        >
          {
            lifecycleText[
              group.status === "draft"
                ? "publish"
                : group.status === "active"
                  ? "archive"
                  : "restore"
            ]
          }
        </Button>
        {dirty && <p className="hub-muted">Сначала сохраните настройки.</p>}
      </section>
      {action.error && <p role="alert">{action.error}</p>}
      <ConfirmDialog
        open={!!confirm}
        title={
          confirm === "settings"
            ? "Изменить условия участия?"
            : lifecycleText[confirm] || "Публикация"
        }
        confirmText={
          confirm === "settings" ? "Сохранить условия" : lifecycleText[confirm]
        }
        onCancel={() => setConfirm(null)}
        loading={action.busy}
        onConfirm={() =>
          confirm === "settings"
            ? save()
            : action.run(
                () =>
                  changeGroupLifecycle(group.slug, {
                    version: group.version,
                    action: confirm,
                  }),
                confirm === "archive"
                  ? "Объединение в архиве"
                  : "Состояние обновлено",
                () => setConfirm(null),
              )
        }
      >
        <p>
          {confirm === "archive"
            ? "Новые вступления прекратятся. Незавершённые заявки, приглашения и предложения руководства будут закрыты. Данные сохранятся."
            : confirm === "restore"
              ? "Старые заявки и приглашения не возобновятся. Приём участников нужно включить отдельно."
              : `${groupAccess[draft.access]}. Вступление: ${groupModes[draft.join_mode]}. Состав: ${rosterVisibility[draft.roster_visibility]}.`}
        </p>
        {!draft.accepting && confirm === "settings" && (
          <p>
            Принять старое приглашение или одобрить заявку на паузе нельзя.
            Отказы и отзывы останутся доступны.
          </p>
        )}
        {action.error && <p role="alert">{action.error}</p>}
      </ConfirmDialog>
    </div>
  );
}
