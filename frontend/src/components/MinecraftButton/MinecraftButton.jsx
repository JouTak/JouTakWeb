export default function MinecraftButton({ children, onClick }) {
    const styles = {

    }

    return(
        <button style={styles} onClick={onClick}>
            {children}
        </button>
    )
}