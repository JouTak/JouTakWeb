import { Link, useNavigate } from "react-router-dom";
import MinecraftButton from "../MineCraftButton/MinecraftButton";
import styles from "./eventCard.module.css";

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

    let navigate = useNavigate()
    return (
        <div className="event-card">
            <div className="event-info">
                <h3>{title}</h3>
                <p>{formattedDate}</p>
                <p>{location}</p>
                <p>{description}</p>
                <MinecraftButton 
                // onClick={() => navigate(to)}
                >регистрация</MinecraftButton>
            </div>
            <img src={image} />
        </div>
    )
}