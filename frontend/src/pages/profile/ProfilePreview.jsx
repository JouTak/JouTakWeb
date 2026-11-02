import { Link } from "react-router-dom";

import { HubPage, ResourceState } from "../../components/hub/HubShell";
import useResource from "../../components/hub/useResource";
import ProfileView from "../../components/profile/ProfileView";
import {
  getPreviewConnections,
  getPreviewGroups,
  getProfilePreview,
} from "../../services/api/profilesApi";

export default function ProfilePreview() {
  const resource = useResource(getProfilePreview);
  return (
    <HubPage title="Гостевой просмотр" hero={!!resource.data?.profile}>
      <div className="profile-owner-note">
        <p>
          Так гость видит сохранённый профиль. Несохранённые изменения сюда не
          входят.
        </p>
        <Link to="/account/profile">← Вернуться к настройкам</Link>
      </div>
      <ResourceState resource={resource}>
        {resource.data?.profile ? (
          <ProfileView
            profile={resource.data.profile}
            preview
            connectionsLoad={getPreviewConnections}
            groupsLoad={getPreviewGroups}
          />
        ) : (
          resource.data && (
            <section className="hub-panel">
              <h2>Профиль недоступен гостю</h2>
              <p>
                Текущая аудитория профиля не разрешает просмотр без входа.
                Копирование ссылки не изменяет эту настройку.
              </p>
            </section>
          )
        )}
      </ResourceState>
    </HubPage>
  );
}
