import "../assets/user-profile.css";
import UserCard from "../components/UserCard.jsx";

const ProfilePrototype = () => {
  const data = [{
    "UUID": "26969461-3d36-4e5c-b99b-d219c9aae471",
    "email": "Sasavot123456@joutak.ru",
    "nickname": "long_nickname_qwerty",
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
  },
  {
    "UUID": "26969461-3d36-4e5c-b99b-d219c9aae472",
    "email": "Sasavot111111111111111111@joutak.ru",
    "nickname": "qwerty",
    "profile": {
      "first_name": "Gleb",
      "second_name": "Orlovorlov",
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
      }
    ]
  },
  {
    "UUID": "26969461-3d36-4e5c-b99b-d219c9aae473",
    "email": "Sasavot@joutak.ru",
    "nickname": "abcd",
    "profile": {
      "first_name": "Glebgleb",
      "second_name": "Orlov",
      "birth_date": "2000-04-13 00:00:00.000",
      "profile_photo": "https://avatars.githubusercontent.com/u/35216654?v=4"
    },
    "roles": [
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
  },
  {
    "UUID": "26969461-3d36-4e5c-b99b-d219c9aae474",
    "email": "Sasavot123@joutak.ru",
    "nickname": "long_nickname_qwertyuiop",
    "profile": {
      "first_name": "Gl",
      "second_name": "Orl",
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
        "id": 3,
        "name": "ITMO.Students",
        "color": "blue",
        "description": "Студент ИТМО",
        "functions": []
      }
    ]
  },
  {
    "UUID": "26969461-3d36-4e5c-b99b-d219c9aae475",
    "email": "Sasavot123456789@joutak.ru",
    "nickname": "short",
    "profile": {
      "first_name": "Gleb",
      "second_name": "Orlov",
      "birth_date": "2000-04-13 00:00:00.000",
      "profile_photo": "https://avatars.githubusercontent.com/u/35216654?v=4"
    },
    "roles": [
      {
        "id": 3,
        "name": "ITMO.Students",
        "color": "blue",
        "description": "Студент ИТМО",
        "functions": []
      }
    ]
  },
  {
    "UUID": "26969461-3d36-4e5c-b99b-d219c9aae476",
    "email": "Sasavot012@joutak.ru",
    "nickname": "long_nickname",
    "profile": {
      "first_name": "Glebglebglebgleb",
      "second_name": "Orlov",
      "birth_date": "2000-04-13 00:00:00.000",
      "profile_photo": "https://avatars.githubusercontent.com/u/35216654?v=4"
    },
    "roles": [
      {
        "id": 2,
        "name": "verified",
        "color": "green",
        "description": "Подтверждённый игрок JouTak",
        "functions": []
      }
    ]
  },
  {
    "UUID": "26969461-3d36-4e5c-b99b-d219c9aae477",
    "email": "Sas@joutak.ru",
    "nickname": "mantevian",
    "profile": {
      "first_name": "Gleb",
      "second_name": "Orlovorlovorlov",
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
      }
    ]
  },
  {
    "UUID": "26969461-3d36-4e5c-b99b-d219c9aae478",
    "email": "Sa@jt.ru",
    "nickname": "enderdissa",
    "profile": {
      "first_name": "Glebgleb",
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
  },
  {
    "UUID": "26969461-3d36-4e5c-b99b-d219c9aae479",
    "email": "Sas@jou.ru",
    "nickname": "foobarfoobarfoobar",
    "profile": {
      "first_name": "Glebglebglebgleb",
      "second_name": "Orlovorlovorlovorlov",
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
  },
  {
    "UUID": "26969461-3d36-4e5c-b99b-d219c9aae47a",
    "email": "Sasavot12345678@joutak.ru",
    "nickname": "12345678901234567890",
    "profile": {
      "first_name": "Glebgleb",
      "second_name": "Orlovorlov",
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
  }];

  return (
    <>
      <section className="user-profile">
        <h1>Профиль пользователя</h1>

        <UserCard data={data[0]} mode="full" />
      </section>

      <section>
        <h1>Список пользователей</h1>
        <ul className="profile-cards">
          {data.map((item, index) =>
            <li key={item.UUID} >
              <UserCard data={item} />
            </li>
          )}
        </ul>
      </section>
    </>
  );
};

export default ProfilePrototype;
