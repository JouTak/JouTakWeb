import { Button } from "@gravity-ui/uikit";
import { useCallback, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import {
  getGroupProcesses,
  inviteToGroup,
  reviewGroupRequest,
  revokeGroupInvitation,
  revokeGroupLeadership,
} from "../../services/api/groupsApi";
import { Pager, ResourceState } from "../hub/HubShell";
import useResource from "../hub/useResource";
import { ConfirmDialog } from "../ui/primitives";
import { GroupText } from "./GroupFields";
import { processLabels } from "./labels";
import useGroupAction from "./useGroupAction";

const kinds = {
  request: "Заявки",
  invitation: "Приглашения",
  leadership: "Предложения руководства",
};
export default function GroupQueue({ group }) {
  const [params, setParams] = useSearchParams();
  const kind = kinds[params.get("kind")] ? params.get("kind") : "request";
  const [page, setPage] = useState(1);
  const [username, setUsername] = useState("");
  const [dialog, setDialog] = useState(null);
  const [reason, setReason] = useState("");
  const resource = useResource(
    useCallback(
      () => getGroupProcesses(group.slug, { kind, page }),
      [group.slug, kind, page],
    ),
  );
  const action = useGroupAction(resource.reload);
  const enabled = group.capabilities.write_enabled && group.capabilities.manage;
  function decide() {
    action.run(
      () =>
        kind === "request"
          ? reviewGroupRequest(group.slug, dialog.id, {
              decision: dialog.decision,
              reason,
            })
          : kind === "invitation"
            ? revokeGroupInvitation(group.slug, dialog.id)
            : revokeGroupLeadership(group.slug, dialog.id),
      "Решение сохранено",
      () => setDialog(null),
    );
  }
  return (
    <div className="group-section">
      <form
        className="hub-panel hub-form"
        onSubmit={(event) => {
          event.preventDefault();
          action.run(
            () => inviteToGroup(group.slug, { username }),
            "Приглашение отправлено в личный кабинет",
            () => setUsername(""),
          );
        }}
      >
        <h2>Пригласить участника</h2>
        <p>
          Человек сам примет решение. Приглашение не добавляет его автоматически
          и не выдаёт полномочий.
        </p>
        <GroupText
          label="Логин профиля"
          value={username}
          onChange={setUsername}
          required
          maxLength={150}
        />
        <Link to="/players">Найти игрока</Link>
        <Button
          type="submit"
          view="action"
          loading={action.busy}
          disabled={!enabled || !group.accepting || group.status !== "active"}
        >
          Отправить приглашение
        </Button>
        {!group.accepting && (
          <p className="hub-muted">Сейчас набор на паузе.</p>
        )}
        {action.error && !dialog && <p role="alert">{action.error}</p>}
      </form>
      <section className="hub-panel group-section">
        <nav className="hub-actions" aria-label="Процессы участия">
          {Object.entries(kinds).map(([key, title]) => (
            <Button
              key={key}
              view={kind === key ? "outlined" : "flat-secondary"}
              onClick={() => {
                setPage(1);
                setParams({ ...Object.fromEntries(params), kind: key });
              }}
            >
              {title}
            </Button>
          ))}
        </nav>
        <ResourceState resource={resource}>
          {resource.data && (
            <>
              {!resource.data.items.length && (
                <p>{kinds[kind]} пока не поступали.</p>
              )}
              <ul className="group-people">
                {resource.data.items.map((process) => (
                  <li className="group-person-row" key={process.id}>
                    <div>
                      <strong>
                        {process.minecraft_nick ||
                          process.username ||
                          "Удалённый аккаунт"}
                      </strong>
                      <p>
                        {processLabels[process.status]} ·{" "}
                        {new Date(process.created_at).toLocaleDateString(
                          "ru-RU",
                        )}
                      </p>
                      {process.answer && (
                        <p className="group-prewrap">{process.answer}</p>
                      )}
                      {process.reason && (
                        <p className="hub-muted">{process.reason}</p>
                      )}
                      {process.sender_username && (
                        <p className="hub-muted">
                          Отправил{" "}
                          {process.sender_nick || process.sender_username}
                        </p>
                      )}
                      {process.transfer && <p>Передача руководства</p>}
                    </div>
                    {process.status === "pending" && enabled && (
                      <div className="hub-actions">
                        {kind === "request" && (
                          <Button
                            disabled={
                              !group.accepting ||
                              group.status !== "active" ||
                              group.restricted
                            }
                            onClick={() => {
                              setReason("");
                              setDialog({ ...process, decision: "accept" });
                            }}
                          >
                            Принять
                          </Button>
                        )}
                        {(kind !== "leadership" ||
                          group.capabilities.configure) && (
                          <Button
                            view="flat-secondary"
                            onClick={() => {
                              setReason("");
                              setDialog({ ...process, decision: "reject" });
                            }}
                          >
                            {kind === "request" ? "Отклонить" : "Отозвать"}
                          </Button>
                        )}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
              <Pager
                page={page}
                total={resource.data.total}
                onChange={setPage}
              />
            </>
          )}
        </ResourceState>
      </section>
      <ConfirmDialog
        open={!!dialog}
        title={
          kind === "request"
            ? dialog?.decision === "accept"
              ? "Принять заявку?"
              : "Отклонить заявку?"
            : "Отозвать предложение?"
        }
        confirmText="Подтвердить"
        onCancel={() => setDialog(null)}
        onConfirm={decide}
        loading={action.busy}
      >
        <p>
          {dialog?.decision === "accept"
            ? "Автор заявки станет обычным участником. Его настройки видимости сохранятся."
            : "Результат появится в личном кабинете получателя. Это не ограничивает его участие в других объединениях."}
        </p>
        {kind === "request" && (
          <GroupText
            label="Пояснение автору заявки (необязательно)"
            value={reason}
            onChange={setReason}
            maxLength={500}
            multiline
          />
        )}
        {action.error && <p role="alert">{action.error}</p>}
      </ConfirmDialog>
    </div>
  );
}
