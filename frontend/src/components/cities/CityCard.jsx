import "./CityCard.css";

import { Button, Label, Tooltip } from "@gravity-ui/uikit";
import { FiMap } from "react-icons/fi";
import { Link } from "react-router-dom";

import { safeExternalUrl } from "../../services/urlSafety";
import { getPlayerName } from "../../utils/playerIdentity";
import { recruitmentLabels } from "../hub/labels";
import { HubImage } from "../hub/SafeContent";

const playerPlural = new Intl.PluralRules("ru");
const playerWords = {
  one: "игрок",
  few: "игрока",
  many: "игроков",
  other: "игрока",
};

export default function CityCard({ city }) {
  const cityPath = `/cities/${city.slug}`;
  const mapUrl = safeExternalUrl(city.map_url);
  return (
    <article className="hub-panel city-card" aria-label={city.name}>
      <Link
        className="city-card-logo"
        to={cityPath}
        aria-label={`Открыть ${city.name}`}
      >
        <HubImage key={city.logo_url} src={city.logo_url} alt={city.name} />
      </Link>
      <div className="city-card-content">
        <div className="city-card-toolbar">
          <Label
            theme={city.recruitment_status === "open" ? "success" : "normal"}
          >
            {city.recruitment_status === "open"
              ? "Набор открыт"
              : recruitmentLabels[city.recruitment_status]}
          </Label>
          {mapUrl && (
            <Tooltip content="Открыть на карте">
              <Button
                className="city-card-map"
                view="flat-secondary"
                size="m"
                href={mapUrl}
                target="_blank"
                rel="noopener noreferrer"
                extraProps={{ "aria-label": `${city.name} на карте` }}
              >
                <FiMap size={18} aria-hidden="true" />
              </Button>
            </Tooltip>
          )}
        </div>
        <h2>
          <Link to={cityPath}>{city.name}</Link>
        </h2>
        <p className="city-card-meta hub-muted">
          {city.leader && (
            <>
              <span>
                {city.leader.position || "Управляющий"}{" "}
                <Link to={`/u/${encodeURIComponent(city.leader.username)}`}>
                  {getPlayerName(city.leader)}
                </Link>
              </span>
              <span aria-hidden="true">·</span>
            </>
          )}
          <span>
            {city.member_count}{" "}
            {playerWords[playerPlural.select(city.member_count)]}
          </span>
        </p>
        <p className="city-card-description">{city.short_description}</p>
      </div>
    </article>
  );
}
