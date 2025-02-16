# JouTakWeb

[![Lint](https://github.com/JouTak/JouTakWeb/actions/workflows/CI.yml/badge.svg)](https://github.com/JouTak/JouTakWeb/actions/workflows/lint.yml)
![GitHub top language](https://img.shields.io/github/languages/top/JouTak/JouTakWeb)

## Начало работы:

Перед началом работы убедитесь, что на вашей системе установлены:

- **[Git](https://git-scm.com/downloads)** – для клонирования репозитория.
- **[Node.js](https://nodejs.org/en)** – требуется версия **20+** (желательно v22+).

## Копирование проекта с репозитория:

После проверки установки вы можете скопировать проект с репозитория введя команду:

```bash
git clone https://github.com/JouTak/JouTakWeb.git
```

## Установка node.js

Если у вас ещё не установлен Node.js нужной версии, выполните следующие шаги.

### Для \*nix-систем (Linux, macOS):

1. Установите nvm (Node Version Manager):
   ```bash
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
   ```
2. Установите Node.js версии 22:
   ```bash
   nvm install 22
   ```
3. Переключитесь на установленную версию и проверьте её:
   ```bash
   nvm use 22
   node -v     # Should print "v22.x.x".
   npm -v      # Should print "10.x.x".
   ```

### Для Windows:

1. **Установите fnm (Fast Node Manager):**
   ```bash
   winget install Schniz.fnm
   ```
2. **Установите Node.js версии 22:**
   ```bash
   fnm install 22
   ```
3. **Проверьте установленные версии:**
   ```bash
   node -v     # Should print "v22.x.x".
   npm -v      # Should print "10.x.x".
   ```

## Установка зависимостей приложения

После клонирования репозитория и проверки установки Node.js выполните следующие команды:

1. Перейдите в каталог с фронтендом:

   ```bash
   cd JouTakWeb/frontend/
   ```

2. Установите зависимости:

   ```bash
   npm install
   ```

3. Запустите проект в режиме разработки:
   ```bash
   npm run dev
   ```

## And that's it!

В случае успешного запуска в консоли будет отображен путь, по которому доступно приложение, например:  
`http://localhost:5173/`.
