import "../assets/user-profile.css";
import CalendarIcon from "../components/icons/Calendar.jsx";
import EmailIcon from "../components/icons/Email.jsx";

const Me = () => {
  const data = {
    "UUID": "26969461-3d36-4e5c-b99b-d219c9aae472",
    "email": "Sasavot@joutak.ru",
    "nickname": "Sasavot",
    "profile": {
      "first_name": "Gleb",
      "second_name": "Orlov",
      "birth_date": "2000-04-13 00:00:00.000",
      "profile_photo": "https://avatars.githubusercontent.com/u/35216654?v=4"
    },
    "roles": [
      {
        "id": 1,
        "name": "user",
        "color": "white",
        "description": "Пользователь системы",
        "functions": []
      },
      {
        "id": 2,
        "name": "verified",
        "color": "green",
        "description": "Подтверждённый игрок JouTak",
        "functions": []
      },
      {
        "id": 3,
        "name": "ITMO.Students",
        "color": "blue",
        "description": "Студент ИТМО",
        "functions": []
      }
    ]
  };

  const birthdateRus = new Date(data.profile.birth_date)
    .toLocaleDateString('ru-RU', {
      day: "numeric",
      month: "long",
      year: "numeric"
    });

  return (
    <section className="user-profile">
      <h1>Профиль пользователя</h1>

      <article className="user-card">
        <figure>
          <picture>
            <img src={data.profile.profile_photo} />
          </picture>
        </figure>

        <div>
          <p className="nickname">{data.nickname}</p>

          <p className="realname">{data.profile.first_name} {data.profile.second_name}</p>

          <a className="email" href={`mailto:${data.email}`}>
            <p><EmailIcon />
              {data.email}
            </p>
          </a>

          <p><CalendarIcon />{birthdateRus}</p>

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
      </article>

    </section>
  );
};

export default Me;
