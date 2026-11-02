import { Button } from "@gravity-ui/uikit";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { saveGroup } from "../../services/api/groupsApi";
import UnsavedChangesGuard from "../hub/UnsavedChangesGuard";
import GroupContentFields from "./GroupContentFields";
import useGroupAction from "./useGroupAction";

const sections = {
  identity: "Основное",
  description: "Описание",
  appearance: "Оформление",
  contacts: "Контакты",
  welcome: "Приветствие",
};
const fields = {
  identity: ["name", "short_description", "category"],
  description: ["description"],
  appearance: ["logo_url", "cover_url"],
  contacts: ["contacts"],
  welcome: ["welcome"],
};
function EditorForm({ group, section, onSaved }) {
  const keys = fields[section];
  const initial = Object.fromEntries(keys.map((key) => [key, group[key]]));
  const [draft, setDraft] = useState(initial);
  const action = useGroupAction(onSaved);
  const dirty = JSON.stringify(initial) !== JSON.stringify(draft);
  return (
    <form
      className="hub-panel hub-form"
      onSubmit={(event) => {
        event.preventDefault();
        action.run(
          () => saveGroup(group.slug, { version: group.version, ...draft }),
          "Изменения опубликованы",
        );
      }}
    >
      <UnsavedChangesGuard dirty={dirty} />
      <h2>{sections[section]}</h2>
      <fieldset
        className="group-editor-fields"
        disabled={action.busy || !group.capabilities.edit}
      >
        <GroupContentFields
          group={group}
          section={section}
          draft={draft}
          update={(key, value) => setDraft((old) => ({ ...old, [key]: value }))}
        />
      </fieldset>
      {action.error && <p role="alert">{action.error}</p>}
      <Button
        view="action"
        type="submit"
        disabled={!dirty || !group.capabilities.edit}
        loading={action.busy}
      >
        Сохранить
      </Button>
    </form>
  );
}
export default function GroupEditor({ group, onSaved }) {
  const [params, setParams] = useSearchParams();
  const allowed = group.capabilities.configure
    ? sections
    : Object.fromEntries(
        Object.entries(sections).filter(([key]) => key !== "identity"),
      );
  const requested = params.get("section");
  const section = allowed[requested]
    ? requested
    : group.capabilities.configure
      ? "identity"
      : "description";
  return (
    <div className="group-section">
      <nav className="hub-actions" aria-label="Разделы страницы">
        {Object.entries(allowed).map(([key, title]) => (
          <Button
            key={key}
            view={section === key ? "outlined" : "flat-secondary"}
            onClick={() =>
              setParams({ ...Object.fromEntries(params), section: key })
            }
          >
            {title}
          </Button>
        ))}
      </nav>
      <EditorForm
        key={`${section}:${group.version}`}
        group={group}
        section={section}
        onSaved={onSaved}
      />
    </div>
  );
}
