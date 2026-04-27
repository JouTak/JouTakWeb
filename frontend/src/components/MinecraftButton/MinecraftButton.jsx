import styles from "./MinecraftButton.module.css";

export default function MinecraftButton({ children, onClick }) {
  return (
    <button className={styles.button} onClick={onClick}>
      {children}
    </button>
  );
}