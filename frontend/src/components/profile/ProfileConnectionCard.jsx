import { Button, Tooltip } from "@gravity-ui/uikit";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { getConnections } from "../../services/api/playersApi";
import { extractErrorMessage } from "../../services/errors";
import { getPlayerName } from "../../utils/playerIdentity";
import { Pager } from "../hub/HubShell";
import useResource from "../hub/useResource";
import ProfileAvatar from "./ProfileAvatar";

export default function ProfileConnectionCard({
  username,
  direction,
  title,
  revision = 0,
  load = getConnections,
}) {
  const [page, setPage] = useState(1);
  const headingId = useId();
  const resource = useResource(
    useCallback(
      () => load(username, direction, page),
      [username, direction, page, load],
    ),
    { retainOnReload: true },
  );
  const { reload } = resource;
  const previous = useRef(revision);
  useEffect(() => {
    if (previous.current !== revision) {
      previous.current = revision;
      reload();
    }
  }, [revision, reload]);
  const data = resource.data;
  useEffect(() => {
    if (data?.is_visible && page > 1 && (page - 1) * 24 >= data.total)
      setPage(Math.max(1, Math.ceil(data.total / 24)));
  }, [data, page]);
  return (
    <section className="profile-connection-card" aria-labelledby={headingId}>
      <div className="hub-panel profile-stat-card">
        <div className="profile-stat-heading">
          <h2 id={headingId}>{title}</h2>
          {data?.is_visible && (
            <output
              className="profile-connection-count"
              aria-label={`${title}: ${data.total}`}
            >
              {data.total}
            </output>
          )}
        </div>
        {resource.loading && !data ? (
          <p className="hub-muted" role="status">
            Загрузка…
          </p>
        ) : resource.error ? (
          <div className="profile-stat-error">
            <p role="alert">{extractErrorMessage(resource.error)}</p>
            <Button size="s" view="flat" onClick={resource.reload}>
              Повторить
            </Button>
          </div>
        ) : (
          <p className="hub-muted">
            {!data?.is_visible
              ? "Список скрыт"
              : direction === "friends"
                ? "Взаимная подписка"
                : "Следят за профилем"}
          </p>
        )}
      </div>
      {data?.is_visible && (
        <>
          {data.items.length > 0 && (
            <ul className="profile-avatar-grid" aria-label={title}>
              {data.items.map((player) => (
                <li key={player.username}>
                  <Tooltip content={`@${getPlayerName(player)}`}>
                    <Link
                      to={`/u/${encodeURIComponent(player.username)}`}
                      aria-label={`Профиль @${getPlayerName(player)}`}
                    >
                      <ProfileAvatar profile={player} />
                    </Link>
                  </Tooltip>
                </li>
              ))}
            </ul>
          )}
          <Pager page={page} total={data.total} onChange={setPage} />
        </>
      )}
    </section>
  );
}
