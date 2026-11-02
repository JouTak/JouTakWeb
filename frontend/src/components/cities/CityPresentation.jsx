import { Button, Label } from "@gravity-ui/uikit";
import { Link } from "react-router-dom";

import { getPlayerName } from "../../utils/playerIdentity";
import {
  cityRoles,
  cityStatuses,
  formatDate,
  recruitmentLabels,
} from "../hub/labels";
import { ExternalLink, HubImage, Markdown } from "../hub/SafeContent";
import CityMapCard from "./CityMapCard";

export function CityPeople({ people }) {
  return (
    <ul className="hub-people">
      {people.map((person, index) => (
        <li key={person.username || index} className="hub-person">
          <HubImage src={person.avatar_url} alt={getPlayerName(person)} />
          <div>
            {person.username ? (
              <Link to={`/u/${encodeURIComponent(person.username)}`}>
                {getPlayerName(person)}
              </Link>
            ) : (
              <span>{getPlayerName(person)}</span>
            )}
            <p>{person.position || cityRoles[person.role]}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}
function Edit({ section, onEdit, label = "Изменить" }) {
  return onEdit ? (
    <Button
      size="s"
      view="flat"
      onClick={() => onEdit(section)}
      extraProps={{
        "aria-label": `${label}: ${section === "about" ? "о городе" : section === "contacts" ? "контакты" : section === "join" ? "вступление" : "сведения"}`,
      }}
    >
      {label}
    </Button>
  ) : null;
}
export default function CityPresentation({
  city,
  preview = false,
  primary = false,
  onEdit,
  tab = "overview",
  children,
}) {
  const Heading = primary ? "h1" : "h2";
  const edit = !preview && city.capabilities.edit ? onEdit : null;
  return (
    <>
      <nav aria-label="Путь" className="hub-breadcrumb">
        <Link to="/cities">Города</Link>
        <span>/</span>
        <span>{city.name}</span>
      </nav>
      <section className="hub-hero hub-city-hero">
        <div className="hub-city-cover">
          <HubImage
            key={city.cover_url}
            src={city.cover_url}
            alt={`Панорама ${city.name}`}
            cover
          />
          {edit && (
            <Button
              className="hub-cover-edit"
              view="normal"
              onClick={() => edit("appearance")}
            >
              Изменить оформление
            </Button>
          )}
        </div>
        <div className="hub-hero-body">
          <div className="hub-identity">
            <HubImage key={city.logo_url} src={city.logo_url} alt={city.name} />
            <div>
              <Heading>{city.name}</Heading>
              <p>{city.short_description}</p>
            </div>
            <Edit section="identity" onEdit={edit} />
          </div>
          <div className="hub-actions">
            <Label
              theme={city.recruitment_status === "open" ? "success" : "normal"}
            >
              {recruitmentLabels[city.recruitment_status]}
            </Label>
            {city.status !== "active" && (
              <Label>{cityStatuses[city.status]}</Label>
            )}
            {tab === "overview" &&
              city.how_to_join &&
              city.recruitment_status !== "closed" && (
                <a href="#join">Как присоединиться ↓</a>
              )}
          </div>
          <dl className="hub-facts">
            <div>
              <dt>Жители</dt>
              <dd>{city.member_count}</dd>
            </div>
            {city.founded_at && (
              <div>
                <dt>Основан</dt>
                <dd>{formatDate(city.founded_at)}</dd>
              </div>
            )}
            {city.region && (
              <div>
                <dt>Регион</dt>
                <dd>{city.region}</dd>
              </div>
            )}
            <div>
              <dt>Обновлено</dt>
              <dd>{formatDate(city.updated_at)}</dd>
            </div>
          </dl>
          {city.capabilities.manage_location && (
            <Edit section="facts" onEdit={edit} label="Изменить сведения" />
          )}
        </div>
      </section>
      {children}
      {tab === "overview" && (
        <div className="hub-city-layout">
          <div className="hub-section">
            <section className="hub-panel">
              <div className="hub-section-heading">
                <h2>О городе</h2>
                <Edit section="about" onEdit={edit} />
              </div>
              <Markdown>{city.description}</Markdown>
            </section>
            <section className="hub-panel">
              <h2>Администрация</h2>
              {city.leadership.length ? (
                <CityPeople people={city.leadership} />
              ) : (
                <p className="hub-muted">
                  Публичные профили представителей пока не добавлены.
                </p>
              )}
            </section>
          </div>
          <aside className="hub-section">
            <section className="hub-panel">
              <div className="hub-section-heading">
                <h2>Связаться</h2>
                <Edit section="contacts" onEdit={edit} />
              </div>
              {city.contacts.length ? (
                city.contacts.map((contact, index) => (
                  <ExternalLink
                    className="hub-contact"
                    key={index}
                    href={contact.url}
                  >
                    {contact.label} ↗
                  </ExternalLink>
                ))
              ) : (
                <p className="hub-muted">Контакты пока не добавлены.</p>
              )}
            </section>
            <CityMapCard
              location={city.location}
              onEdit={
                city.capabilities.manage_location && edit
                  ? () => edit("location")
                  : null
              }
            />
            {(city.how_to_join || edit) && (
              <section className="hub-panel" id="join">
                <div className="hub-section-heading">
                  <h2>Вступление</h2>
                  <Edit section="join" onEdit={edit} />
                </div>
                {city.how_to_join ? (
                  <Markdown>{city.how_to_join}</Markdown>
                ) : (
                  <p className="hub-muted">
                    Расскажите, кого вы ждёте и как получить приглашение.
                  </p>
                )}
                {city.recruitment_status === "closed" && (
                  <p>Сейчас набор закрыт.</p>
                )}
              </section>
            )}
          </aside>
        </div>
      )}
    </>
  );
}
