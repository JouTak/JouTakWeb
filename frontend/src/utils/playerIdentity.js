// Only use Minecraft identity already permitted by the API's visibility policy.
// Account usernames remain the stable keys for links and mutations.
export function getPlayerName(player) {
  return (
    String(player?.minecraft_nick || "").trim() ||
    String(player?.username || "").trim() ||
    "Участник сообщества"
  );
}
