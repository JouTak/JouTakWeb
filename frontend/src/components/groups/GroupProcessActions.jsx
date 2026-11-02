import { Button } from "@gravity-ui/uikit";
import { useState } from "react";

import {
  respondGroupInvitation,
  respondGroupLeadership,
  withdrawMyGroupRequest,
} from "../../services/api/groupsApi";
import { GroupSelect } from "./GroupFields";
import { memberVisibility } from "./labels";
import useGroupAction from "./useGroupAction";

export default function GroupProcessActions({
  process,
  group,
  writeEnabled,
  onChanged,
}) {
  const [visibility, setVisibility] = useState("private");
  const action = useGroupAction(onChanged);
  if (process.status !== "pending") return null;
  const leadership = process.kind === "leadership";
  const canAccept =
    group &&
    group.status !== "archived" &&
    (!group.restricted || process.recovery) &&
    (leadership || group.accepting);
  function respond(decision) {
    const call = leadership ? respondGroupLeadership : respondGroupInvitation;
    action.run(
      () => call(process.id, { decision, visibility }),
      decision === "accept"
        ? leadership
          ? "Вы приняли руководство объединением"
          : "Вы присоединились к объединению"
        : "Предложение отклонено",
    );
  }
  return (
    <div className="hub-form">
      {!writeEnabled && (
        <p className="hub-muted">Изменения временно приостановлены.</p>
      )}
      {process.kind === "request" ? (
        <Button
          disabled={!writeEnabled}
          loading={action.busy}
          onClick={() =>
            action.run(
              () => withdrawMyGroupRequest(process.id),
              "Заявка отозвана",
            )
          }
        >
          Отозвать заявку
        </Button>
      ) : (
        <>
          {leadership ? (
            <p>
              {process.transfer
                ? "После принятия вы получите управление, а отправитель станет обычным участником."
                : "После принятия вы сможете менять настройки и управлять участниками этого объединения."}
            </p>
          ) : (
            <>
              <GroupSelect
                label="Кто увидит моё участие"
                value={visibility}
                options={memberVisibility}
                onChange={setVisibility}
              />
              <p className="hub-muted">
                Руководство увидит участие для управления составом. Города и
                серверные права не изменятся.
              </p>
            </>
          )}
          {!canAccept && (
            <p className="hub-muted">
              Сейчас принять предложение нельзя. Набор или работа объединения
              приостановлены.
            </p>
          )}
          <div className="hub-actions">
            <Button
              view="action"
              disabled={!writeEnabled || !canAccept}
              loading={action.busy}
              onClick={() => respond("accept")}
            >
              {leadership ? "Принять руководство" : "Принять приглашение"}
            </Button>
            <Button
              disabled={!writeEnabled || action.busy}
              onClick={() => respond("decline")}
            >
              Отказаться
            </Button>
          </div>
        </>
      )}
      {action.error && <p role="alert">{action.error}</p>}
    </div>
  );
}
