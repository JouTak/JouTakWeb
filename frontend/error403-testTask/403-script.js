const hasAccess = false
const path = window.location.pathname

function showError403Page() {
    document.body.innerHTML = `
    <header>
        <button id="theme-switch">
            <img src="images/light-mode-icon.svg" alt="иконка солнца, символизирующая светлую тему страницы">
            <img src="images/dark-mode-icon.svg" alt="иконка луны, символизирующая тёмную тему страницы">
        </button>
    </header>
    
    <main class="container">
        <img id="warden" src="images/warden.png" alt="варден, который символизирует ограниченный доступ">
        <div class="page-info">
            <h1>403</h1>
            <h2>FORBIDDEN</h2>
            <img id="table" src="images/error-info.png" alt="табличка, на которой написано, что у пользователя нет доступа к этой странице">

            <div class="buttons">
                <a href="javascript:history.back()"><img src="images/back-btn.png" alt="кнопка, чтобы вернуться назад"></a>
                <a href="#"><img src="images/main-page-btn.png" alt="ссылка, чтобы вернуться на главную страницу"></a>
                <a href="https://cloud.joutak.ru/login"><img src="images/change-acc-btn.png" alt="кнопка, чтобы сменить аккаунт"></a>
            </div>
        </div>
    </main>`

    const switchThemeBtn = document.getElementById("theme-switch")

    switchThemeBtn.addEventListener('click', () => {
        document.body.classList.toggle('darkmode')
    })
}

if (path.includes('403.html')) {
    showError403Page()
}

if (path.includes('restricted.html')) {
    if (!hasAccess) {
        showError403Page()
    } else {
       document.body.innerHTML = '<p>доступ разрешен! вы на секретной страничке)</p>'
    }
}

