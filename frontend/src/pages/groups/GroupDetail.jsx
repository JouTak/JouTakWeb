import "../../components/groups/groups.css";

import { Label } from "@gravity-ui/uikit";
import { useCallback } from "react";
import { Link, useParams } from "react-router-dom";

import GroupParticipation from "../../components/groups/GroupParticipation";
import GroupPeople from "../../components/groups/GroupPeople";
import {
  groupAccess,
  groupCategories,
  groupModes,
  groupStatuses,
} from "../../components/groups/labels";
import { HubPage, ResourceState } from "../../components/hub/HubShell";
import {
  ExternalLink,
  HubImage,
  Markdown,
} from "../../components/hub/SafeContent";
import useResource from "../../components/hub/useResource";
import { getGroup } from "../../services/api/groupsApi";

export default function GroupDetail() {
  const { slug } = useParams();
  const resource = useResource(useCallback(() => getGroup(slug), [slug]));
  const group = resource.data;
  return (
    <HubPage title={group?.name || "Объединение"} hero={!!group}>
      <Link to="/communities">← Сообщества</Link>
      <ResourceState resource={resource}>
        {group && (
          <>
            <header className="hub-hero">
              {group.cover_url && (
                <HubImage
                  key={group.cover_url}
                  cover
                  src={group.cover_url}
                  alt={`Обложка ${group.name}`}
                />
              )}
              <div className="hub-hero-body">
                <div className="hub-identity">
                  <HubImage
                    key={group.logo_url}
                    src={group.logo_url}
                    alt={group.name}
                  />
                  <div>
                    <p className="hub-muted">
                      {groupCategories[group.category]} ·{" "}
                      {group.scope?.name || "Весь JouTak"}
                    </p>
                    <h1>{group.name}</h1>
                  </div>
                </div>
                <p>{group.short_description}</p>
                <div className="hub-actions">
                  <Label>
                    {group.accepting
                      ? groupModes[group.join_mode]
                      : "Набор на паузе"}
                  </Label>
                  {group.access !== "public" && (
                    <Label>{groupAccess[group.access]}</Label>
                  )}
                  {group.status !== "active" && (
                    <Label>{groupStatuses[group.status]}</Label>
                  )}
                  {(group.capabilities.manage ||
                    group.capabilities.configure) && (
                    <Link
                      className="hub-link-button"
                      to={`/groups/${slug}/manage`}
                    >
                      Управление
                    </Link>
                  )}
                </div>
              </div>
            </header>
            <div className="group-layout">
              <div className="group-section">
                <section className="hub-panel">
                  <h2>Чем занимаемся</h2>
                  <Markdown>
                    {group.description || group.short_description}
                  </Markdown>
                </section>
                {group.rules && (
                  <section className="hub-panel">
                    <h2>Условия участия</h2>
                    <Markdown>{group.rules}</Markdown>
                  </section>
                )}
                {group.welcome && (
                  <section className="hub-panel">
                    <h2>Для участников</h2>
                    <Markdown>{group.welcome}</Markdown>
                  </section>
                )}
                <GroupPeople slug={slug} />
              </div>
              <aside className="group-section">
                <GroupParticipation group={group} onChanged={resource.reload} />
                {group.contacts.length > 0 && (
                  <section className="hub-panel">
                    <h2>На связи</h2>
                    {group.contacts.map((contact) => (
                      <ExternalLink
                        key={`${contact.type}:${contact.url}`}
                        href={contact.url}
                      >
                        {contact.label} ↗
                      </ExternalLink>
                    ))}
                  </section>
                )}
              </aside>
            </div>
          </>
        )}
      </ResourceState>
    </HubPage>
  );
}
