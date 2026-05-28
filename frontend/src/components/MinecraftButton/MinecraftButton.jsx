import styles from "./MinecraftButton.module.css";

export default function MinecraftButton({ children, onClick, className = "" }) {
  return (
    <button className={`${styles.button} ${className}`} onClick={onClick} type="button">
      {children}
    </button>
  );
}