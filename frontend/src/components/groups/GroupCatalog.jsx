import "./groups.css";

import { Button, TextInput } from "@gravity-ui/uikit";
import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { getGroups } from "../../services/api/groupsApi";
import { Pager, ResourceState } from "../hub/HubShell";
import useResource from "../hub/useResource";
import GroupCard from "./GroupCard";
import { GroupSelect } from "./GroupFields";
import { groupCategories, groupModes } from "./labels";

export default function GroupCatalog({ communities = [] }) {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") || "";
  const scope = params.get("scope") || "";
  const category = params.get("category") || "";
  const join_mode = params.get("join_mode") || "";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const [search, setSearch] = useState(q);
  useEffect(() => setSearch(q), [q]);
  const resource = useResource(
    useCallback(
      () =>
        getGroups({
          q,
          page,
          ...(scope ? { scope } : {}),
          ...(category ? { category } : {}),
          ...(join_mode ? { join_mode } : {}),
        }),
      [q, page, scope, category, join_mode],
    ),
  );
  function filter(values) {
    const next = { ...Object.fromEntries(params), page: "1", ...values };
    Object.keys(next).forEach((key) => {
      if (!next[key]) delete next[key];
    });
    setParams(next);
  }
  return (
    <section className="group-section" aria-labelledby="group-catalog-title">
      <div className="group-section-title">
        <h2 id="group-catalog-title">Клубы и команды</h2>
        <div className="hub-actions">
          {resource.data?.can_create && (
            <Link className="hub-link-button" to="/groups/new">
              Создать объединение
            </Link>
          )}
          {resource.data?.can_moderate && (
            <Link to="/moderation/groups">Модерация</Link>
          )}
        </div>
      </div>
      <form
        className="hub-panel hub-form group-catalog-form"
        onSubmit={(event) => {
          event.preventDefault();
          filter({ q: search });
        }}
      >
        <label htmlFor="group-search">
          Поиск объединения
          <TextInput
            id="group-search"
            size="xl"
            value={search}
            maxLength={100}
            onUpdate={setSearch}
          />
        </label>
        <div className="group-catalog-filters">
          <GroupSelect
            label="Тип объединения"
            value={category}
            onChange={(value) => filter({ category: value })}
            options={{ "": "Все объединения", ...groupCategories }}
          />
          <GroupSelect
            label="Вступление"
            value={join_mode}
            onChange={(value) => filter({ join_mode: value })}
            options={{ "": "Любой способ", ...groupModes }}
          />
          {communities.length > 0 && (
            <GroupSelect
              label="Серверное сообщество"
              value={scope}
              onChange={(value) => filter({ scope: value })}
              options={{
                "": "Любой контекст",
                ...Object.fromEntries(
                  communities.map((community) => [
                    community.slug,
                    community.name,
                  ]),
                ),
              }}
            />
          )}
        </div>
        <Button type="submit" size="xl">
          Найти
        </Button>
      </form>
      <ResourceState resource={resource}>
        {resource.data && (
          <>
            <div className="group-grid">
              {resource.data.items.map((group) => (
                <GroupCard key={group.slug} group={group} />
              ))}
            </div>
            {!resource.data.total && (
              <div className="hub-panel">
                <h3>
                  {q || scope || category || join_mode
                    ? "Ничего не найдено"
                    : "Здесь появятся объединения игроков"}
                </h3>
                <p>
                  {q || scope || category || join_mode
                    ? "Попробуйте другой запрос или снимите фильтры."
                    : "Клуб, команда или гильдия помогут собрать людей для общего дела. Участие добровольное — можно быть в нескольких объединениях."}
                </p>
                {(q || scope || category || join_mode) && (
                  <Button onClick={() => setParams({})}>
                    Сбросить фильтры
                  </Button>
                )}
              </div>
            )}
            <Pager
              page={page}
              total={resource.data.total}
              onChange={(value) => filter({ page: String(value) })}
            />
          </>
        )}
      </ResourceState>
    </section>
  );
}
