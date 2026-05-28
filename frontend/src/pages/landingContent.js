export const sharedProjects = [
  {
    title: "JouTak",
    description: "Наш основной сервер. Выживание, строительство и дружба",
    image: "/img/joutak.png",
    to: "/joutak",
  },
  {
    title: "Mini Games",
    description: "Играем в мини-игры. От классики до новейших идей",
    image: "/img/minigames.png",
    to: "/minigames",
  },
  {
    title: "Legacy 1.5.2",
    description: "Ностальгический сервер для тех, кому раньше блоки были зеленее",
    image: "/img/legacy.png",
    to: "/legacy",
  },
  {
    title: "ITMOcraft",
    description: "Клуб любителей Майнкрафта в Университете ИТМО",
    image: "/img/itmocraft.png",
    to: "/itmocraft",
    extended: true,
  },
];

export const sharedFaqItems = [
  {
    question: "Вопрос 1",
    answer: `Lorem ipsum dolor sit amet, consectetur adipiscing elit.
        Vivamus eget viverra neque, a pulvinar ipsum. Pellentesque
        interdum nibh sed urna gravida, at fringilla augue scelerisque.`,
  },
  {
    question: "Вопрос 2",
    answer: `Curabitur accumsan quam a lectus ultrices consequat.
        Praesent nec mi suscipit, placerat justo vitae, ullamcorper ex.
        Nullam vitae posuere tellus, dignissim pretium dui.`,
  },
  {
    question: "Вопрос 3",
    answer: `Aliquam consequat ipsum justo, vitae luctus ante tempus
        vitae. Nunc tellus quam, convallis nec tempus vel, mollis quis libero.
        Phasellus pharetra tellus et velit aliquam hendrerit. Proin vel dapibus neque.`,
  },
  {
    question: "Вопрос 4",
    answer: `Nunc suscipit neque vel tortor accumsan, vel vulputate mi
        feugiat. Phasellus et suscipit leo, ut posuere magna. Suspendisse est ligula,
        facilisis a neque non, mattis bibendum magna.
        Cras sit amet justo sit amet nibh ultricies sodales id sit amet nunc.`,
  },
];

export const joutakPageContent = {
  sections: [
    {
      type: "main",
      props: {
        backgroundImage: "/img/main-image.png",
        logoSrc: "/img/logo-maxi.svg",
        logoAlt: "JouTak",
        notificationUpperText: "Комьюнити",
        notificationLowerText: "Больше, чем просто сервер!",
      },
    },
    {
      type: "projects",
      props: {
        projects: sharedProjects,
      },
    },
    {
      type: "events",
      props: {
        events: [
          {
            title: "Бункер",
            description: `На сервере JouTak произошла ужасающая катастрофа.
                    Спасение есть, но доступно оно немногим.
                    Лишь избранные смогут доказать, что достойны выживания и
                    продолжения судьбы человечества.`,
            location: "JouTak",
            image: "/img/бункер.png",
            date: new Date(2026, 1, 30, 19, 0),
            to: "#",
          },
        ],
      },
    },
    {
      type: "gallery",
      props: {
        galleryItems: [
          {
            label: "JouTak SMP",
            image: "/img/gallery-bg.png",
            photos: [
              "https://cloud.joutak.ru/s/m4pmA9iX9bSKTiz/preview",
              "https://cloud.joutak.ru/s/kXFGKq4QRAsnQK2/preview",
              "https://cloud.joutak.ru/s/bRKobTnNY4aA2HT/preview",
            ],
          },
          {
            label: "ITMOcraft",
            image: "/img/gallery-bg-2.png",
            photos: [
              "https://cloud.joutak.ru/s/pGs2iz44gcc6GB8/preview",
              "https://cloud.joutak.ru/s/CjHZBKp2rKaAjsX/preview",
              "https://cloud.joutak.ru/s/yq3SSomEYryNNYD/preview",
            ],
          },
          {
            label: "MiniGames",
            image: "/img/gallery-bg-3.png",
            photos: [
              "https://cloud.joutak.ru/s/boiePJ5rDJPA9QA/preview",
              "https://cloud.joutak.ru/s/ENTw5jJmZABCEkG/preview",
              "https://cloud.joutak.ru/s/dMGLFqQDSteegSp/preview",
            ],
          },
          {
            label: "Legacy",
            image: "/img/gallery-bg-4.png",
            photos: [
              "https://cloud.joutak.ru/s/K7yf4EC9Mr7DW4r/preview",
              "https://cloud.joutak.ru/s/zKSXyDGkmfksNZJ/preview",
              "https://cloud.joutak.ru/s/DDNncCtkSgCqEtA/preview",
            ],
          },
        ],
      },
    },
    {
      type: "faq",
      props: {
        faqItems: sharedFaqItems,
      },
    },
  ],
};

