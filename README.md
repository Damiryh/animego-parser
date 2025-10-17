# AnimeGO parser

Парсер профиля с сайта Animego.

Из-за всех этих блокировок неплохо бы уже заиметь возможность сохранять списки аниме с пиратских сайтов локально.
Эта софтина решает 70% возникающих проблем.
Парсер написан на Python.

## Использование
```
$ animego-parser --username USERNAME [--output FILENAME] [--format FORMAT]
```

| Option | Description |
|----------------------|---------------------------------------------------------|
| --username USERNAME  | Имя пользователя, список которого нужно спарсить        |
| --output OUTPUT      | Имя выходного фала (stdout, если не указан)             |
| --format FORMAT      | Формат файла (json по умолчанию) (Пока только json :) ) |


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
