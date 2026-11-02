import { useCallback } from "react";
import { Link, useParams } from "react-router-dom";

import { HubPage, ResourceState } from "../../components/hub/HubShell";
import { communityRoles } from "../../components/hub/labels";
import {
  ExternalLink,
  HubImage,
  Markdown,
} from "../../components/hub/SafeContent";
import useResource from "../../components/hub/useResource";
import { useHub } from "../../features/hub/context";
import { getCommunity } from "../../services/api/communitiesApi";
export default function CommunityDetail() {
  const { slug } = useParams();
  const { flags } = useHub();
  const resource = useResource(useCallback(() => getCommunity(slug), [slug]));
  return (
    <HubPage title={resource.data?.name || "Сообщество"} hero={!!resource.data}>
      <Link to="/communities">← Сообщества</Link>
      <ResourceState resource={resource}>
        {resource.data && (
          <>
            <header className="hub-account-header">
              <div className="hub-identity">
                <HubImage
                  src={resource.data.logo_url}
                  alt={resource.data.name}
                />
                <div>
                  <p className="hub-eyebrow">Сообщество сервера</p>
                  <h1>{resource.data.name}</h1>
                  <p>{resource.data.short_description}</p>
                </div>
              </div>
            </header>
            <section className="hub-panel">
              <Markdown>{resource.data.description}</Markdown>
              <p className="hub-muted">
                Участников: {resource.data.member_count}
              </p>
            </section>
            <section className="hub-panel">
              <h2>
                {resource.data.membership?.status === "active"
                  ? "Ваше участие"
                  : "Как присоединиться"}
              </h2>
              {resource.data.membership && (
                <p>
                  {resource.data.membership.status === "active"
                    ? communityRoles[resource.data.membership.role]
                    : resource.data.membership.status === "pending"
                      ? "Участие ожидает подтверждения"
                      : resource.data.membership.status === "suspended"
                        ? "Участие приостановлено"
                        : "Участие завершено"}
                </p>
              )}
              {resource.data.enrollment_text ? (
                <Markdown>{resource.data.enrollment_text}</Markdown>
              ) : (
                <p>
                  Участие в сервере оформляет его администрация. Вступление в
                  клубы и команды само по себе не даёт доступа к игре.
                </p>
              )}
              {resource.data.enrollment_url ? (
                <ExternalLink href={resource.data.enrollment_url}>
                  Порядок участия ↗
                </ExternalLink>
              ) : (
                <Link to="/contact">Связаться с администрацией</Link>
              )}
            </section>
            {resource.data.has_cities && flags.cities_ui && (
              <section className="hub-panel">
                <h2>Поселения игроков</h2>
                <p>
                  На сервере игроки строят города и живут вместе. Познакомьтесь
                  с поселениями в отдельном каталоге.
                </p>
                <Link
                  className="hub-link-button"
                  to={`/cities?community=${slug}`}
                >
                  Посмотреть города →
                </Link>
              </section>
            )}
            {flags.player_groups_ui && (
              <section className="hub-panel">
                <h2>Общее дело</h2>
                <p>
                  Найдите клуб или команду в этом серверном сообществе. Их роли
                  и участие существуют отдельно от городов.
                </p>
                <Link to={`/communities?scope=${slug}`}>Клубы и команды →</Link>
              </section>
            )}
          </>
        )}
      </ResourceState>
    </HubPage>
  );
}
