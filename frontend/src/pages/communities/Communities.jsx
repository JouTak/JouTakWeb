import { useCallback, useState } from "react";
import { Link } from "react-router-dom";

import GroupCatalog from "../../components/groups/GroupCatalog";
import { HubPage, Pager, ResourceState } from "../../components/hub/HubShell";
import { HubImage } from "../../components/hub/SafeContent";
import useResource from "../../components/hub/useResource";
import { useHub } from "../../features/hub/context";
import { getCommunities } from "../../services/api/communitiesApi";

export default function Communities() {
  const { flags, viewer } = useHub();
  const [page, setPage] = useState(1);
  const resource = useResource(useCallback(() => getCommunities(page), [page]));
  return (
    <HubPage
      title="Сообщества"
      intro="Сообщества серверов и люди для совместных проектов."
    >
      {viewer?.is_authenticated && (
        <Link to="/account/communities">Моё участие и приглашения →</Link>
      )}
      <h2>Сообщества серверов</h2>
      <ResourceState resource={resource}>
        {resource.data && (
          <>
            <div className="hub-grid">
              {resource.data.items.map((c) => (
                <article key={c.slug} className="hub-panel group-server-card">
                  <HubImage src={c.logo_url} alt={c.name} />
                  <div>
                    <h3>
                      <Link to={`/communities/${c.slug}`}>{c.name}</Link>
                    </h3>
                    <p>{c.short_description}</p>
                  </div>
                </article>
              ))}
            </div>
            {!resource.data.total && (
              <p>Публичные сообщества пока не добавлены.</p>
            )}
            <Pager page={page} total={resource.data.total} onChange={setPage} />
          </>
        )}
      </ResourceState>
      {flags.player_groups_ui && (
        <GroupCatalog communities={resource.data?.items || []} />
      )}
    </HubPage>
  );
}
