import { Button, Label } from "@gravity-ui/uikit";
import { useCallback, useState } from "react";
import { Link } from "react-router-dom";

import { getGroupMembers } from "../../services/api/groupsApi";
import { getPlayerName } from "../../utils/playerIdentity";
import { Pager, ResourceState } from "../hub/HubShell";
import { HubImage } from "../hub/SafeContent";
import useResource from "../hub/useResource";
import GroupMemberDialog from "./GroupMemberDialog";
import { groupRoles, memberVisibility } from "./labels";

export default function GroupMembersManager({ group, onChanged }) {
  const [page, setPage] = useState(1);
  const [history, setHistory] = useState(false);
  const [dialog, setDialog] = useState(null);
  const resource = useResource(
    useCallback(
      () => getGroupMembers(group.slug, { page, history }),
      [group.slug, page, history],
    ),
  );
  const caps = group.capabilities;
  const role = group.viewer.membership?.role;
  const ownId = group.viewer.membership?.id;
  function refresh() {
    resource.reload();
    onChanged();
  }
  return (
    <section className="hub-panel group-section">
      <div className="group-toolbar">
        <h2>Участники</h2>
        <Button
          view="flat-secondary"
          onClick={() => {
            setHistory(!history);
            setPage(1);
          }}
        >
          {history ? "Только действующие" : "Завершённое участие и ограничения"}
        </Button>
      </div>
      <p className="hub-muted">
        Служебный состав. Личная видимость человека не изменяется при назначении
        роли.
      </p>
      <ResourceState resource={resource}>
        {resource.data && (
          <>
            <p>
              {history ? "Записей" : "Действующих участников"}:{" "}
              {resource.data.total}
            </p>
            {!resource.data.items.length && (
              <p>
                Участников пока нет. Приглашения отправляются в разделе «Заявки
                и приглашения».
              </p>
            )}
            <ul className="group-people">
              {resource.data.items.map((member) => {
                const protectedRole =
                  !caps.moderate &&
                  (member.role === "manager" ||
                    (role === "moderator" && member.role !== "member"));
                const writable = caps.write_enabled && caps.manage;
                return (
                  <li key={member.id} className="group-person-row">
                    <div className="hub-identity">
                      <HubImage
                        src={member.avatar_url}
                        alt={getPlayerName(member)}
                      />
                      <div>
                        <Link to={`/u/${encodeURIComponent(member.username)}`}>
                          {getPlayerName(member)}
                        </Link>
                        <div className="hub-actions">
                          <Label>
                            {member.status === "active"
                              ? groupRoles[member.role]
                              : member.status === "left"
                                ? "Вышел"
                                : "Участие завершено"}
                          </Label>
                          {member.restricted && (
                            <Label theme="danger">Участие ограничено</Label>
                          )}
                        </div>
                        <p className="hub-muted">
                          Видимость: {memberVisibility[member.visibility]}
                          {!member.eligible &&
                            " · Нет доступа к серверному сообществу"}
                        </p>
                      </div>
                    </div>
                    {writable && !protectedRole && (
                      <div className="hub-actions">
                        {member.status === "active" && caps.configure && (
                          <Button
                            size="s"
                            onClick={() =>
                              setDialog({
                                member,
                                operation:
                                  member.role === "member"
                                    ? "moderator"
                                    : "member",
                              })
                            }
                          >
                            {member.role === "member"
                              ? "Назначить модератором"
                              : "Снять полномочия"}
                          </Button>
                        )}
                        {member.status === "active" &&
                          caps.configure &&
                          member.eligible &&
                          member.role !== "manager" &&
                          member.id !== ownId && (
                            <>
                              <Button
                                size="s"
                                onClick={() =>
                                  setDialog({ member, operation: "offer" })
                                }
                              >
                                Предложить руководство
                              </Button>
                              {role === "manager" && (
                                <Button
                                  size="s"
                                  onClick={() =>
                                    setDialog({ member, operation: "transfer" })
                                  }
                                >
                                  Передать руководство
                                </Button>
                              )}
                            </>
                          )}
                        {member.status === "active" && (
                          <Button
                            size="s"
                            view="flat-danger"
                            onClick={() =>
                              setDialog({ member, operation: "remove" })
                            }
                          >
                            Завершить участие
                          </Button>
                        )}
                        <Button
                          size="s"
                          view="flat-secondary"
                          onClick={() =>
                            setDialog({
                              member,
                              operation: member.restricted
                                ? "restore"
                                : "restrict",
                            })
                          }
                        >
                          {member.restricted
                            ? "Снять ограничение"
                            : "Ограничить участие"}
                        </Button>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
            <Pager page={page} total={resource.data.total} onChange={setPage} />
          </>
        )}
      </ResourceState>
      {dialog && (
        <GroupMemberDialog
          {...dialog}
          group={group}
          onClose={() => setDialog(null)}
          onChanged={refresh}
        />
      )}
    </section>
  );
}
