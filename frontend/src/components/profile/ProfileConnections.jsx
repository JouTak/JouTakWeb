import { Link } from "react-router-dom";

import ProfileConnectionCard from "./ProfileConnectionCard";

export default function ProfileConnections({
  username,
  own = false,
  revision = 0,
  load,
}) {
  return (
    <div className="profile-connections">
      <div className="profile-connections-grid">
        <ProfileConnectionCard
          username={username}
          direction="followers"
          title="Подписчики"
          revision={revision}
          load={load}
        />
        <ProfileConnectionCard
          username={username}
          direction="friends"
          title="Друзья"
          revision={revision}
          load={load}
        />
      </div>
      {own && (
        <Link
          className="profile-visibility-link"
          to="/account/profile/following"
        >
          Мои подписки
        </Link>
      )}
    </div>
  );
}
