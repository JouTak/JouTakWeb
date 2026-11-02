import { Button, TextInput } from "@gravity-ui/uikit";
import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import CityCard from "../../components/cities/CityCard";
import { HubPage, Pager, ResourceState } from "../../components/hub/HubShell";
import { recruitmentLabels } from "../../components/hub/labels";
import useResource from "../../components/hub/useResource";
import { getCities } from "../../services/api/citiesApi";

export default function CityCatalog() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") || "";
  const recruitment = params.get("recruitment") || "";
  const community = params.get("community") || "";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const [search, setSearch] = useState(q);
  useEffect(() => setSearch(q), [q]);
  const resource = useResource(
    useCallback(
      () =>
        getCities({
          q,
          page,
          ...(recruitment ? { recruitment } : {}),
          ...(community ? { community } : {}),
        }),
      [q, page, recruitment, community],
    ),
  );
  const filter = (values) =>
    setParams({ ...Object.fromEntries(params), ...values });
  return (
    <HubPage title="Города">
      <form
        className="hub-panel hub-form"
        onSubmit={(e) => {
          e.preventDefault();
          filter({ q: search, page: "1" });
        }}
      >
        <div className="hub-grid">
          <label htmlFor="city-search">
            Поиск города
            <TextInput
              id="city-search"
              value={search}
              maxLength={100}
              onUpdate={setSearch}
            />
          </label>
          <label>
            Набор жителей
            <select
              value={recruitment}
              onChange={(e) =>
                filter({ recruitment: e.target.value, page: "1" })
              }
            >
              <option value="">Все города</option>
              {Object.entries(recruitmentLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <Button type="submit">Найти</Button>
      </form>
      <ResourceState resource={resource}>
        {resource.data && (
          <>
            <div className="city-catalog-grid">
              {resource.data.items.map((city) => (
                <CityCard key={city.slug} city={city} />
              ))}
            </div>
            {!resource.data.items.length && (
              <div className="hub-empty">
                <p>
                  {q || recruitment
                    ? "По этим условиям города не найдены."
                    : "Города пока не добавлены."}
                </p>
                {(q || recruitment) && (
                  <Button
                    onClick={() => {
                      setParams({});
                      setSearch("");
                    }}
                  >
                    Сбросить поиск и фильтр
                  </Button>
                )}
              </div>
            )}
            <Pager
              page={page}
              total={resource.data.total}
              onChange={(p) => filter({ page: String(p) })}
            />
          </>
        )}
      </ResourceState>
    </HubPage>
  );
}
