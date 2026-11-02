import "../../components/groups/groups.css";

import { useCallback, useState } from "react";
import { Link } from "react-router-dom";

import { groupAccess, groupStatuses } from "../../components/groups/labels";
import { HubPage, Pager, ResourceState } from "../../components/hub/HubShell";
import useResource from "../../components/hub/useResource";
import { getModerationGroups } from "../../services/api/groupsApi";

export default function GroupsModeration() {
  const [page, setPage] = useState(1);
  const resource = useResource(
    useCallback(() => getModerationGroups(page), [page]),
  );
  return (
    <HubPage
      title="Модерация объединений"
      intro="Состояние страниц, управление и восстановление руководства."
    >
      <Link to="/communities">← Сообщества</Link>
      <ResourceState resource={resource}>
        {resource.data && (
          <>
            {!resource.data.items.length && (
              <p className="hub-panel">Объединений пока нет.</p>
            )}
            <div className="group-grid">
              {resource.data.items.map((group) => (
                <article className="hub-panel" key={group.slug}>
                  <h2>
                    <Link to={`/groups/${group.slug}`}>{group.name}</Link>
                  </h2>
                  <p>
                    {groupStatuses[group.status]} · {groupAccess[group.access]}
                    {group.restricted && " · Ограничено платформой"}
                  </p>
                  <div className="hub-actions">
                    <Link to={`/groups/${group.slug}/manage?tab=moderation`}>
                      Модерация
                    </Link>
                    <Link to={`/groups/${group.slug}/manage?tab=history`}>
                      История
                    </Link>
                  </div>
                </article>
              ))}
            </div>
            <Pager page={page} total={resource.data.total} onChange={setPage} />
          </>
        )}
      </ResourceState>
    </HubPage>
  );
}
