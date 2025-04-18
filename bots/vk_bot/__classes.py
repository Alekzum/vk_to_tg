# dict(
#     photo=lambda _obj: (
#         [
#             photik["url"]
#             for photik in sorted(
#                 _obj["photo"].get("sizes", []), key=lambda x: x["height"], reverse=True
#             )
#             if photik["type"] in ["w", "z", "x"]
#         ]
#         or [
#             f"https://vk.com/photo{_obj['photo'].get('owner_id', '???')}_{_obj['photo'].get('id', '???')}"
#         ]
#     )[0],
#     video=lambda _obj: _obj["video"]["link"],
#     audio=lambda _obj: _obj["audio"]["url"],
#     doc=lambda _obj: (_obj["doc"]["url"], f"{_obj['doc']['title']} (document)"),
#     market=lambda _obj: f"Артикул: {_obj['market']['sku']}",
#     market_album=lambda _obj: f"Название: {_obj['market_album']['title']}, id владельца: {_obj['market_album']['owner_id']}",
#     wall_reply=lambda _obj: f"№{_obj['wall_reply']['id']} от пользователя №{_obj['wall_reply']['owner_id']}",
#     sticker=lambda _obj: _obj["sticker"]["images"][-1]["url"],
#     gift=lambda _obj: _obj["gift"]["thumb_256"],
#     audio_message=lambda _obj: _obj["audio_message"]["link_mp3"],
#     wall=lambda _obj: f"https://vk.com/wall{_obj['wall']['from_id']}_{_obj['wall']['id']}",
#     link=lambda _obj: _obj["link"]["url"],
# )


