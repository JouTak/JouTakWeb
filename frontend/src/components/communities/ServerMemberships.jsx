import { Link } from "react-router-dom";

import { getServerMemberships } from "../../services/api/communitiesApi";
import { ResourceState } from "../hub/HubShell";
import { communityRoles } from "../hub/labels";
import useResource from "../hub/useResource";

const statuses = {
  active: "Участие действует",
  pending: "Участие ожидает подтверждения",
  suspended: "Участие приостановлено",
  left: "Участие завершено",
};
export default function ServerMemberships() {
  const resource = useResource(getServerMemberships);
  return (
    <section className="group-section">
      <h2>Сообщества серверов</h2>
      <ResourceState resource={resource}>
        {resource.data && (
          <>
            <div className="hub-grid">
              {resource.data.items.map((member) => (
                <article className="hub-panel" key={member.community.slug}>
                  <h3>
                    <Link to={`/communities/${member.community.slug}`}>
                      {member.community.name}
                    </Link>
                  </h3>
                  <p>{statuses[member.status]}</p>
                  {member.status === "active" ? (
                    <p className="hub-muted">{communityRoles[member.role]}</p>
                  ) : (
                    <p className="hub-muted">
                      Доступ к связанным городам и объединениям определяется
                      действующим серверным участием.
                    </p>
                  )}
                </article>
              ))}
            </div>
            {!resource.data.items.length && (
              <p className="hub-muted">
                Серверное участие пока не оформлено. Порядок вступления указан
                на странице соответствующего сообщества.
              </p>
            )}
          </>
        )}
      </ResourceState>
    </section>
  );
}
