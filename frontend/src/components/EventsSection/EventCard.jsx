import MinecraftButton from "../MineCraftButton/MinecraftButton";
import styles from "./eventCard.module.css";
import { FiCalendar } from "react-icons/fi";
import { GrLocation } from "react-icons/gr";

export default function EventCard({
    title,
    description,
    location,
    image,
    date,
    to,
}) {

    const formattedDate = new Date(date).toLocaleString("ru-RU", {
        day: "2-digit",
        month: "long",
        hour: "2-digit",
        minute: "2-digit",
    });
    return (
        <div className={styles.card}>
            <div className={styles.text}>
                <h3 className={styles.title}>{title}</h3>
                <p className={styles.info}><FiCalendar /> {formattedDate}</p>    
                <p className={styles.info}><GrLocation /> {location}</p>
                <p className={styles.description}>{description}</p>
                <MinecraftButton
                // onClick={() => navigate(to)}
                >
                    регистрация
                </MinecraftButton>
            </div>
            <img className={styles.eventImg} src={image} width="739" />
        </div>
    )
}