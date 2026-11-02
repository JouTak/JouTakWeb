import { Button } from "@gravity-ui/uikit";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { GroupSelect, GroupText } from "../../components/groups/GroupFields";
import { groupCategories } from "../../components/groups/labels";
import useGroupAction from "../../components/groups/useGroupAction";
import { HubPage, ResourceState } from "../../components/hub/HubShell";
import UnsavedChangesGuard from "../../components/hub/UnsavedChangesGuard";
import useResource from "../../components/hub/useResource";
import { useHub } from "../../features/hub/context";
import { getServerMemberships } from "../../services/api/communitiesApi";
import { createGroup } from "../../services/api/groupsApi";

export default function GroupCreate() {
  const [draft, setDraft] = useState({
    name: "",
    slug: "",
    short_description: "",
    category: "club",
    scope_slug: "",
  });
  const [saved, setSaved] = useState(false);
  const resource = useResource(getServerMemberships);
  const action = useGroupAction();
  const navigate = useNavigate();
  const { flags } = useHub();
  const update = (key, value) => setDraft((old) => ({ ...old, [key]: value }));
  return (
    <HubPage
      title="Новое объединение"
      intro="Соберите людей для общего дела. Сначала сохраним черновик — опубликовать его можно после настройки."
    >
      <Link to="/communities">← Сообщества</Link>
      <UnsavedChangesGuard
        dirty={
          !saved && !!(draft.name || draft.slug || draft.short_description)
        }
      />
      <ResourceState resource={resource}>
        {resource.data && (
          <form
            className="hub-panel hub-form"
            onSubmit={(event) => {
              event.preventDefault();
              action.run(
                () =>
                  createGroup({
                    ...draft,
                    scope_slug: draft.scope_slug || null,
                  }),
                "Черновик создан",
                (group) => {
                  setSaved(true);
                  // Leave the blocker disabled before changing routes.
                  setTimeout(() => navigate(`/groups/${group.slug}/manage`), 0);
                },
              );
            }}
          >
            <GroupText
              label="Название объединения"
              value={draft.name}
              onChange={(v) => update("name", v)}
              maxLength={120}
              required
            />
            <GroupText
              label="Чем будете заниматься"
              value={draft.short_description}
              onChange={(v) => update("short_description", v)}
              multiline
              rows={3}
              maxLength={280}
              required
            />
            <GroupText
              label="Адрес страницы"
              value={draft.slug}
              onChange={(v) => update("slug", v.toLowerCase())}
              maxLength={80}
              pattern="[a-z0-9]+(-[a-z0-9]+)*"
              required
              placeholder="builders"
            />
            <p className="hub-muted">
              Латинские буквы, цифры и дефис. Адрес останется постоянным.
            </p>
            <div className="hub-grid">
              <GroupSelect
                label="Тип объединения"
                value={draft.category}
                onChange={(v) => update("category", v)}
                options={groupCategories}
              />
              <GroupSelect
                label="Контекст"
                value={draft.scope_slug}
                onChange={(v) => update("scope_slug", v)}
                options={{
                  "": "Весь JouTak",
                  ...Object.fromEntries(
                    resource.data.items
                      .filter((m) => m.status === "active")
                      .map((m) => [m.community.slug, m.community.name]),
                  ),
                }}
              />
            </div>
            <p className="hub-muted">
              Вы станете первым руководителем. Ваше участие пока будет видно
              только вам и руководству. Контекст нельзя сменить после создания.
            </p>
            {!flags.player_groups_write && (
              <p>Создание временно приостановлено.</p>
            )}
            {action.error && <p role="alert">{action.error}</p>}
            <Button
              type="submit"
              view="action"
              loading={action.busy}
              disabled={!flags.player_groups_write}
            >
              Сохранить черновик
            </Button>
          </form>
        )}
      </ResourceState>
    </HubPage>
  );
}
