const switchThemeBtn = document.getElementById("theme-switch")

switchThemeBtn.addEventListener('click', () => {
    document.body.classList.toggle('darkmode')
})