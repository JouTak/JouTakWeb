import { Button, useToaster } from "@gravity-ui/uikit";
import { useCallback, useState } from "react";
import { Link } from "react-router-dom";

import {
  getMyCityInvitations,
  respondCityInvitation,
} from "../../services/api/cityInvitationsApi";
import { extractErrorMessage } from "../../services/errors";
import { Pager, ResourceState } from "../hub/HubShell";
import { HubImage } from "../hub/SafeContent";
import useResource from "../hub/useResource";

export default function CityInvitations({ onChanged }) {
  const [page, setPage] = useState(1);
  const resource = useResource(
    useCallback(() => getMyCityInvitations(page), [page]),
  );
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState("");
  const { add } = useToaster();
  async function respond(invitation, decision) {
    setBusy(invitation.id);
    setError("");
    try {
      await respondCityInvitation(invitation.id, decision);
      add({
        name: "city-invitation",
        title:
          decision === "accept"
            ? `Теперь вы житель города ${invitation.city_name}`
            : "Приглашение отклонено",
        theme: "success",
      });
      resource.reload();
      onChanged?.();
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setBusy(null);
    }
  }
  if (resource.data && !resource.data.total && !error) return null;
  return (
    <section className="hub-section">
      <h2>Приглашения в города</h2>
      {error && <p role="alert">{error}</p>}
      <ResourceState resource={resource}>
        {resource.data?.items.map((invitation) => (
          <article key={invitation.id} className="hub-invitation">
            <div className="hub-identity">
              <HubImage src={invitation.logo_url} alt={invitation.city_name} />
              <div>
                <h3>{invitation.city_name}</h3>
                <p>Вас пригласили стать жителем.</p>
                <Link to={`/cities/${invitation.city_slug}`}>
                  Познакомиться с городом
                </Link>
              </div>
            </div>
            <div className="hub-actions">
              <Button
                view="action"
                disabled={busy !== null}
                loading={busy === invitation.id}
                onClick={() => respond(invitation, "accept")}
              >
                Принять приглашение
              </Button>
              <Button
                disabled={busy !== null}
                onClick={() => respond(invitation, "decline")}
              >
                Отказаться
              </Button>
            </div>
          </article>
        ))}
      </ResourceState>
      <Pager page={page} total={resource.data?.total || 0} onChange={setPage} />
    </section>
  );
}
