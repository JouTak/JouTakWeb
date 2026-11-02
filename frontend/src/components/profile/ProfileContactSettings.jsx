import { Button } from "@gravity-ui/uikit";
import { useState } from "react";

import { getProfileContacts } from "../../services/api/playersApi";
import EditDialog from "../hub/EditDialog";
import { ResourceState } from "../hub/HubShell";
import { visibilityLabels } from "../hub/labels";
import useResource from "../hub/useResource";
import { contactNames } from "./contactLabels";
import ProfileContactEditor from "./ProfileContactEditor";

export default function ProfileContactSettings() {
  const resource = useResource(getProfileContacts);
  const [open, setOpen] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  return (
    <section className="hub-panel">
      <div className="hub-section-heading">
        <h2>Контакты для связи</h2>
        <Button disabled={!resource.data} onClick={() => setOpen(true)}>
          Настроить контакты
        </Button>
      </div>
      <ResourceState resource={resource}>
        {resource.data && (
          <>
            {!resource.data.contacts.length && (
              <p className="hub-muted">
                Добавьте Discord, Telegram или VK и выберите, кто сможет
                связаться с вами.
              </p>
            )}
            <ul className="profile-contacts">
              {resource.data.contacts.map((c) => (
                <li key={c.type}>
                  <span>
                    <b>{contactNames[c.type]}</b> · {c.value}
                  </span>
                  <small className="hub-muted">
                    {visibilityLabels[c.visibility]}
                  </small>
                </li>
              ))}
            </ul>
            {open && (
              <EditDialog
                title="Контакты для связи"
                dirty={dirty}
                busy={busy}
                onClose={() => {
                  setOpen(false);
                  setDirty(false);
                }}
              >
                <ProfileContactEditor
                  initial={resource.data}
                  onDirtyChange={setDirty}
                  onBusyChange={setBusy}
                  onSaved={() => {
                    setOpen(false);
                    setDirty(false);
                    resource.reload();
                  }}
                />
              </EditDialog>
            )}
          </>
        )}
      </ResourceState>
    </section>
  );
}
