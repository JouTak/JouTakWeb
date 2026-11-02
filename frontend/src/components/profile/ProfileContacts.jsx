import { Button } from "@gravity-ui/uikit";
import { useEffect, useState } from "react";

import { ExternalLink } from "../hub/SafeContent";
import { contactNames } from "./contactLabels";
export function CopyButton({ value, children = "Скопировать" }) {
  const [copied, setCopied] = useState(false);
  const [fallback, setFallback] = useState(false);
  useEffect(() => {
    setCopied(false);
    setFallback(false);
  }, [value]);
  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setFallback(false);
    } catch {
      setCopied(false);
      setFallback(true);
    }
  }
  return (
    <div className="hub-follow-action">
      <Button size="s" onClick={copy}>
        {copied ? "Скопировано" : children}
      </Button>
      {copied && (
        <span className="hub-muted" role="status">
          Можно отправить ссылку или контакт собеседнику.
        </span>
      )}
      {fallback && (
        <p className="profile-share-fallback" role="status">
          Скопируйте вручную: <span>{value}</span>
        </p>
      )}
    </div>
  );
}
export default function ProfileContacts({ contacts = [], vkUrl }) {
  return (
    <section className="hub-panel">
      <h2>На связи</h2>
      {!contacts.length && !vkUrl && (
        <p className="hub-muted">Нет доступных контактов.</p>
      )}
      <ul className="profile-contacts">
        {contacts.map((contact) => (
          <li key={contact.type}>
            <div>
              <b>{contactNames[contact.type]}</b>
              <p>
                {contact.url ? (
                  <ExternalLink href={contact.url}>
                    {contact.value} ↗
                  </ExternalLink>
                ) : (
                  contact.value
                )}
              </p>
            </div>
            <CopyButton value={contact.url || contact.value} />
          </li>
        ))}
      </ul>
      {vkUrl && !contacts.some((c) => c.type === "vk") && (
        <ExternalLink href={vkUrl}>Связаться в VK ↗</ExternalLink>
      )}
    </section>
  );
}
