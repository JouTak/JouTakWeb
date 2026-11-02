from cities.integrations.bluemap import map_url
from cities.leadership import public_leadership
from cities.queries import card
from cities.schemas import CatalogCityOut, CityLeaderOut


def catalog_cards(query, viewer, flags):
    cities = list(query)
    leadership = public_leadership(cities, viewer, roles=("manager",))
    result = []
    for city in cities:
        leader = next(
            (person for person in leadership[city.pk] if person.username), None
        )
        result.append(
            CatalogCityOut(
                **card(city).model_dump(),
                leader=CityLeaderOut(
                    username=leader.username,
                    minecraft_nick=leader.minecraft_nick,
                    position=leader.position,
                )
                if leader
                else None,
                map_url=map_url(city)
                if flags.get("cities_map_integration")
                else None,
            )
        )
    return result
