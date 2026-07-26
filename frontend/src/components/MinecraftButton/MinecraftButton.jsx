import styles from "./MinecraftButton.module.css";

export default function MinecraftButton({
  children,
  className = "",
  type = "button",
  ...buttonProps
}) {
  return (
    <button
      {...buttonProps}
      className={`${styles.button} ${className}`}
      type={type}
    >
      {children}
    </button>
  );
}
