import "./groups.css";

import { Label } from "@gravity-ui/uikit";
import { Link } from "react-router-dom";

import { HubImage } from "../hub/SafeContent";
import {
  groupCategories,
  groupModes,
  groupRoles,
  groupStatuses,
  membershipStates,
} from "./labels";

export default function GroupCard({ group }) {
  const member = group.membership;
  return (
    <article className="hub-panel group-card">
      <Link className="group-card-link" to={`/groups/${group.slug}`}>
        <HubImage key={group.logo_url} src={group.logo_url} alt={group.name} />
        <div className="group-card-body">
          <div className="hub-actions">
            <Label>{groupCategories[group.category]}</Label>
            {group.status !== "active" && (
              <Label>{groupStatuses[group.status]}</Label>
            )}
            {group.restricted && (
              <Label theme="warning">Действия ограничены</Label>
            )}
          </div>
          <h3>{group.name}</h3>
          <p>{group.short_description}</p>
          <p className="hub-muted">
            {group.scope?.name || "Весь JouTak"} ·{" "}
            {group.accepting ? groupModes[group.join_mode] : "Набор на паузе"}
          </p>
          {member && (
            <p className="group-relation">
              {!member.eligible
                ? `Требуется участие в ${group.scope?.name || "серверном сообществе"}`
                : member.status === "active"
                  ? groupRoles[member.role]
                  : membershipStates[member.status]}
            </p>
          )}
          {group.pending && (
            <p className="group-relation">
              {group.pending === "request"
                ? "Ваша заявка рассматривается"
                : "Вам поступило предложение"}
            </p>
          )}
        </div>
      </Link>
    </article>
  );
}
