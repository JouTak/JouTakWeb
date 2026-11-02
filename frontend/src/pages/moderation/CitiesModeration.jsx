import { Button } from "@gravity-ui/uikit";
import { useCallback, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import CityCreateForm from "../../components/cities/CityCreateForm";
import { HubPage, Pager, ResourceState } from "../../components/hub/HubShell";
import {
  cityStatuses,
  formatDate,
  visibilityLabels,
} from "../../components/hub/labels";
import useResource from "../../components/hub/useResource";
import { getModerationCities } from "../../services/api/moderationApi";

export default function CitiesModeration() {
  const [recentDays, setRecentDays] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();
  const resource = useResource(
    useCallback(
      () =>
        getModerationCities({
          page,
          ...(status ? { status } : {}),
          ...(recentDays ? { recent_days: recentDays } : {}),
        }),
      [page, status, recentDays],
    ),
  );
  return (
    <HubPage
      title="Модерация городов"
      intro="Публикация, управляющие и история. Последние изменения показываются первыми."
    >
      <ResourceState resource={resource}>
        {resource.data && (
          <>
            <div className="hub-actions">
              <Button view="action" onClick={() => setCreating((v) => !v)}>
                {creating ? "Скрыть создание" : "Создать город"}
              </Button>
            </div>
            {creating && (
              <CityCreateForm
                onCreated={(city) => navigate(`/cities/${city.slug}/manage`)}
              />
            )}
            <div className="hub-form">
              <label>
                Статус города
                <select
                  value={status}
                  onChange={(e) => {
                    setStatus(e.target.value);
                    setPage(1);
                  }}
                >
                  <option value="">Все</option>
                  {Object.entries(cityStatuses).map(([v, label]) => (
                    <option value={v} key={v}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Изменения за период
                <select
                  value={recentDays}
                  onChange={(e) => {
                    setRecentDays(e.target.value);
                    setPage(1);
                  }}
                >
                  <option value="">Всё время</option>
                  <option value="7">Последние 7 дней</option>
                  <option value="30">Последние 30 дней</option>
                </select>
              </label>
            </div>
            <div className="hub-grid">
              {resource.data.items.map((city) => (
                <article className="hub-panel" key={city.slug}>
                  <h2>
                    <Link to={`/cities/${city.slug}/manage`}>{city.name}</Link>
                  </h2>
                  <p>{cityStatuses[city.status]}</p>
                  <p>Видимость: {visibilityLabels[city.visibility]}</p>
                  <p>
                    Управляющие:{" "}
                    {city.managers.map((m) => `@${m}`).join(", ") ||
                      "Не назначены"}
                  </p>
                  <p className="hub-muted">
                    Обновлено {formatDate(city.updated_at)} ·{" "}
                    {city.updated_by || "Система"}
                  </p>
                </article>
              ))}
            </div>
            {!resource.data.total && <p>Городов с этим статусом нет.</p>}
            <Pager page={page} total={resource.data.total} onChange={setPage} />
          </>
        )}
      </ResourceState>
    </HubPage>
  );
}