'''
@dataclass
class Media:
    type: str
    access_key: Optional[str] = None
    photo: Optional["Photo"] = None
    video: Optional["Video"] = None
    audio: Optional["Audio"] = None
    doc: Optional["Document"] = None
    market: Optional["Market"] = None
    market_album: Optional["MarketAlbum"] = None
    wall_reply: Optional["WallReply"] = None
    sticker: Optional["Sticker"] = None
    gift: Optional["VkObject"] = None
    audio_message: Optional["AudioMessage"] = None
    wall: Optional["Wall"] = None
    link: Optional["Link"] = None


@dataclass
class ShortMedia:
    id: str
    type: str


@dataclass
class ShortMedias(list[ShortMedia]):
    def __init__(self, raw: dict[str, str]):
        self = [ShortMedia(id=raw[i], type=raw[f"{i}_type"]) for i in raw if not i.endswith("_type")]


@dataclass
class PhotoCopy(Media):
    type: str
    url: str
    width: int
    height: int


@dataclass
class Photo(Media):
    id: int
    """Идентификатор фотографии"""
    album_id: int
    """Идентификатор альбома, в котором находится фотография"""
    owner_id: int
    """Идентификатор владельца фотографии"""
    user_id: int
    """Идентификатор пользователя, загрузившего фото (если фотография размещена в сообществе). Для фотографий, размещенных от имени сообщества, user_id = 100"""
    text: str
    """Текст описания фотографии"""
    date: int
    """Дата добавления в формате Unixtime"""
    sizes: list[PhotoCopy]
    """Массив с копиями изображения в разных размерах"""
    width: Optional[int]
    """Значения могут быть недоступны для фотографий, загруженных на сайт до 2012 года"""
    height: Optional[int]
    """Значения могут быть недоступны для фотографий, загруженных на сайт до 2012 года"""


@dataclass
class Video(Media):
    ...
    """id
    integer Идентификатор видеозаписи.

    owner_id
    integer Идентификатор владельца видеозаписи.

    title
    string Название видеозаписи.

    description
    string Текст описания видеозаписи.

    duration
    integer Длительность ролика в секундах.

    image
    array Изображение обложки. Содержит массив объектов с полями:

    •     height (integer) — высота изображения.
    •     url (string) — ссылка на изображение.
    •     width (integer) — ширина изображения.
    •     with_padding (integer) — поле возвращается, если изображение с отбивкой, всегда содержит 1.
    first_frame
    array Изображение первого кадра. Содержит массив объектов с полями:

    •     height (integer) — высота изображения.
    •     url (string) — ссылка на изображение.
    •     width (integer) — ширина изображение.
    date
    integer Дата создания видеозаписи в формате Unixtime.

    adding_date
    integer Дата добавления видеозаписи пользователем или группой в формате Unixtime.

    views
    integer Количество просмотров видеозаписи.

    local_views
    integer Если видео внешнее, количество просмотров ВКонтакте.

    comments
    integer Количество комментариев к видеозаписи. Поле не возвращается, если комментарии недоступны.

    player
    string URL страницы с плеером, который можно использовать для воспроизведения ролика в браузере. Поддерживается flash и HTML5, плеер всегда масштабируется по размеру окна.

    platform
    string Название платформы (для видеозаписей, добавленных с внешних сайтов).

    can_add
    integer Может ли пользователь добавить видеозапись к себе.

    •     0 — не может добавить.
    •     1 — может добавить.
    is_private
    integer Поле возвращается, если видеозапись приватная (например, была загружена в личное сообщение), всегда содержит 1.

    access_key
    string Ключ доступа к объекту. Подробнее см. Ключ доступа к данным access_key.

    processing
    integer Поле возвращается в том случае, если видеоролик находится в процессе обработки, всегда содержит 1.

    is_favorite
    boolean true, если объект добавлен в закладки у текущего пользователя.

    can_comment
    integer Может ли пользователь комментировать видео.

    •     0 — не может комментировать.
    •     1 — может комментировать.
    can_edit
    integer Может ли пользователь редактировать видео.

    •     0 — не может редактировать.
    •     1 — может редактировать.
    can_like
    integer Может ли пользователь добавить видео в список <<Мне нравится>>.

    •     0 — не может добавить.
    •     1 — может добавить.
    can_repost
    integer Может ли пользователь сделать репост видео.

    •     0 — не может сделать репост.
    •     1 — может сделать репост.
    can_subscribe
    integer Может ли пользователь подписаться на автора видео.

    •     0 — не может подписаться.
    •     1 — может подписаться.
    can_add_to_faves
    integer Может ли пользователь добавить видео в избранное.

    •     0 — не может добавить.
    •     1 — может добавить.
    can_attach_link
    integer Может ли пользователь прикрепить кнопку действия к видео.

    •     0 — не может прикрепить.
    •     1 — может прикрепить.
    width
    integer Ширина видео.

    height
    integer Высота видео.

    user_id
    integer Идентификатор пользователя, загрузившего видео, если оно было загружено в группу одним из участников.

    converting
    integer Конвертируется ли видео.

    •     0 — не конвертируется.
    •     1 — конвертируется.
    added
    integer Добавлено ли видео в альбомы пользователя.

    •     0 — не добавлено.
    •     1 — добавлено.
    is_subscribed
    integer Подписан ли пользователь на автора видео.

    •     0 — не подписан.
    •     1 — подписан.
    repeat
    integer Поле возвращается в том случае, если видео зациклено, всегда содержит 1

    type
    string Тип видеозаписи. Может принимать значения: video, music_video, movie.

    balance
    integer Баланс донатов в трансляции.

    live
    integer Поле возвращается в том случае, если видеозапись является трансляцией, всегда содержит 1. Обратите внимание, в этом случае в поле duration содержится значение 0.

    live_start_time
    integer Дата и время начала трансляции. Указывается в виде целого числа (Unix Timestamp).

    live_status
    string Статус трансляции. Может принимать значения: waiting, started, finished, failed, upcoming.

    upcoming
    integer Поле свидетельствует о том, что трансляция скоро начнётся. Для live =1.

    spectators
    integer Количество зрителей трансляции.

    likes
    object Содержит объект отметки «Мне нравится».

    •     count (integer) — количество лайков.

    •     user_likes (integer) — добавлено ли видео в список «Мне нравится» текущего пользователя.

    •     0 — не добавлено.
    •     1 — добавлено.
    reposts
    object Содержит объект репоста.

    •     count (integer) — счетчик общего количества репостов. Содержит сумму репостов на стену и в личные сообщения.
    •     wall_count (integer) — счетчик репостов на стену.
    •     mail_count (integer) — счетчик репостов в личные сообщения.
    •     user_reposted (integer) — информация о том, сделал ли текущий пользователь репост этого видео."""


@dataclass
class Audio(Media):
    ...
    """id
integer Идентификатор аудиозаписи.

owner_id
integer Идентификатор владельца аудиозаписи.

artist
string Исполнитель.

title
string Название композиции.

duration
integer Длительность аудиозаписи в секундах.

url
string Ссылка на mp3.

lyrics_id
integer Идентификатор текста аудиозаписи (если доступно).

album_id
integer Идентификатор альбома, в котором находится аудиозапись (если присвоен).

genre_id
integer Идентификатор жанра из списка аудио жанров.

date
integer Дата добавления.

no_search
integer 1, если включена опция «Не выводить при поиске». Если опция отключена, поле не возвращается.

is_hq
integer 1, если аудио в высоком качестве.

Версии API ниже 5.0
Для версий ниже 5.0 названия полей и их структура отличаются от приведенных выше. Мы не рекомендуем использовать версии ниже 5.0.

aid
integer Идентификатор аудиозаписи

owner_id
integer Идентификатор владельца аудиозаписи.

artist
string Исполнитель.

title
string Название композиции.

duration
integer Длительность аудиозаписи в секундах.

url
string Ссылка на mp3.

lyrics_id
integer Идентификатор текста аудиозаписи (если доступно).

album
integer Идентификатор альбома, в котором находится аудиозапись (если присвоен).

genre
integer Идентификатор жанра из списка аудио жанров."""
    ...


@dataclass
class Document(Media):
    """id
integer Идентификатор файла.

owner_id
integer Идентификатор пользователя, загрузившего файл.

title
string Название файла.

size
integer Размер файла в байтах.

ext
string Расширение файла.

url
string Адрес файла, по которому его можно загрузить.

date
integer Дата добавления в формате Unixtime.

type
integer Тип файла. Возможные значения:

• 1 — текстовые документы;
• 2 — архивы;
• 3 — gif;
• 4 — изображения;
• 5 — аудио;
• 6 — видео;
• 7 — электронные книги;
• 8 — неизвестно.
preview
object Информация для предварительного просмотра файла. Может содержать следующие поля:

• photo (object) — изображения для предпросмотра. Содержит единственное поле:
• sizes (array) — массив копий изображения в разных размерах. Подробное описание структуры вы найдёте на этой странице.
• graffiti (object) — данные о граффити. Содержит следующие поля:
• src (string) — URL файла с граффити;
• width (integer) — ширина изображения в px;
• height (integer) — высота изображения в px.
• audio_message — данные об аудиосообщении. Объект, который содержит следующие поля:
• duration (integer) — длительность аудиосообщения в секундах;
• waveform (array) — массив значений (integer) для визуального отображения звука;
• link_ogg (string) — URL .ogg-файла;
• link_mp3 (string) — URL .mp3-файла.

"""
    ...


@dataclass
class Market(Media):
    """id
integer Идентификатор товара.

owner_id
integer Идентификатор владельца товара.

title
string Название товара.

description
string Текст описания товара.

price
object Цена. Объект, содержащий поля:

• amount (string) — цена товара в сотых долях единицы валюты.
• currency (object) — валюта. Объект, содержащий поля:
• id (integer) — идентификатор валюты.
• name(string) — обозначение валюты.
• old_amount (string) — старая цена товара в сотых долях единицы валюты.
• text (string) — строковое представление цены.
dimensions
object Габариты товара. Объект, содержащий поля:

• width (integer) — ширина в миллиметрах.
• height (integer) — высота в миллиметрах.
• length (integer) — длина в миллиметрах.
weight
integer Вес в граммах.

category
object Категория товара. Объект, содержащий поля:

• id (integer) — идентификатор категории.
• name (string) — название категории.
• section (object) — секция. Объект, содержащий поля:
• id (integer) — идентификатор секции.
• name (string) — название секции.
thumb_photo
string URL изображения-обложки товара.

date
integer Дата создания товара в формате Unixtime.

availability
integer Статус доступности товара. Возможные значения:

• 0 — товар доступен.
• 1 — товар удален.
• 2 — товар недоступен.
is_favorite
boolean true, если объект добавлен в закладки у текущего пользователя.

sku
string Артикул товара, произвольная строка длиной до 50 символов.

reject_info
object Информация о модерации товара, если товар не прошёл модерацию. Объект, содержащий поля:

• title (string) — название причины отклонения товара.
• description (string) — описание причины блокировки.
• buttons (object) — кнопки «Удалить» и «Написать в поддержку».
• moderation_status (integer) — числовое представление статуса модерации.
• info_link (string) — ссылка на правила модерации.
• white_to_support_link (string) — ссылка на поддержку.
"""
    ...


@dataclass
class MarketAlbum(Media):
    """id
integer Идентификатор подборки.

owner_id
integer Идентификатор владельца подборки.

title
string Название подборки.

is_main
boolean Является ли подборка основной.

is_hidden
boolean Является ли подборка скрытой.

photo
object Обложка подборки, объект, описывающий фотографию.

count
integer Число товаров в подборке."""
    ...


@dataclass
class WallReply(Media):
    """id
integer Идентификатор комментария.

from_id
integer Идентификатор автора комментария.

date
integer Дата создания комментария в формате Unixtime.

text
string Текст комментария.

donut
object Информация о VK Donut. Объект со следующими полями:

• is_don (boolean) — является ли комментатор подписчиком VK Donut.
• placeholder (string) — заглушка для пользователей, которые не оформили подписку VK Donut.
reply_to_user
integer Идентификатор пользователя или сообщества, в ответ которому оставлен текущий комментарий (если применимо).

reply_to_comment
integer Идентификатор комментария, в ответ на который оставлен текущий (если применимо).

attachments
object Медиавложения комментария (фотографии, ссылки и т.п.). Описание массива attachments находится на отдельной странице.

parents_stack
array Массив идентификаторов родительских комментариев.

thread
object Информация о вложенной ветке комментариев, объект с полями:

• count (integer) — количество комментариев в ветке.
• items (array) — массив объектов комментариев к записи (только для метода wall.getComments).
• can_post (boolean) – может ли текущий пользователь оставлять комментарии в этой ветке.
• show_reply_button (boolean) – нужно ли отображать кнопку «ответить» в ветке.
• groups_can_post (boolean) – могут ли сообщества оставлять комментарии в ветке.
"""
    ...


@dataclass
class AudioMessage(Media):
    """id
integer Идентификатор голосового сообщения.

owner_id
integer Идентификатор пользователя, загрузившего голосовое сообщение.

duration
integer Длительность аудиосообщения в секундах.

waveform
array Массив значений (integer) для визуального отображения звука.

link_ogg
string URL .ogg-файла.

link_mp3
string URL .mp3-файла."""
    ...


@dataclass
class Wall(Media):
    """id
integer

Идентификатор записи.

owner_id
integer

Идентификатор владельца стены, на которой размещена запись. В версиях API ниже 5.7 это поле называется to_id.

from_id
integer

Идентификатор автора записи (от чьего имени опубликована запись).

created_by
integer

Идентификатор администратора, который опубликовал запись (возвращается только для сообществ при запросе с ключом доступа администратора). Возвращается в записях, опубликованных менее 24 часов назад.

date
integer

Время публикации записи в формате unixtime.

text
string

Текст записи.

reply_owner_id
integer

Идентификатор владельца записи, в ответ на которую была оставлена текущая.

reply_post_id
integer

Идентификатор записи, в ответ на которую была оставлена текущая.

friends_only
integer

1, если запись была создана с опцией «Только для друзей».

comments
object

Информация о комментариях к записи, объект с полями:

• count (integer) — количество комментариев;
• can_post* (integer) — информация о том, может ли текущий пользователь комментировать запись (1 — может, 0 — не может);
• groups_can_post (boolean) — информация о том, могут ли сообщества комментировать запись;
• can_close(boolean) — может ли текущий пользователь закрыть комментарии к записи;
• can_open(boolean) — может ли текущий пользователь открыть комментарии к записи.
copyright
object

Источник материала, объект с полями:

• id (integer);
• link* (string);
• name* (string);
• type* (string).
likes
object

Информация о лайках к записи, объект с полями:

• count (integer) — число пользователей, которым понравилась запись;
• user_likes* (integer) — наличие отметки «Мне нравится» от текущего пользователя (1 — есть, 0 — нет);
• can_like* (integer) — информация о том, может ли текущий пользователь поставить отметку «Мне нравится» (1 — может, 0 — не может);
• can_publish* (integer) — информация о том, может ли текущий пользователь сделать репост записи (1 — может, 0 — не может).
reposts
object

Информация о репостах записи («Рассказать друзьям»), объект с полями:

• count (integer) — число пользователей, скопировавших запись;
• user_reposted* (integer) — наличие репоста от текущего пользователя (1 — есть, 0 — нет).
views
object

Информация о просмотрах записи. Объект с единственным полем:

• count (integer) — число просмотров записи.
post_type
string

Тип записи, может принимать следующие значения: post, copy, reply, postpone, suggest.

post_source
object

Поле возвращается только для Standalone-приложений с ключом доступа, полученным в Implicit Flow.

Информация о способе размещения записи. Описание объекта находится на отдельной странице.

attachments
array

Массив объектов, соответствующих медиаресурсам, прикреплённым к записи: фотографиям, документам, видеофайлам и другим. Подробное описание — в разделе Медиавложения в записях на стене.

geo
object

Информация о местоположении , содержит поля:

• type (string) — тип места;
• coordinates (string) — координаты места;
• place (object) — описание места (если оно добавлено). Объект места.
signer_id
integer

Идентификатор автора, если запись была опубликована от имени сообщества и подписана пользователем;

copy_history
array

Массив, содержащий историю репостов для записи. Возвращается только в том случае, если запись является репостом. Каждый из объектов массива, в свою очередь, является объектом-записью стандартного формата.

can_pin
integer

Информация о том, может ли текущий пользователь закрепить запись (1 — может, 0 — не может).

can_delete
integer

Информация о том, может ли текущий пользователь удалить запись (1 — может, 0 — не может).

can_edit
integer

Информация о том, может ли текущий пользователь редактировать запись (1 — может, 0 — не может).

is_pinned
integer

Информация о том, что запись закреплена.

marked_as_ads
integer

Информация о том, содержит ли запись отметку «реклама» (1 — да, 0 — нет).

is_favorite
boolean

true, если объект добавлен в закладки у текущего пользователя.

donut
object

Информация о записи VK Donut:

• is_donut (boolean) — запись доступна только платным подписчикам VK Donut;
• paid_duration (integer) — время, в течение которого запись будет доступна только платным подписчикам VK Donut;
• placeholder (object) — заглушка для пользователей, которые не оформили подписку VK Donut. Отображается вместо содержимого записи.
• can_publish_free_copy (boolean) — можно ли открыть запись для всех пользователей, а не только подписчиков VK Donut;
• edit_mode (string) — информация о том, какие значения VK Donut можно изменить в записи. Возможные значения:
• all — всю информацию о VK Donut.
• duration — время, в течение которого запись будет доступна только платным подписчикам VK Donut.
postponed_id
integer

Идентификатор отложенной записи. Это поле возвращается тогда, когда запись стояла на таймере.


"""
    ...


@dataclass
class Link(Media):
    """url
string URL ссылки.

title
string Заголовок ссылки.

caption
string Подпись ссылки (если имеется).

description
string Описание ссылки.

photo
object Изображение превью, объект фотографии (если имеется).

product
object Информация о продукте (если имеется). Поле возвращается для ссылок на магазины, например, AliExpress. Объект с единственным полем price (object), которое описано на отдельной странице.

button
object Информация о кнопке для перехода (если имеется). Объект описан на отдельной странице.

preview_page
string Идентификатор вики-страницы с контентом для предпросмотра содержимого страницы. Возвращается в формате "owner_id_page_id".

preview_url
string URL страницы с контентом для предпросмотра содержимого страницы."""
    ...


@dataclass
class Sticker(Media):
    """inner_type
string Тип, который описывает вариант формата ответа. По умолчанию: "base_sticker_new"

sticker_id
integer Идентификатор стикера

product_id
integer Идентификатор набора

is_allowed
boolean Информация о том, доступен ли стикер

Объект, описывающий стикер, содержит следующие поля (с версии 5.74) для приложений, которым возвращаются ссылки на изображения:

inner_type
string Тип, который описывает вариант формата ответа. По умолчанию: "base_sticker_new"

sticker_id
integer Идентификатор стикера

product_id
integer Идентификатор набора

images
array Изображения для стикера (с прозрачным фоном). Массив, каждый объект в котором содержит поля:

• url (string) — URL копии изображения;
• width (integer) — ширина копии в px;
• height (integer) — высота копии в px.
images_with_background
array Изображения для стикера (с непрозрачным фоном). Массив, каждый объект в котором содержит поля:

• url (string) — URL копии изображения;
• width (integer) — ширина копии в px;
• height (integer) — высота копии в px.
animation_url
string URL анимации стикера (для анимированных стикеров)

is_allowed
boolean Информация о том, доступен ли стикер


"""
    ...


class VkObject:
    def __init__(self, **kwargs):
        [setattr(self, n, kwargs[n]) for n in kwargs]
        # good luck.


@dataclass
class MessageData:
    attachments: list[Media] | None = None
    conversation_message_id: int | None = None
    date: int | None = None
    from_id: int | None = None
    fwd_messages: list | None = None
    id: int | None = None
    important: bool | None = None
    is_hidden: bool | None = None
    out: bool | None = None
    peer_id: int | None = None
    random_id: int | None = None
    text: str | None = None
    version: int | None = None


@dataclass
class Update(Event):
    raw: list

    type: VkEventType | int
    from_user = False
    from_chat = False
    from_group = False
    from_me = False
    to_me = False

    attachments: list[Media] | ShortMedias = None
    message_data = None
    message_id = None
    timestamp = None
    peer_id = None
    flags = None
    extra = None
    extra_values = None
    type_id = None

    # attachments: dict
    # datetime: str
    # extra: None
    # extra_values: dict
    # flags: int
    # from_chat: bool
    # from_group: bool
    # from_me: bool
    # from_user: bool
    # message: str
    # message_data: dict
    # message_flags: str
    # message_id: int
    # peer_id: int
    # raw: list
    # text: str
    # timestamp: int
    # title: str
    # to_me: bool
    # type: int
    # type_id: None
    # user_id: int

    def __post_init__(self, raw: dict):
        self.attachments = ShortMedias(raw['attachments'])
'''
