import "../assets/Forbidden.css";

import { useState } from "react";

import darkModeIconUrl from "../assets/images/dark-mode-icon.svg";
import lightModeIconUrl from "../assets/images/light-mode-icon.svg";
import wardenUrl from "../assets/images/warden.png";

export default function Forbidden() {
  const [darkMode, setDarkMode] = useState(false);

  return (
    <div className={`error-page forbidden-page ${darkMode ? "darkmode" : ""}`}>
      <header>
        <button
          id="theme-switch"
          onClick={() => setDarkMode(!darkMode)}
          aria-label="кнопка, которая переключает тему страницы между темной и светлой"
        >
          <img
            src={lightModeIconUrl}
            alt="иконка солнца, символизирующая светлую тему страницы"
          />
          <img
            src={darkModeIconUrl}
            alt="иконка луны, символизирующая тёмную тему страницы"
          />
        </button>
      </header>

      <main className="forbidden-content">
        <img
          id="warden"
          src={wardenUrl}
          alt="варден, который символизирует ограниченный доступ"
        />
        <div className="page-info">
          <h1>403</h1>
          <h2>FORBIDDEN</h2>

          <p className="light-font">
            Страница существует, но у вас нет прав доступа.
          </p>

          <p className="hint light-font">
            Вы можете вернуться на главную или попробовать другой аккаунт.
          </p>

          <div className="buttons">
            <button
              onClick={() => window.history.back()}
              className="secondary-btn"
            >
              Назад
            </button>
            <a href="/" className="primary-btn">
              На главную
            </a>
            <a href="https://cloud.joutak.ru/login" className="tertiary-btn">
              Сменить аккаунт
            </a>
          </div>
        </div>
      </main>
    </div>
  );
}
