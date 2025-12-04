# AnimeGO parser

Парсер профиля с сайта Animego.

Из-за всех этих блокировок неплохо бы уже заиметь возможность сохранять списки аниме с пиратских сайтов локально.
Эта софтина решает 70% возникающих проблем.
Парсер написан на Python.

## Парсинг профиля
```
$ animego-parser profile --username USERNAME [--output FILENAME] [--format FORMAT]
```

| Option | Description |
|----------------------|---------------------------------------------------------|
| --username USERNAME  | Имя пользователя, список которого нужно спарсить        |
| --output OUTPUT      | Имя выходного файла (stdout, если не указано)           |
| --format FORMAT      | Формат данных (json, xml) (json по умолчанию)           |

### Формат вывода

#### JSON

```json
[
    {
        "title": "Этот замечательный мир!",
        "original_title": "Kono Subarashii Sekai ni Shukufuku wo!",
        "user_status": "Просмотрено",
        "user_score": "9",
        "episodes": "10/10",
        "release_type": "ТВ Сериал"
    },
    {
        "title": "Я требую яоя!",
        "original_title": "Watashi ga Motete Dousunda",
        "user_status": "Запланировано",
        "user_score": "–",
        "episodes": "0/12",
        "release_type": "ТВ Сериал"
    },
    {
        "title": "Евангелион: Конец Евангелиона",
        "original_title": "Neon Genesis Evangelion: The End of Evangelion",
        "user_status": "Просмотрено",
        "user_score": "–",
        "episodes": "–",
        "release_type": "Фильм"
    },
    ...
]
```

#### XML

```xml
<AnimeList>
    <Anime>
        <title>Этот замечательный мир!</title>
        <originalTitle>Kono Subarashii Sekai ni Shukufuku wo!</originalTitle>
        <userStatus>Просмотрено</userStatus>
        <userScore>9</userScore>
        <episodes>10/10</episodes>
        <releaseType>ТВ Сериал</releaseType>
    </Anime>
</AnimeList>
```
