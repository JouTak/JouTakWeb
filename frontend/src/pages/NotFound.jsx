import { useState } from "react"
import "../assets/NotFound.css"

export default function NotFound() {
  const [darkMode, setDarkMode] = useState(false)

  return (
    <div className={`notfound-page ${darkMode ? "darkmode" : ""}`}>
      <header>
        <button
          id="theme-switch"
          onClick={() => setDarkMode(!darkMode)}
          aria-label="кнопка, которая переключает тему страницы между темной и светлой"
        >
          <img
            src="img/light-mode-icon.svg"
            alt="иконка солнца, символизирующая светлую тему страницы"
          />
          <img
            src="img/dark-mode-icon.svg"
            alt="иконка луны, символизирующая тёмную тему страницы"
          />
        </button>
      </header>

      <main className="notfound-content">
        <h1>404</h1>
        <h2>NOT FOUND</h2>

        <p>Страница не существует или была удалена.</p>

        <div className="buttons">
          <button onClick={() => window.history.back()}>Назад</button>
          <a href="/">На главную</a>
        </div>
      </main>
    </div>
  )
}