export const itmoCraftPageContent = {
  sections: [
    {
      type: "main",
      props: {
        backgroundImage: "/img/bg-itmocraft-joutak.png",
        logoSrc: "/img/itmocraft-joutak-logo.svg",
        logoAlt: "Фундамент ITMOcraft",
        notificationUpperText: "Фундамент ITMOcraft",
        notificationLowerText: "Отсюда все начиналось!",
      },
    },
    {
      type: "gallery",
      props: {
        galleryItems: [
          {
            label: "Джойтак",
            image: "/img/gallery-bg.png",
            photos: [
              "#",
              "#",
              "#",
            ],
          },
          {
            label: "Казахстан",
            image: "/img/gallery-bg-2.png",
            photos: [
              "#",
              "#",
              "#",
            ],
          },
          {
            label: "Богемия",
            image: "/img/gallery-bg-3.png",
            photos: [
              "#",
              "#",
              "#",
            ],
          },
          {
            label: "Tokyo :3",
            image: "/img/gallery-bg-4.png",
            photos: [
              "#",
              "#",
              "#",
            ],
          },
        ],
      },
    },
  ],
};

export const miniGamesPageContent = {
  sections: [
    {
      type: "main",
      props: {
        backgroundImage: "/img/bg-minigames.png",
        logoSrc: "/img/minigames-logo.svg",
        logoAlt: "MiniGames",
        showNotification: false,
      },
    },
    {
      type: "projects",
      props: {
        title: "Режимы",
        projects: [
          {
            title: "Block Party",
            description: `Игроки находятся на платформе с постоянно меняющимся рисунком. 
            Задача вовремя встать на блок нужного цвета. 
            Осторожно: времени на поиск блока становится все меньше, а к ужесточенной борьбе подключаются снежки...`,
            image: "/img/block-party.png",
            imageHeight: "248px",
            to: "/minigames",
          },
          {
            title: "Ace Race",
            description: `Стремительная паркур-гонка в невесомости. Сохраняй хороший ритм и побивай 
все рекорды!`,
            image: "/img/ace-race.png",
            imageHeight: "248px",
            to: "/minigames",
          },
          {
            title: "Survival Games",
            description: "Игра на выживание в стиле Королевской битвы",
            image: "/img/survival-games.png",
            imageHeight: "248px",
            to: "/minigames",
          },
          {
            title: "Splatoon",
            description: "Используй сплат-пушку, чтобы закрасить белую карту своим цветом и превратить всё вокруг в яркую композицию (?)",
            image: "/img/splatoon.png",
            imageHeight: "248px",
            to: "/minigames",
          },
          {
            title: "Spooky Wars",
            description: "Защищайте своё сердце и бла бла бла",
            image: "/img/spooky-wars.png",
            imageHeight: "248px",
            to: "/minigames",
          },
          {
            title: "The walls",
            description: "На этом мои полномочия всё :(",
            image: "/img/the-walls.png",
            imageHeight: "248px",
            to: "/minigames",
          },
        ],
      },
    },
    {
      type: "events",
      props: {
        events: [
          {
            title: "Спартакиада",
            description: `Каждый семестр сервер MiniGames становится площадкой для спартакиады в университете ИТМО. 
            У каждого есть возможность почуствовать себя настоящим 
            киберспортсменом и получить реальные баллы по физ-ре. Следи за новостями, чтобы ничего не пропустить!`,
            location: "MiniGames",
            image: "/img/minigames-event.png",
            imageWidth: "560px",
            date: new Date(2026, 6, 10, 18, 0),
            to: "#",
          },
        ],
      },
    },
    {
      type: "gallery",
      props: {
        galleryItems: [
          {
            label: "Лобби",
            image: "/img/gallery-bg.png",
            photos: [
              "#",
              "#",
              "#",
            ],
          },
          {
            label: "Block Party",
            image: "/img/gallery-bg-2.png",
            photos: [
              "#",
              "#",
              "#",
            ],
          },
          {
            label: "Ace Race",
            image: "/img/gallery-bg-3.png",
            photos: [
              "#",
              "#",
              "#",
            ],
          },
          {
            label: "Survival Games",
            image: "/img/gallery-bg-4.png",
            photos: [
              "#",
              "#",
              "#",
            ],
          },
          {
            label: "Splatoon",
            image: "/img/gallery-bg-3.png",
            photos: [
              "#",
              "#",
              "#",
            ],
          },
        ],
      },
    },
    
  ],
};
