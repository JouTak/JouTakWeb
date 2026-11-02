import { Link } from "react-router-dom";

import { cityRoles, communityRoles } from "../hub/labels";
import { HubImage } from "../hub/SafeContent";

export default function MembershipCards({
  memberships,
  own = false,
  section = "all",
  showHeading = true,
}) {
  const CardHeading = showHeading ? "h3" : "h2";
  const cities = memberships.cities.filter(
    (m) =>
      m.status === "active" &&
      m.city_status !== "archived" &&
      (m.city_status !== "draft" || m.can_manage),
  );
  const communities = memberships.communities.filter(
    (m) => m.status === "active",
  );
  return (
    <>
      {section !== "cities" && (
        <section className="hub-section">
          {showHeading && <h2>{own ? "Мои сообщества" : "Сообщества"}</h2>}
          <div className="hub-grid">
            {communities.map((m) => (
              <Link
                className="hub-membership-card"
                key={m.community.slug}
                to={`/communities/${m.community.slug}`}
              >
                <HubImage alt={m.community.name} />
                <div>
                  <CardHeading>{m.community.name}</CardHeading>
                  <p>{communityRoles[m.role]}</p>
                </div>
                <span aria-hidden="true">→</span>
              </Link>
            ))}
          </div>
          {!communities.length && (
            <p className="hub-muted">
              {own
                ? "Вы пока не присоединились к сообществам."
                : "Нет открытой информации о сообществах."}{" "}
              {own && <Link to="/communities">Найти сообщество →</Link>}
            </p>
          )}
        </section>
      )}
      {section !== "communities" && (
        <section className="hub-section">
          <div className="hub-section-heading">
            <h2>{own ? "Мои города" : "Города"}</h2>
            {own && <Link to="/cities">Все города →</Link>}
          </div>
          <div className="hub-grid">
            {cities.map((m) => (
              <Link
                className="hub-membership-card"
                key={m.slug}
                to={`/cities/${m.slug}`}
              >
                <HubImage src={m.logo_url} alt={m.name} />
                <div>
                  <h3>{m.name}</h3>
                  <p>{m.position || cityRoles[m.role]}</p>
                  {m.short_description && <small>{m.short_description}</small>}
                </div>
                <span aria-hidden="true">→</span>
              </Link>
            ))}
          </div>
          {!cities.length && (
            <div className="hub-empty">
              <p>
                {own
                  ? "Найдите своё место в JouTak SMP"
                  : "Нет открытой информации о городах."}
              </p>
              {own && (
                <>
                  <p className="hub-muted">
                    Познакомьтесь с городами и их жителями. Присоединиться можно
                    по приглашению.
                  </p>
                  <Link className="hub-link-button" to="/cities">
                    Посмотреть города
                  </Link>
                </>
              )}
            </div>
          )}
        </section>
      )}
    </>
  );
}
