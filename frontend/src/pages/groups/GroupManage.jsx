import "../../components/groups/groups.css";

import { Button } from "@gravity-ui/uikit";
import { useCallback } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import GroupEditor from "../../components/groups/GroupEditor";
import GroupHistory from "../../components/groups/GroupHistory";
import GroupMembersManager from "../../components/groups/GroupMembersManager";
import GroupModeration from "../../components/groups/GroupModeration";
import GroupQueue from "../../components/groups/GroupQueue";
import GroupSettings from "../../components/groups/GroupSettings";
import { HubPage, ResourceState } from "../../components/hub/HubShell";
import useResource from "../../components/hub/useResource";
import { getGroup } from "../../services/api/groupsApi";

export default function GroupManage() {
  const { slug } = useParams();
  const [params, setParams] = useSearchParams();
  const resource = useResource(useCallback(() => getGroup(slug), [slug]));
  const group = resource.data;
  const caps = group?.capabilities || {};
  const tabs = {
    ...(caps.manage
      ? {
          page: "Страница",
          members: "Участники",
          queue: "Заявки и приглашения",
        }
      : {}),
    ...(caps.configure ? { settings: "Условия участия" } : {}),
    ...(caps.moderate || group?.viewer.membership?.role === "manager"
      ? { history: "История" }
      : {}),
    ...(caps.moderate ? { moderation: "Модерация" } : {}),
  };
  const tab = tabs[params.get("tab")]
    ? params.get("tab")
    : Object.keys(tabs)[0];
  return (
    <HubPage
      title={group ? `${group.name}: управление` : "Управление объединением"}
    >
      <Link to={`/groups/${encodeURIComponent(slug)}`}>
        ← Страница объединения
      </Link>
      <ResourceState resource={resource}>
        {group && (
          <>
            {!caps.write_enabled && (
              <p role="status" className="hub-panel">
                Изменения временно приостановлены. Содержимое доступно для
                просмотра.
              </p>
            )}
            {!tab ? (
              <p className="hub-panel">
                У вас нет доступа к управлению этим объединением.
              </p>
            ) : (
              <>
                <nav
                  className="hub-actions group-tabs"
                  aria-label="Управление объединением"
                >
                  {Object.entries(tabs).map(([key, title]) => (
                    <Button
                      key={key}
                      view={tab === key ? "outlined" : "flat-secondary"}
                      onClick={() => setParams({ tab: key })}
                    >
                      {title}
                    </Button>
                  ))}
                </nav>
                {tab === "page" && (
                  <GroupEditor group={group} onSaved={resource.reload} />
                )}
                {tab === "members" && (
                  <GroupMembersManager
                    group={group}
                    onChanged={resource.reload}
                  />
                )}
                {tab === "queue" && <GroupQueue group={group} />}
                {tab === "settings" && (
                  <GroupSettings
                    key={group.version}
                    group={group}
                    onSaved={resource.reload}
                  />
                )}
                {tab === "history" && <GroupHistory slug={slug} />}
                {tab === "moderation" && (
                  <GroupModeration group={group} onChanged={resource.reload} />
                )}
              </>
            )}
          </>
        )}
      </ResourceState>
    </HubPage>
  );
}
