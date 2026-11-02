import { useCallback, useState } from "react";
import { Link } from "react-router-dom";

import { getGroupPeople } from "../../services/api/groupsApi";
import { getPlayerName } from "../../utils/playerIdentity";
import { Pager, ResourceState } from "../hub/HubShell";
import { HubImage } from "../hub/SafeContent";
import useResource from "../hub/useResource";
import { groupRoles } from "./labels";

export default function GroupPeople({ slug }) {
  const [page, setPage] = useState(1);
  const resource = useResource(
    useCallback(() => getGroupPeople(slug, page), [slug, page]),
  );
  return (
    <section className="hub-panel">
      <h2>Люди</h2>
      <ResourceState resource={resource}>
        {resource.data && (
          <>
            {!resource.data.is_visible ? (
              <p className="hub-muted">
                Состав ограничен настройками объединения. Закрытые профили здесь
                не раскрываются.
              </p>
            ) : (
              <>
                <p className="hub-muted">
                  Открытые профили: {resource.data.total}
                </p>
                {resource.data.total === 0 && (
                  <p>Участники пока не открыли свои профили в этом списке.</p>
                )}
                <ul className="group-people">
                  {resource.data.items.map((person, index) => (
                    <li key={person.username || index}>
                      <div className="hub-identity">
                        <HubImage
                          src={person.avatar_url}
                          alt={getPlayerName(person)}
                        />
                        <div>
                          {person.username ? (
                            <Link
                              to={`/u/${encodeURIComponent(person.username)}`}
                            >
                              {getPlayerName(person)}
                            </Link>
                          ) : (
                            getPlayerName(person)
                          )}
                          <p className="hub-muted">{groupRoles[person.role]}</p>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
                <Pager
                  page={page}
                  total={resource.data.total}
                  onChange={setPage}
                />
              </>
            )}
          </>
        )}
      </ResourceState>
    </section>
  );
}
