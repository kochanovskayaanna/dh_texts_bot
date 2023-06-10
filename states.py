from telegram.ext import (
    ConversationHandler)

# State definitions for top level conversation
CHOOSING_SCENARIO, SCENARIO_ADD, SCENARIO_PACKET, SCENARIO_EXTRACT = map(chr, range(4))
# State definitions for descriptions conversation
SELECTING_FEATURE, TYPING = map(chr, range(4, 6))
END = ConversationHandler.END

FEATURES, CURRENT_FEATURE, START_OVER, ADD_DATA, ADD_PACKET, CONFIRMATION, SHOWING, STOPPING, SKIP, YES, \
    SEARCH = map(chr, range(6, 17))


class Info:
    TITLE, \
        CONFIRM_NO_DUPLICATES, \
        CREATOR, \
        GENRE, \
        DESCRIPTION, \
        ABSTRACT, \
        KEYWORDS, \
        KEYWORDS_RU, \
        COUNTRY_OF_ORIGIN, \
        BIBLIOGRAPHIC_CITATION, \
        DATE, \
        PUBLISHER, \
        IDENTIFIER, \
        SUBJECT, \
        MEDIATOR, \
        ADDED_BY, \
        USER_COMMENT, \
        URL, \
        STOP_INFO, \
        EDIT_FIELD, \
        EDIT_FIELD_CHOSEN, \
        EDIT_FIELD_VALUE, \
        = map(chr, range(17, 39))


class Search:
    START_SEARCH, \
        SEARCH_COLUMNS, \
        BY_AUTHOR, \
        BY_ARTICLE, \
        BY_KEYWORDS, \
        IN_ANNOTS, \
        BY_UPLOADER, \
        PAGINATOR, \
        NORES, \
        ONE_RES, \
        REVIEW_BRANCH, \
        SEARCH_BY, \
        REVIEWS_CONTAINER, \
        WRITE_REVIEW, \
        REVIEW_HANDLER = map(chr, range(39, 54))


fields = {"Библиографическая ссылка": Info.BIBLIOGRAPHIC_CITATION, "Название": Info.TITLE, "Автор": Info.CREATOR,
          "Жанр": Info.GENRE, "Страна публикации": Info.COUNTRY_OF_ORIGIN, "Год": Info.DATE,
          "Издатель": Info.PUBLISHER, "Идентификатор": Info.IDENTIFIER, "URL": Info.URL,
          "Аннотация на английском": Info.DESCRIPTION, "Аннотация на русском": Info.ABSTRACT,
          "Ключевые слова на английском": Info.KEYWORDS, "Ключевые слова на русском": Info.KEYWORDS_RU,
          "Предметная область": Info.SUBJECT, "Учебные дисциплины": Info.MEDIATOR, "Кто добавил": Info.ADDED_BY,
          "Рецензия": Info.USER_COMMENT}

fields_buttons = [[field] for field in fields]

fields_repr_dict = {
    'bibliographic_citation': "Библиографическая ссылка",
    'title': "Название",
    'creator': "Автор",
    'genre': "Жанр",
    'description': "Аннотация на английском",
    'abstract': "Аннотация на русском",
    'keywords': "Ключевые слова на английском",
    'keywords_ru': "Ключевые слова на русском",
    'country_of_origin': "Страна публикации",
    'date': "Год",
    'publisher': "Издатель",
    'identifier': "Идентификатор",
    'url': "URL",
    'subject': "Предметная область",
    'mediator': "Учебные дисциплины",
    'added_by': "Кто добавил",
    'user_comment': "Рецензия",
}
