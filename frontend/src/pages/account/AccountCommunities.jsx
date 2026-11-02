import { useState } from "react";

import ServerMemberships from "../../components/communities/ServerMemberships";
import { GroupInbox, MyGroups } from "../../components/groups/AccountGroups";
import { HubPage } from "../../components/hub/HubShell";
import { useHub } from "../../features/hub/context";

export default function AccountCommunities() {
  const { flags } = useHub();
  const [revision, setRevision] = useState(0);
  const [history, setHistory] = useState(false);
  return (
    <HubPage
      title="Мои сообщества"
      intro="Ваше участие в серверах, клубах и командах."
      account
    >
      {flags.player_groups_ui && (
        <>
          <GroupInbox onChanged={() => setRevision((value) => value + 1)} />
          <MyGroups revision={revision} />
        </>
      )}
      <ServerMemberships />
      {flags.player_groups_ui && (
        <details onToggle={(event) => setHistory(event.currentTarget.open)}>
          <summary>История участия</summary>
          {history && <MyGroups history revision={revision} />}
        </details>
      )}
    </HubPage>
  );
}
