import { useCallback } from "react";
import { Link, useParams } from "react-router-dom";

import { HubPage, ResourceState } from "../../components/hub/HubShell";
import useResource from "../../components/hub/useResource";
import ProfileView from "../../components/profile/ProfileView";
import { useHub } from "../../features/hub/context";
import { getPublicProfile } from "../../services/api/profilesApi";
import { getPlayerName } from "../../utils/playerIdentity";

export default function PublicProfile() {
  const { username } = useParams();
  const { profileRevision } = useHub();
  const resource = useResource(
    useCallback(() => {
      void profileRevision;
      return getPublicProfile(username);
    }, [username, profileRevision]),
  );
  const profile = resource.data;
  if (resource.error?.response?.status === 404)
    return (
      <HubPage title="Профиль недоступен">
        <p>Эта страница недоступна для просмотра.</p>
        <Link to="/players">Вернуться к игрокам</Link>
      </HubPage>
    );
  return (
    <HubPage
      title={
        profile
          ? profile.is_self
            ? "Мой профиль"
            : getPlayerName(profile)
          : "Профиль"
      }
      hero={!!profile}
    >
      <ResourceState resource={resource}>
        {profile && <ProfileView key={username} profile={profile} />}
      </ResourceState>
    </HubPage>
  );
}
