import { Alert, ThemeProvider } from "@gravity-ui/uikit";
import { useState } from "react";

import cl from "./NotificationBanner.module.css";

export default function NotificationBanner({ defaultHidden = false, ...data }) {
  const [isDismissed, setIsDismissed] = useState(defaultHidden);
  const [isLightTheme, setIsLightTheme] = useState(false);
  const classes = [cl.notification];

  if (isDismissed) {
    classes.push(cl.hide);
  }

  return (
    <div className={classes.join(" ")}>
      <ThemeProvider theme={isLightTheme ? "light" : "dark"}>
        <Alert
          align="center"
          onClose={() => setIsDismissed(true)}
          corners="square"
          title={data.title}
          message={data.message}
          theme={data.theme}
          actions={
            <Alert.Action onClick={() => setIsLightTheme(!isLightTheme)}>
              Смена темы уведомления
            </Alert.Action>
          }
        />
      </ThemeProvider>
    </div>
  );
}
