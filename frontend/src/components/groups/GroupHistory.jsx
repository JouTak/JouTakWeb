import { useCallback, useState } from "react";

import { getGroupHistory } from "../../services/api/groupsApi";
import { Pager, ResourceState } from "../hub/HubShell";
import useResource from "../hub/useResource";
import { groupRoles } from "./labels";

const events = {
  group_created: "Создано объединение",
  group_updated: "Изменена страница",
  group_publish: "Объединение опубликовано",
  group_archive: "Объединение отправлено в архив",
  group_restore: "Объединение восстановлено",
  member_joined: "Новый участник",
  member_left: "Участник вышел",
  member_removed: "Участие завершено",
  role_changed: "Изменены полномочия",
  member_visibility_changed: "Изменена видимость участия",
  request_sent: "Подана заявка",
  request_accepted: "Заявка принята",
  request_rejected: "Заявка отклонена",
  request_cancelled: "Заявка отозвана",
  request_expired: "Срок заявки истёк",
  invitation_sent: "Отправлено приглашение",
  invitation_accepted: "Приглашение принято",
  invitation_declined: "Приглашение отклонено",
  invitation_revoked: "Приглашение отозвано",
  invitation_expired: "Срок приглашения истёк",
  leadership_offered: "Предложено руководство",
  leadership_accepted: "Руководство принято",
  leadership_declined: "Руководство отклонено",
  leadership_revoked: "Предложение руководства отозвано",
  leadership_expired: "Срок предложения истёк",
  leadership_transferred: "Передано руководство",
  participation_restricted: "Ограничено участие",
  participation_restored: "Снято ограничение участия",
  participation_eligibility_lost: "Изменились условия участия",
  governance_recovery_required: "Требуется восстановление руководства",
  account_removed: "Удалён аккаунт",
  group_restricted: "Объединение ограничено платформой",
  group_unrestricted: "Ограничение объединения снято",
  leadership_recovery_offered: "Предложено восстановление руководства",
};
const fields = {
  name: "название",
  short_description: "краткое описание",
  description: "описание",
  rules: "условия участия",
  welcome: "приветствие",
  application_question: "вопрос заявки",
  logo_url: "логотип",
  cover_url: "обложка",
  category: "категория",
  access: "доступ к странице",
  join_mode: "способ вступления",
  accepting: "приём участников",
  roster_visibility: "видимость состава",
  contacts: "контакты",
};
export default function GroupHistory({ slug }) {
  const [page, setPage] = useState(1);
  const resource = useResource(
    useCallback(() => getGroupHistory(slug, page), [slug, page]),
  );
  return (
    <section className="hub-panel">
      <h2>История</h2>
      <ResourceState resource={resource}>
        {resource.data && (
          <>
            {!resource.data.items.length && <p>Изменений пока нет.</p>}
            <ol className="group-people">
              {resource.data.items.map((event) => (
                <li key={event.id}>
                  <strong>{events[event.action] || "Обновлено участие"}</strong>
                  <p className="hub-muted">
                    {event.actor || "Система"}
                    {event.target ? ` → ${event.target}` : ""} ·{" "}
                    {new Date(event.created_at).toLocaleString("ru-RU")}
                  </p>
                  {!!event.metadata.changed_fields.length && (
                    <p>
                      {event.metadata.changed_fields
                        .map((field) => fields[field] || field)
                        .join(", ")}
                    </p>
                  )}
                  {event.metadata.after_role && (
                    <p>
                      {groupRoles[event.metadata.before_role]} →{" "}
                      {groupRoles[event.metadata.after_role]}
                    </p>
                  )}
                  {event.metadata.reason && <p>{event.metadata.reason}</p>}
                  {event.metadata.platform_override && (
                    <p className="hub-muted">Действие модератора платформы</p>
                  )}
                </li>
              ))}
            </ol>
            <Pager page={page} total={resource.data.total} onChange={setPage} />
          </>
        )}
      </ResourceState>
    </section>
  );
}
