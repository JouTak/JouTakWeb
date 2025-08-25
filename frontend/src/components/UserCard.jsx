import { useState } from "react";
import CalendarIcon from "../components/icons/Calendar.jsx";
import EmailIcon from "../components/icons/Email.jsx";

const UserCard = ({ data, mode }) => {
  if (!data || !data.profile) {
    return <></>;
  }

  const birthdateRus = new Date(data.profile.birth_date)
    .toLocaleDateString('ru-RU', {
      day: "numeric",
      month: "long",
      year: "numeric"
    });

  const [expanded, setExpanded] = useState(false);

  return (
    <article className="user-card" onClick={() => setExpanded(!expanded)} data-expanded={expanded || mode == "full"}>
      <div>
        <h3>
          <figure>
            <picture>
              <img src={data.profile.profile_photo} alt="Аватарка" />
            </picture>
          </figure>
          <span className="nickname">{data.nickname}</span>
          <span className="realname">{data.profile.first_name} {data.profile.second_name}</span>
        </h3>

        <div className="expandable">
          <div>
            <a className="email" href={`mailto:${data.email}`}>
              <p title="Электронная почта"><EmailIcon />
                {data.email}
              </p>
            </a>

            <p title="День рождения"><CalendarIcon />{birthdateRus}</p>

            <ul className="chips-list">
              {data.roles.map(role =>
                <li key={role.id} data-color={role.color}>
                  <p>
                    {role.description}
                  </p>
                </li>
              )}
            </ul>
          </div>
        </div>
      </div>
    </article>
  );
};

export default UserCard;
