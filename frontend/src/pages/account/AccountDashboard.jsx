import { Link } from "react-router-dom";

import CityInvitations from "../../components/cities/CityInvitations";
import MembershipCards from "../../components/communities/MembershipCards";
import { MyGroups } from "../../components/groups/AccountGroups";
import { HubPage, ResourceState } from "../../components/hub/HubShell";
import { HubImage } from "../../components/hub/SafeContent";
import useResource from "../../components/hub/useResource";
import { useHub } from "../../features/hub/context";
import { getSelfProfile } from "../../services/api/profilesApi";
import { getPlayerName } from "../../utils/playerIdentity";

export default function AccountDashboard() {
  const resource = useResource(getSelfProfile);
  const { flags } = useHub();
  const profile = resource.data;
  return (
    <HubPage title="Личный кабинет" hero>
      <ResourceState resource={resource}>
        {profile && (
          <>
            <header className="hub-account-header">
              <div className="hub-identity">
                <HubImage
                  src={profile.avatar_url}
                  alt={getPlayerName(profile)}
                />
                <div>
                  <p className="hub-eyebrow">Личный кабинет</p>
                  <h1>{getPlayerName(profile)}</h1>
                </div>
              </div>
              <Link
                className="hub-link-button"
                to={`/u/${encodeURIComponent(profile.username)}`}
              >
                Мой профиль →
              </Link>
            </header>
            {flags.cities_ui && <CityInvitations onChanged={resource.reload} />}
            {flags.cities_ui && (
              <MembershipCards
                memberships={profile.memberships}
                own
                section="cities"
              />
            )}
            {flags.communities_ui && (
              <MembershipCards
                memberships={profile.memberships}
                own
                section="communities"
              />
            )}
            {flags.player_groups_ui && (
              <>
                <Link className="hub-link-button" to="/account/communities">
                  Моё участие и приглашения →
                </Link>
                <MyGroups />
              </>
            )}
            <div className="hub-shortcuts">
              <Link to="/players">Найти игроков</Link>
              <Link to="/players?view=following">Мои подписки</Link>
              <Link to="/account/profile">Редактировать профиль</Link>
              <Link to="/account/security">Безопасность аккаунта</Link>
              {profile.can_moderate && flags.cities_moderation_ui && (
                <Link to="/moderation/cities">Модерация городов</Link>
              )}
            </div>
          </>
        )}
      </ResourceState>
    </HubPage>
  );
}
