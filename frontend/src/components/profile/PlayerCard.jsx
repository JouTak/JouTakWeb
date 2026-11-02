import "./players.css";

import { Link } from "react-router-dom";

import { getPlayerName } from "../../utils/playerIdentity";
import FollowButton from "./FollowButton";
import PlayerCityStatuses from "./PlayerCityStatuses";
import ProfileAvatar from "./ProfileAvatar";

export default function PlayerCard({ player, onFollowChanged }) {
  const profileUrl = `/u/${encodeURIComponent(player.username)}`;
  return (
    <article className="player-card">
      <Link
        className="player-card-identity"
        to={profileUrl}
        aria-label={getPlayerName(player)}
      >
        <ProfileAvatar profile={player} />
        <div>
          <h2>{getPlayerName(player)}</h2>
        </div>
      </Link>
      <PlayerCityStatuses cities={player.cities} />
      <FollowButton player={player} onChanged={onFollowChanged} />
    </article>
  );
}
