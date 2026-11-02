import { useCallback, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import CityEditor from "../../components/cities/CityEditor";
import CityHistory from "../../components/cities/CityHistory";
import CityPresentation from "../../components/cities/CityPresentation";
import CityPublication from "../../components/cities/CityPublication";
import CityResidents from "../../components/cities/CityResidents";
import EditDialog from "../../components/hub/EditDialog";
import { HubPage, ResourceState } from "../../components/hub/HubShell";
import useResource from "../../components/hub/useResource";
import { getCity } from "../../services/api/citiesApi";
import { extractErrorMessage } from "../../services/errors";
const sections = {
  identity: "Название и описание",
  about: "О городе",
  join: "Вступление в город",
  appearance: "Оформление города",
  facts: "Сведения о городе",
  location: "Расположение",
  contacts: "Контакты города",
};
function CityView({ initial }) {
  const [city, setCity] = useState(initial);
  const [params, setParams] = useSearchParams();
  const [editing, setEditing] = useState(
    initial.capabilities.edit && params.get("edit") === "identity"
      ? "identity"
      : null,
  );
  const [dirty, setDirty] = useState(false);
  const [refreshError, setRefreshError] = useState("");
  async function refreshCity() {
    try {
      setCity(await getCity(city.slug));
      setRefreshError("");
    } catch (error) {
      setRefreshError(extractErrorMessage(error));
    }
  }
  const available = {
    overview: "О городе",
    residents: `Жители · ${city.member_count}`,
    ...(city.capabilities.edit ? { history: "История" } : {}),
    ...(city.capabilities.moderate ? { publication: "Публикация" } : {}),
  };
  const tab = Object.hasOwn(available, params.get("tab"))
    ? params.get("tab")
    : "overview";
  function close() {
    setEditing(null);
    setDirty(false);
    if (params.has("edit")) {
      const next = new URLSearchParams(params);
      next.delete("edit");
      setParams(next, { replace: true });
    }
  }
  return (
    <>
      <CityPresentation city={city} primary onEdit={setEditing} tab={tab}>
        <nav className="hub-tabs" aria-label="Разделы города">
          {Object.entries(available).map(([key, label]) => (
            <Link
              key={key}
              to={`?tab=${key}`}
              aria-current={tab === key ? "page" : undefined}
            >
              {label}
            </Link>
          ))}
        </nav>
      </CityPresentation>
      {refreshError && <p role="alert">{refreshError}</p>}
      {tab === "residents" && (
        <CityResidents city={city} onChanged={refreshCity} />
      )}
      {tab === "history" && (
        <CityHistory slug={city.slug} revision={city.version} />
      )}
      {tab === "publication" && (
        <CityPublication city={city} onSaved={setCity} />
      )}
      {editing && (
        <EditDialog title={sections[editing]} dirty={dirty} onClose={close}>
          <CityEditor
            city={city}
            section={editing}
            onDirtyChange={setDirty}
            onSaved={setCity}
          />
        </EditDialog>
      )}
    </>
  );
}
export default function CityDetail() {
  const { slug } = useParams();
  const resource = useResource(useCallback(() => getCity(slug), [slug]));
  return (
    <HubPage title={resource.data?.name || "Город"} hero={!!resource.data}>
      <ResourceState resource={resource}>
        {resource.data && <CityView key={slug} initial={resource.data} />}
      </ResourceState>
    </HubPage>
  );
}
