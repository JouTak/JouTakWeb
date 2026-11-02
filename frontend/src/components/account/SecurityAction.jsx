import { Button } from "@gravity-ui/uikit";
import { useEffect, useId, useState } from "react";
import { useLocation } from "react-router-dom";

export default function SecurityAction({
  id,
  title,
  description,
  status,
  action,
  collapse,
  children,
}) {
  const { hash } = useLocation();
  const panelId = useId();
  const [open, setOpen] = useState(hash === `#${id}`);
  const [visited, setVisited] = useState(open);
  useEffect(() => {
    if (hash === `#${id}`) {
      setOpen(true);
      setVisited(true);
    }
  }, [hash, id]);
  return (
    <div className="security-action" id={id}>
      <div className="security-action-row">
        <div className="security-action-copy">
          <div className="security-action-title">
            <h3>{title}</h3>
            {status}
          </div>
          {description && <div className="security-muted">{description}</div>}
        </div>
        <Button
          view="outlined"
          onClick={() => {
            setOpen(!open);
            setVisited(true);
          }}
          extraProps={{ "aria-expanded": open, "aria-controls": panelId }}
        >
          {open ? collapse : action}
        </Button>
      </div>
      <div id={panelId} hidden={!open} className="security-action-panel">
        {visited && children}
      </div>
    </div>
  );
}
