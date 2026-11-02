import { Button, useToaster } from "@gravity-ui/uikit";
import { useCallback, useState } from "react";

import { getCityMembers } from "../../services/api/citiesApi";
import {
  getSentCityInvitations,
  inviteCityResident,
  revokeCityInvitation,
} from "../../services/api/cityInvitationsApi";
import { extractErrorMessage } from "../../services/errors";
import { getPlayerName } from "../../utils/playerIdentity";
import EditDialog from "../hub/EditDialog";
import { Pager, ResourceState } from "../hub/HubShell";
import { cityRoles } from "../hub/labels";
import { HubImage } from "../hub/SafeContent";
import useResource from "../hub/useResource";
import { TextField } from "./CityEditorFields";
import CityMemberDialog from "./CityMemberDialog";

export default function CityMembersManager({ city, onChanged }) {
  const [page, setPage] = useState(1);
  const [invitePage, setInvitePage] = useState(1);
  const resource = useResource(
    useCallback(() => getCityMembers(city.slug, page), [city.slug, page]),
  );
  const invitations = useResource(
    useCallback(
      () => getSentCityInvitations(city.slug, invitePage),
      [city.slug, invitePage],
    ),
  );
  const [username, setUsername] = useState("");
  const [inviting, setInviting] = useState(false);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { add } = useToaster();
  async function send(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await inviteCityResident(city.slug, username.trim());
      setUsername("");
      setInviting(false);
      invitations.reload();
      add({
        name: "city-invite-sent",
        title: "Приглашение отправлено",
        content: "Пользователь увидит его в своём кабинете.",
        theme: "success",
      });
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  async function revoke(id) {
    setBusy(true);
    setError("");
    try {
      await revokeCityInvitation(city.slug, id);
      invitations.reload();
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  const changed = () => {
    resource.reload();
    onChanged?.();
  };
  return (
    <section className="hub-section">
      <div className="hub-section-heading">
        <h2>Жители города</h2>
        {city.status === "active" && (
          <Button
            view="action"
            onClick={() => {
              setError("");
              setInviting(true);
            }}
          >
            Пригласить жителя
          </Button>
        )}
      </div>
      {error && !inviting && <p role="alert">{error}</p>}
      <ResourceState resource={resource}>
        {resource.data && (
          <>
            {[
              { title: "Администрация", leader: true },
              { title: "Жители", leader: false },
            ].map((group) => (
              <section className="hub-panel" key={group.title}>
                <h3>{group.title}</h3>
                <ul className="hub-roster">
                  {resource.data.items
                    .filter((m) => (m.role !== "resident") === group.leader)
                    .map((member) => (
                      <li key={member.id} className="hub-row">
                        <div className="hub-identity">
                          <HubImage
                            src={member.avatar_url}
                            alt={getPlayerName(member)}
                          />
                          <div>
                            <b>{getPlayerName(member)}</b>
                            <p className="hub-muted">
                              {member.position || cityRoles[member.role]}
                            </p>
                          </div>
                        </div>
                        <Button
                          size="s"
                          onClick={() => setSelected(member)}
                          extraProps={{
                            "aria-label": `Права @${getPlayerName(member)}`,
                          }}
                        >
                          Права и должность
                        </Button>
                      </li>
                    ))}
                </ul>
              </section>
            ))}
            {!resource.data.total && (
              <p>Пока нет зарегистрированных жителей.</p>
            )}
            <Pager page={page} total={resource.data.total} onChange={setPage} />
          </>
        )}
      </ResourceState>
      <section className="hub-panel">
        <h3>Ожидают ответа</h3>
        <ResourceState resource={invitations}>
          {invitations.data && (
            <>
              <ul className="hub-roster">
                {invitations.data.items.map((invitation) => (
                  <li key={invitation.id} className="hub-row">
                    <span>{getPlayerName(invitation)}</span>
                    <Button
                      size="s"
                      disabled={busy}
                      onClick={() => revoke(invitation.id)}
                    >
                      Отозвать приглашение
                    </Button>
                  </li>
                ))}
              </ul>
              {!invitations.data.total && (
                <p className="hub-muted">Отправленных приглашений пока нет.</p>
              )}
              <Pager
                page={invitePage}
                total={invitations.data.total}
                onChange={setInvitePage}
              />
            </>
          )}
        </ResourceState>
      </section>
      {inviting && (
        <EditDialog
          title="Пригласить в город"
          onClose={() => setInviting(false)}
          dirty={!!username}
        >
          <form onSubmit={send} className="hub-form">
            <p>
              Пользователь сам решит, присоединяться ли к городу. После принятия
              он станет жителем.
            </p>
            <TextField
              label="Имя пользователя на JouTak"
              value={username}
              onChange={setUsername}
              required
              maxLength={150}
              placeholder="Без @"
            />
            <p className="hub-muted">
              Пригласить можно участника JouTak SMP. Приглашение действует 14
              дней.
            </p>
            {error && <p role="alert">{error}</p>}
            <Button
              type="submit"
              view="action"
              loading={busy}
              disabled={!username.trim()}
            >
              Отправить приглашение
            </Button>
          </form>
        </EditDialog>
      )}
      {selected && (
        <CityMemberDialog
          member={selected}
          city={city}
          onClose={() => setSelected(null)}
          onSaved={changed}
        />
      )}
    </section>
  );
}
