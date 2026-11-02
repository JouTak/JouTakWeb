import { Button } from "@gravity-ui/uikit";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { HubPage, Pager, ResourceState } from "../../components/hub/HubShell";
import useResource from "../../components/hub/useResource";
import ProfileAvatar from "../../components/profile/ProfileAvatar";
import {
  getOwnFollowing,
  removeOwnFollow,
} from "../../services/api/playersApi";
import { extractErrorMessage } from "../../services/errors";
import { getPlayerName } from "../../utils/playerIdentity";

export default function OwnFollowing() {
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState("");
  const resource = useResource(
    useCallback(() => getOwnFollowing(page), [page]),
  );
  useEffect(() => {
    if (resource.data && page > 1 && (page - 1) * 24 >= resource.data.total)
      setPage(Math.max(1, Math.ceil(resource.data.total / 24)));
  }, [page, resource.data]);
  async function remove(id) {
    setBusy(id);
    setError("");
    try {
      await removeOwnFollow(id);
      resource.reload();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }
  return (
    <HubPage title="Мои подписки" account>
      <p>
        Ваши исходящие подписки, включая взаимные. Отписка снимает только вашу
        сторону связи.
      </p>
      {error && <p role="alert">{error}</p>}
      <ResourceState resource={resource}>
        {resource.data && (
          <>
            {!resource.data.total && (
              <p>
                У вас пока нет подписок.{" "}
                <Link to="/players">Найти игроков →</Link>
              </p>
            )}
            {resource.data.items.map(({ id, profile }) => (
              <article className="hub-panel hub-row" key={id}>
                {profile ? (
                  <Link
                    className="hub-identity"
                    to={`/u/${encodeURIComponent(profile.username)}`}
                  >
                    <ProfileAvatar profile={profile} />
                    {getPlayerName(profile)}
                  </Link>
                ) : (
                  <span>Недоступный профиль</span>
                )}
                <Button
                  loading={busy === id}
                  disabled={busy !== null}
                  onClick={() => remove(id)}
                  extraProps={{
                    "aria-label": profile
                      ? `Отписаться от ${getPlayerName(profile)}`
                      : "Отписаться от недоступного профиля",
                  }}
                >
                  Отписаться
                </Button>
              </article>
            ))}
            <Pager page={page} total={resource.data.total} onChange={setPage} />
          </>
        )}
      </ResourceState>
    </HubPage>
  );
}
