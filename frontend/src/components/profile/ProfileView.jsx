import { Button, Tooltip } from "@gravity-ui/uikit";
import { useState } from "react";
import { FiEdit2 } from "react-icons/fi";
import { Link } from "react-router-dom";

import { useHub } from "../../features/hub/context";
import MembershipCards from "../communities/MembershipCards";
import { ProfileGroups } from "../groups/AccountGroups";
import { visibilityLabels } from "../hub/labels";
import FollowButton from "./FollowButton";
import ProfileConnections from "./ProfileConnections";
import ProfileContacts from "./ProfileContacts";
import ProfileHero from "./ProfileHero";
import ProfileServerHistory from "./ProfileServerHistory";
import ShareProfileButton from "./ShareProfileButton";

export default function ProfileView({
  profile,
  preview = false,
  connectionsLoad,
  groupsLoad,
}) {
  const { flags = {} } = useHub();
  const [socialRevision, setSocialRevision] = useState(0);
  return (
    <>
      {profile.is_self && !preview && (
        <div className="profile-owner-note">
          <p>
            Вы смотрите свой профиль. Аудитория:{" "}
            {visibilityLabels[profile.own_visibility] || "по вашим настройкам"}.
          </p>
          <Link to="/account/profile/preview">Посмотреть как гость →</Link>
        </div>
      )}
      <ProfileHero
        profile={profile}
        primary
        tools={
          !preview && (
            <>
              {profile.is_self && (
                <Tooltip content="Редактировать профиль">
                  <Button
                    component={Link}
                    role="link"
                    to="/account/profile"
                    className="profile-edit-link"
                    view="flat-secondary"
                    size="l"
                    extraProps={{
                      "aria-label": "Редактировать профиль",
                    }}
                  >
                    <FiEdit2 size={20} aria-hidden="true" />
                  </Button>
                </Tooltip>
              )}
              <ShareProfileButton username={profile.username} />
            </>
          )
        }
      >
        {!preview && (
          <FollowButton
            player={profile}
            onChanged={() => setSocialRevision((n) => n + 1)}
          />
        )}
      </ProfileHero>
      <div className="profile-layout">
        <div className="profile-summary">
          <ProfileServerHistory history={profile.server_history} />
          <ProfileConnections
            username={profile.username}
            own={profile.is_self}
            revision={socialRevision}
            load={connectionsLoad}
          />
        </div>
        <aside className="profile-sidebar" aria-label="Контакты игрока">
          <ProfileContacts contacts={profile.contacts} vkUrl={profile.vk_url} />
        </aside>
        <div className="profile-memberships">
          {profile.memberships.communities.length > 0 && (
            <MembershipCards
              memberships={profile.memberships}
              section="communities"
            />
          )}
          {flags.player_groups_ui && (
            <ProfileGroups username={profile.username} load={groupsLoad} />
          )}
        </div>
      </div>
    </>
  );
}
