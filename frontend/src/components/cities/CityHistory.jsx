import { Button } from "@gravity-ui/uikit";
import { useCallback, useState } from "react";

import { getCityHistory } from "../../services/api/citiesApi";
import { ResourceState } from "../hub/HubShell";
import { cityRoles, formatDateTime, visibilityLabels } from "../hub/labels";
import useResource from "../hub/useResource";

const actions = {
  CITY_INVITATION_SENT: "отправил приглашение",
  CITY_INVITATION_ACCEPTED: "принял приглашение и стал жителем",
  CITY_INVITATION_DECLINED: "отклонил приглашение",
  CITY_INVITATION_REVOKED: "отозвал приглашение",
  CITY_CREATED: "создал город",
  CITY_UPDATED: "обновил город",
  CITY_MEMBER_ADDED: "добавил участника",
  CITY_MEMBER_REMOVED: "исключил участника",
  CITY_ROLE_CHANGED: "изменил роль или должность",
  ACCOUNT_MEMBERSHIP_REMOVED: "удалил членство вместе с аккаунтом",
  CITY_MEMBERSHIP_VISIBILITY_CHANGED: "изменил видимость членства",
};
const fieldLabels = {
  name: "название",
  short_description: "короткое описание",
  description: "описание",
  contacts: "контакты",
  location: "координаты",
  status: "статус",
  recruitment_status: "набор жителей",
  founded_at: "дата основания",
  region: "регион",
  language: "язык",
  how_to_join: "вступление",
  logo_url: "логотип",
  cover_url: "обложка",
  created: "создание",
};
export default function CityHistory({ slug, revision }) {
  const [page, setPage] = useState(1);
  const resource = useResource(
    useCallback(() => {
      void revision;
      return getCityHistory(slug, page);
    }, [slug, page, revision]),
  );
  return (
    <section className="hub-panel">
      <h2>История изменений</h2>
      <ResourceState resource={resource}>
        {resource.data && (
          <>
            <ol>
              {resource.data.events.map((event) => (
                <li key={event.id}>
                  <b>{event.actor || "Удалённый аккаунт / система"}</b>{" "}
                  {actions[event.action] || "изменил город"}
                  {event.target_username && ` · @${event.target_username}`}
                  {event.metadata.before_role &&
                    event.metadata.before_role !==
                      event.metadata.after_role && (
                      <p>
                        Роль: {cityRoles[event.metadata.before_role]} →{" "}
                        {cityRoles[event.metadata.after_role]}
                      </p>
                    )}
                  {event.metadata.after_position != null &&
                    event.metadata.before_position !==
                      event.metadata.after_position && (
                      <p>
                        Должность:{" "}
                        {event.metadata.before_position || "Без должности"} →{" "}
                        {event.metadata.after_position || "Без должности"}
                      </p>
                    )}
                  {event.metadata.before_visibility &&
                    event.metadata.before_visibility !==
                      event.metadata.after_visibility && (
                      <p>
                        Видимость:{" "}
                        {visibilityLabels[event.metadata.before_visibility]} →{" "}
                        {visibilityLabels[event.metadata.after_visibility]}
                      </p>
                    )}
                  <p className="hub-muted">
                    {formatDateTime(event.created_at)}
                    {event.metadata.changed_fields.length > 0 &&
                      ` · ${event.metadata.changed_fields
                        .map((f) => fieldLabels[f] || f)
                        .join(", ")}`}
                    {event.metadata.override_reason &&
                      ` · Решение модератора: ${event.metadata.override_reason}`}
                  </p>
                </li>
              ))}
            </ol>
            {!resource.data.events.length && (
              <p>На этой странице нет записей.</p>
            )}
            <div className="hub-actions">
              <Button
                disabled={page === 1}
                onClick={() => setPage((v) => v - 1)}
              >
                Новее
              </Button>
              <Button
                disabled={
                  resource.data.events.length < 20 &&
                  resource.data.revisions.length < 20
                }
                onClick={() => setPage((v) => v + 1)}
              >
                Раньше
              </Button>
            </div>
          </>
        )}
      </ResourceState>
    </section>
  );
}
