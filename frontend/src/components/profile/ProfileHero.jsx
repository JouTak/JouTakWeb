import "./players.css";

import { getPlayerName } from "../../utils/playerIdentity";
import PlayerCityStatuses from "./PlayerCityStatuses";
import ProfileAvatar from "./ProfileAvatar";
export default function ProfileHero({
  profile,
  primary = false,
  tools,
  children,
}) {
  const Heading = primary ? "h1" : "h2";
  return (
    <header className="hub-profile-hero">
      <div className="profile-hero-top">
        <div className="hub-identity">
          <ProfileAvatar key={profile.avatar_url} profile={profile} />
          <div>
            <Heading>{getPlayerName(profile)}</Heading>
            {profile.display_name &&
              profile.display_name !== profile.username &&
              profile.display_name !== getPlayerName(profile) && (
                <p className="hub-muted">{profile.display_name}</p>
              )}
          </div>
        </div>
        {tools && <div className="profile-hero-tools">{tools}</div>}
      </div>
      {profile.bio && <p className="hub-profile-bio">{profile.bio}</p>}
      <PlayerCityStatuses cities={profile.memberships?.cities} />
      {children}
    </header>
  );
}
