import { useState } from "react"
import "../assets/Forbidden.css"

export default function Forbidden() {

    const [darkMode, setDarkMode] = useState(false)

    return (
        <div className={`forbidden-page ${darkMode ? "darkmode" : ""}`}>
            <header>
                <button id="theme-switch" onClick={() => setDarkMode(!darkMode)} aria-label="кнопка, которая переключает тему страницы между темной и светлой">
                    <img src="img/light-mode-icon.svg" alt="иконка солнца, символизирующая светлую тему страницы" />
                    <img src="img/dark-mode-icon.svg" alt="иконка луны, символизирующая тёмную тему страницы" />
                </button>
            </header>
            
            <main className="forbidden-content">
                <img id="warden" src="img/warden.png" alt="варден, который символизирует ограниченный доступ" />
                <div className="page-info">
                    <h1>403</h1>
                    <h2>FORBIDDEN</h2>

                    <p className="light-font">Страница существует, но у вас нет прав доступа.</p>

                    <p className="hint light-font">Вы можете вернуться на главную или попробовать другой аккаунт.</p>

                    <div className="buttons">
                        <button onClick={() => window.history.back()} className="secondary-btn">Назад</button>
                        <a href="/" className="primary-btn">На главную</a>
                        <a href="https://cloud.joutak.ru/login" className="tertiary-btn">Сменить аккаунт</a>
                    </div>
                </div>
            </main>
        </div>
    )
}