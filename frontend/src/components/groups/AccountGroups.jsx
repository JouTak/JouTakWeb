import "./groups.css";

import { useCallback, useState } from "react";
import { Link } from "react-router-dom";

import {
  getMyGroupProcesses,
  getMyGroups,
  getProfileGroups,
} from "../../services/api/groupsApi";
import { Pager, ResourceState } from "../hub/HubShell";
import { formatDate } from "../hub/labels";
import { Markdown } from "../hub/SafeContent";
import useResource from "../hub/useResource";
import GroupCard from "./GroupCard";
import GroupProcessActions from "./GroupProcessActions";
import { membershipStates, processLabels } from "./labels";

export function GroupInbox({ onChanged }) {
  const [page, setPage] = useState(1);
  const resource = useResource(
    useCallback(() => getMyGroupProcesses(page), [page]),
  );
  const reload = () => {
    resource.reload();
    onChanged?.();
  };
  return (
    <section className="group-section">
      <h2>Приглашения и решения</h2>
      <ResourceState resource={resource}>
        {resource.data && (
          <>
            {resource.data.items.length === 0 && (
              <p className="hub-muted">
                Здесь появятся приглашения, ваши заявки и предложения
                руководства.
              </p>
            )}
            {resource.data.items.map(({ group, process, rules }) => (
              <article
                className="hub-panel group-process"
                key={`${process.kind}:${process.id}`}
              >
                <h3>
                  {group &&
                  !(
                    group.access === "private" &&
                    process.kind === "invitation" &&
                    process.status === "pending"
                  ) ? (
                    <Link to={`/groups/${group.slug}`}>{group.name}</Link>
                  ) : (
                    group?.name || "Объединение недоступно"
                  )}
                </h3>
                <p>
                  {process.kind === "request"
                    ? "Ваша заявка"
                    : process.kind === "leadership"
                      ? "Предложение руководства"
                      : "Приглашение"}{" "}
                  · {processLabels[process.status]}
                </p>
                <p className="hub-muted">
                  {formatDate(process.created_at)}
                  {process.status === "pending"
                    ? ` · до ${formatDate(process.expires_at)}`
                    : ""}
                </p>
                {process.status === "pending" && group && (
                  <>
                    <p>{group.short_description}</p>
                    {process.sender_username && (
                      <p>
                        От{" "}
                        <Link
                          to={`/u/${encodeURIComponent(process.sender_username)}`}
                        >
                          {process.sender_nick || process.sender_username}
                        </Link>
                      </p>
                    )}
                    {rules && (
                      <details>
                        <summary>Условия участия</summary>
                        <Markdown>{rules}</Markdown>
                      </details>
                    )}
                  </>
                )}
                {process.reason && <p>{process.reason}</p>}
                <GroupProcessActions
                  process={process}
                  group={group}
                  writeEnabled={resource.data.write_enabled}
                  onChanged={reload}
                />
              </article>
            ))}
            <Pager page={page} total={resource.data.total} onChange={setPage} />
          </>
        )}
      </ResourceState>
    </section>
  );
}

export function MyGroups({ history = false, revision = 0 }) {
  const [page, setPage] = useState(1);
  const resource = useResource(
    useCallback(() => {
      void revision;
      return getMyGroups({ page, history });
    }, [page, history, revision]),
  );
  return (
    <section className="group-section">
      <div className="group-section-title">
        <h2>{history ? "Прошлое участие и архив" : "Мои объединения"}</h2>
        <Link to="/communities">Найти сообщество →</Link>
      </div>
      <ResourceState resource={resource}>
        {resource.data && (
          <>
            <div className="group-grid">
              {resource.data.items.map(({ group, membership }) =>
                group ? (
                  <GroupCard
                    key={membership.id}
                    group={{ ...group, membership }}
                  />
                ) : (
                  <article className="hub-panel" key={membership.id}>
                    <h3>Объединение недоступно</h3>
                    <p>{membershipStates[membership.status]}</p>
                    <p className="hub-muted">
                      История вашего участия сохранена. Доступ к странице
                      закрыт.
                    </p>
                  </article>
                ),
              )}
            </div>
            {!resource.data.total && (
              <p className="hub-muted">
                {history
                  ? "Завершённых участий пока нет."
                  : "Вы пока не участвуете в клубах и командах. Выберите интересное объединение или создайте своё."}
              </p>
            )}
            <Pager page={page} total={resource.data.total} onChange={setPage} />
          </>
        )}
      </ResourceState>
    </section>
  );
}

export function ProfileGroups({ username, load = getProfileGroups }) {
  const [page, setPage] = useState(1);
  const resource = useResource(
    useCallback(() => load(username, page), [username, page, load]),
  );
  if (resource.data?.total === 0) return null;
  return (
    <section className="group-section">
      <h2>Клубы и команды</h2>
      <ResourceState resource={resource}>
        {resource.data && (
          <>
            <div className="group-grid">
              {resource.data.items.map((group) => (
                <GroupCard key={group.slug} group={group} />
              ))}
            </div>
            <Pager page={page} total={resource.data.total} onChange={setPage} />
          </>
        )}
      </ResourceState>
    </section>
  );
}
