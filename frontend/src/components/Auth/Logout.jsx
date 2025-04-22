import React, { useState, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { obtainToken } from "../../services/api";
import { AuthContext } from "../../context/AuthContext";

function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const { login } = useContext(AuthContext);
  const navigate = useNavigate();
  const [error, setError] = useState("");

  const handleSubmit = (event) => {
    event.preventDefault();
    obtainToken(username, password)
      .then((response) => {
        login(response.data);
        navigate("/");
      })
      .catch((error) => {
        setError("Неправильное имя пользователя или пароль.");
        console.error("Ошибка при входе:", error);
      });
  };

  return (
    <div className="d-flex justify-content-center align-items-center vh-100 text-black">
      <div
        className="form-signin bg-body-secondary p-4 rounded-3 shadow"
        style={{ maxWidth: "360px", width: "100%" }}
      >
        <form onSubmit={handleSubmit}>
          <i className="d-block mx-auto mb-4 fa-solid fa-dna fa-2x text-center"></i>
          <h1 className="h4 mb-3 fw-bold text-center">
            Вход ИС Расписание
          </h1>
          {error && <div className="alert alert-danger">{error}</div>}

          <div className="form-floating mb-3">
            <input
              type="text"
              className="form-control"
              id="floatingInput"
              placeholder="Имя пользователя"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
            <label htmlFor="floatingInput"></label>
          </div>

          <div className="form-floating mb-3">
            <input
              type="password"
              className="form-control"
              id="floatingPassword"
              placeholder="Пароль"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <label htmlFor="floatingPassword"></label>
          </div>

          <button className="w-100 btn btn-primary btn-lg mb-2" type="submit">
            Войти
          </button>
          {/* <a href="/register" className="w-100 btn btn-secondary btn-lg">
                        Зарегистрироваться
                    </a> */}
        </form>
      </div>
    </div>
  );
}

export default Login;