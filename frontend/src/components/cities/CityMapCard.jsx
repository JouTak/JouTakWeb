import { Button } from "@gravity-ui/uikit";

import { ExternalLink } from "../hub/SafeContent";
export default function CityMapCard({ location, onEdit }) {
  return (
    <section className="hub-panel hub-map-card">
      <div className="hub-section-heading">
        <h2>На карте</h2>
        {onEdit && (
          <Button size="s" view="flat" onClick={onEdit}>
            Изменить место
          </Button>
        )}
      </div>
      {location ? (
        <>
          <p className="hub-muted">
            {location.world === "overworld" ? "Основной мир" : location.world}
          </p>
          <div className="hub-coordinates">
            <span>
              <small>X</small> {location.x}
            </span>
            <span>
              <small>Z</small> {location.z}
            </span>
            {location.y != null && (
              <span>
                <small>Y</small> {location.y}
              </span>
            )}
          </div>
          {location.map_url && (
            <ExternalLink
              className="hub-link-button hub-link-primary"
              href={location.map_url}
            >
              Открыть в BlueMap ↗
            </ExternalLink>
          )}
        </>
      ) : (
        <p className="hub-muted">Город пока не отметил своё расположение.</p>
      )}
    </section>
  );
}
