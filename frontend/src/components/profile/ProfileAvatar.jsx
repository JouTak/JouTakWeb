import { getPlayerName } from "../../utils/playerIdentity";
import { HubImage } from "../hub/SafeContent";

export default function ProfileAvatar({ profile }) {
  if (profile.avatar_url)
    return <HubImage src={profile.avatar_url} alt={getPlayerName(profile)} />;
  const hash = Array.from(
    profile.username || profile.minecraft_nick || "player",
  ).reduce((result, char) => (result * 31 + char.codePointAt(0)) >>> 0, 17);
  return (
    <svg
      className="hub-avatar profile-avatar"
      viewBox="0 0 48 48"
      aria-hidden="true"
      focusable="false"
    >
      <rect width="48" height="48" fill="var(--player-avatar-background)" />
      {Array.from({ length: 3 }, (_, row) =>
        Array.from({ length: 3 }, (_, column) => {
          if (((hash >>> (row * 3 + column)) & 1) === 0 && column !== 1)
            return null;
          return (
            <rect
              key={`${row}-${column}`}
              x={8 + column * 11}
              y={8 + row * 11}
              width="11"
              height="11"
              fill="var(--player-avatar-foreground)"
            />
          );
        }),
      )}
    </svg>
  );
}
