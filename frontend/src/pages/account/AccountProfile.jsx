import { Button } from "@gravity-ui/uikit";
import { useState } from "react";
import { Link } from "react-router-dom";

import EditDialog from "../../components/hub/EditDialog";
import { HubPage, ResourceState } from "../../components/hub/HubShell";
import { visibilityLabels } from "../../components/hub/labels";
import useResource from "../../components/hub/useResource";
import GameDataSettings from "../../components/profile/GameDataSettings";
import ProfileContactSettings from "../../components/profile/ProfileContactSettings";
import ProfileEditor from "../../components/profile/ProfileEditor";
import ProfileHero from "../../components/profile/ProfileHero";
import { getSelfProfile } from "../../services/api/profilesApi";
function Settings({ initial }) {
  const [profile, setProfile] = useState(initial);
  const [section, setSection] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [gameRevision, setGameRevision] = useState(0);
  const [refreshError, setRefreshError] = useState(false);
  async function refreshIdentity() {
    setGameRevision((n) => n + 1);
    try {
      setProfile(await getSelfProfile());
      setRefreshError(false);
    } catch {
      setRefreshError(true);
    }
  }
  return (
    <>
      <div className="hub-section-heading">
        <h1>Настройки профиля</h1>
        <Link to={`/u/${encodeURIComponent(profile.username)}`}>
          Мой профиль →
        </Link>
      </div>
      <ProfileHero profile={profile}>
        <Button view="outlined" onClick={() => setSection("about")}>
          Изменить имя, аватар и описание
        </Button>
      </ProfileHero>
      <section className="hub-panel">
        <div className="hub-section-heading">
          <div>
            <h2>Приватность</h2>
            <p className="hub-muted">
              Профиль видят:{" "}
              {visibilityLabels[profile.visibility].toLowerCase()}.
            </p>
          </div>
          <Button onClick={() => setSection("privacy")}>
            Настроить видимость
          </Button>
        </div>
      </section>
      <div className="hub-actions">
        <Link to="/account/profile/preview">Посмотреть как гость →</Link>
        <Link to="/account/profile/following">Мои подписки →</Link>
      </div>
      <ProfileContactSettings key={gameRevision} />
      <GameDataSettings onSaved={refreshIdentity} />
      {refreshError && (
        <div role="alert">
          <p>
            Игровые данные сохранены. Не удалось обновить представление профиля.
          </p>
          <Button onClick={refreshIdentity}>Повторить обновление</Button>
        </div>
      )}
      {section && (
        <EditDialog
          title={section === "about" ? "О себе" : "Приватность профиля"}
          dirty={dirty}
          busy={busy}
          onClose={() => {
            setSection(null);
            setDirty(false);
          }}
        >
          <ProfileEditor
            profile={profile}
            section={section}
            onSaved={setProfile}
            onDirtyChange={setDirty}
            onBusyChange={setBusy}
          />
        </EditDialog>
      )}
    </>
  );
}
export default function AccountProfile() {
  const resource = useResource(getSelfProfile);
  return (
    <HubPage title="Настройки профиля" account hero>
      <ResourceState resource={resource}>
        {resource.data && (
          <Settings key={resource.data.username} initial={resource.data} />
        )}
      </ResourceState>
    </HubPage>
  );
}
