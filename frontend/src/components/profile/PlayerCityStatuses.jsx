import { Link } from "react-router-dom";

import { cityRoles } from "../hub/labels";

export default function PlayerCityStatuses({ cities = [] }) {
  const active = cities.filter(
    (city) =>
      (!city.status || city.status === "active") &&
      (!city.city_status || city.city_status === "active"),
  );
  if (!active.length) return null;
  return (
    <ul className="player-city-statuses">
      {active.map((city) => (
        <li key={city.slug}>
          <Link
            className="player-city-pin"
            data-role={city.role}
            to={`/cities/${encodeURIComponent(city.slug)}`}
          >
            {city.name} — {city.position || cityRoles[city.role]}
          </Link>
        </li>
      ))}
    </ul>
  );
}
