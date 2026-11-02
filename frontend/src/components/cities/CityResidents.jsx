import { useCallback, useState } from "react";

import { useHub } from "../../features/hub/context";
import {
  getCityResidents,
  getOwnCityMembership,
} from "../../services/api/citiesApi";
import MembershipVisibility from "../communities/MembershipVisibility";
import { Pager, ResourceState } from "../hub/HubShell";
import useResource from "../hub/useResource";
import CityMembersManager from "./CityMembersManager";
import { CityPeople } from "./CityPresentation";
function OwnMembership({ slug }) {
  const resource = useResource(
    useCallback(() => getOwnCityMembership(slug), [slug]),
  );
  return (
    <ResourceState resource={resource}>
      {resource.data?.membership?.status === "active" && (
        <details className="hub-panel">
          <summary>Моя видимость в списке жителей</summary>
          <p>
            Профиль и его связи тоже должны быть доступны выбранной аудитории.
          </p>
          <MembershipVisibility
            membership={{ ...resource.data.membership, slug }}
          />
        </details>
      )}
    </ResourceState>
  );
}
export default function CityResidents({ city, onChanged }) {
  const { viewer } = useHub();
  const [page, setPage] = useState(1);
  const resource = useResource(
    useCallback(
      () =>
        city.capabilities.manage_members
          ? Promise.resolve(null)
          : getCityResidents(city.slug, page),
      [city.slug, page, city.capabilities.manage_members],
    ),
  );
  return (
    <div className="hub-section">
      {viewer?.is_authenticated && <OwnMembership slug={city.slug} />}
      {city.capabilities.manage_members ? (
        <CityMembersManager city={city} onChanged={onChanged} />
      ) : (
        <section className="hub-panel">
          <h2>Жители</h2>
          <p className="hub-muted">
            Здесь видны участники, открывшие свой профиль и участие в городе.
          </p>
          <ResourceState resource={resource}>
            {resource.data && (
              <>
                <h3>Администрация</h3>
                <CityPeople
                  people={resource.data.items.filter(
                    (p) => p.role !== "resident",
                  )}
                />
                <h3>Жители</h3>
                <CityPeople
                  people={resource.data.items.filter(
                    (p) => p.role === "resident",
                  )}
                />
                {!resource.data.total && (
                  <p>Пока никто не открыл свой профиль для этой аудитории.</p>
                )}
                <Pager
                  page={page}
                  total={resource.data.total}
                  onChange={setPage}
                />
              </>
            )}
          </ResourceState>
        </section>
      )}
    </div>
  );
}
