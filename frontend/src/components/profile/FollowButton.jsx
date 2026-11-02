import { Button } from "@gravity-ui/uikit";
import { useEffect, useState } from "react";

import { useHub } from "../../features/hub/context";
import { followPlayer, unfollowPlayer } from "../../services/api/playersApi";
import { extractErrorMessage } from "../../services/errors";
import { getPlayerName } from "../../utils/playerIdentity";

export default function FollowButton({ player, onChanged }) {
  const { viewer } = useHub();
  const [following, setFollowing] = useState(!!player.is_following);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(
    () => setFollowing(!!player.is_following),
    [player.username, player.is_following],
  );
  if (player.is_self || !viewer?.is_authenticated) return null;
  async function toggle() {
    setBusy(true);
    setError("");
    try {
      const result = await (following ? unfollowPlayer : followPlayer)(
        player.username,
      );
      setFollowing(result.is_following);
      onChanged?.(result.is_following);
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="hub-follow-action">
      <Button
        view={following ? "outlined" : "action"}
        loading={busy}
        onClick={toggle}
        extraProps={{
          "aria-label": `${following ? "Отписаться от" : "Подписаться на"} @${getPlayerName(player)}`,
        }}
      >
        {following ? "Вы подписаны · Отписаться" : "Подписаться"}
      </Button>
      {error && (
        <p role="alert" className="hub-error">
          {error}
        </p>
      )}
    </div>
  );
}
