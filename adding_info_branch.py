from telegram import (
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    Update
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    Updater,
    CallbackContext)
from states import *
from br_reference import get_text_info, preprocess_string
from db import *
from search_branch import get_maximum_likeness


async def request_bibliographic_citation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [["Пропустить"]]

    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "1/17 Добавьте библиографическую ссылку",
        reply_markup=ReplyKeyboardMarkup(
            keyboard, one_time_keyboard=True, input_field_placeholder="", resize_keyboard=True
        )
    )

    return Info.BIBLIOGRAPHIC_CITATION


async def bibliographic_citation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "Пропустить":
        context.user_data[FEATURES] = {Info.BIBLIOGRAPHIC_CITATION: None}
    else:
        text_info = get_text_info(update.message.text)
        print("text_info", text_info)
        context.user_data[FEATURES] = {Info.BIBLIOGRAPHIC_CITATION: text_info["bibliographicCitation"]}
        context.user_data[FEATURES][Info.TITLE] = text_info["title"]
        context.user_data[FEATURES][Info.CREATOR] = text_info["authors"]
        context.user_data[FEATURES][Info.DATE] = text_info["year"]
        context.user_data[FEATURES][Info.URL] = text_info["url"]
        context.user_data[FEATURES][Info.PUBLISHER] = text_info["publisher"]

    message = update.message
    if Info.TITLE in context.user_data[FEATURES].keys() and context.user_data[FEATURES][Info.TITLE] != '':
        keyboard = ReplyKeyboardMarkup([["Да"]], one_time_keyboard=True)
        await message.reply_text(
            f"2/17 Текст называется:\n\n"
            f"{context.user_data[FEATURES][Info.TITLE]}\n\n"
            f"Если нет, введите название",
            reply_markup=keyboard
        )
    else:
        await message.reply_text(
            "2/17 Напишите название текста",
            reply_markup=ReplyKeyboardRemove(),
        )
    print("Bibliographic citation: ", context.user_data[FEATURES][Info.BIBLIOGRAPHIC_CITATION])

    return Info.TITLE


async def title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text != "Да":
        context.user_data[FEATURES][Info.TITLE] = update.message.text

    cursor.execute(f'SELECT title FROM texts')
    rows = cursor.fetchall()
    rows = [row[0] for row in rows]
    duplicates = get_maximum_likeness("digital", rows, 0.9)
    # if len(duplicates) > 0:
    #     text = "В репозитории есть похожие тексты — сравните вводимый текст с ним. Добавляемый текст уникален?\n\n"
    #     for i, (coef, ind) in enumerate(duplicates):
    #         text += f"{i + 1}) {rows[ind]}"
    # buttons = [
    #     [InlineKeyboardButton("Да, такого текста пока нет", callback_data=str(SCENARIO_ADD))],
    #     [InlineKeyboardButton("Нет, прервать загрузку", callback_data=str(SCENARIO_PACKET))],
    # ]
    #     await update.message.reply_text(
    #         "3/17 Добавьте фамилии и инициалы всех авторов через запятую",
    #         reply_markup=ReplyKeyboardRemove(),
    #     )

    message = update.message
    if Info.CREATOR in context.user_data[FEATURES].keys() and context.user_data[FEATURES][Info.CREATOR] != '':
        keyboard = ReplyKeyboardMarkup([["Верно"]], one_time_keyboard=True)

        await message.reply_text(
            f"3/17 Автор(ы) — "
            f"{context.user_data[FEATURES][Info.CREATOR]}?\n\n"
            f"Если здесь есть ошибки, добавьте фамилии и инициалы всех авторов через запятую",
            reply_markup=keyboard
        )
    else:
        await message.reply_text(
            "3/17 Добавьте фамилии и инициалы всех авторов через запятую",
            reply_markup=ReplyKeyboardRemove(),
        )
    print("Title: ", context.user_data[FEATURES][Info.TITLE])

    return Info.CREATOR


async def creator(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = "4/17 Выберите жанр текста"
    reply_keyboard = [
        ["Журнальная статья"],
        ["Текст доклада"],
        ["Статья к конференции"],
        ["Монография"],
        ["Учебное пособие"],
        ["Диссертация"],
        ["Отчет"],
        ["ВКР"],
        ["Тезисы"],
        ["Автореферат"],
        ["Слайды презентации"],
        ["Другой"],
    ]

    if update.message.text != "Верно":
        context.user_data[FEATURES][Info.CREATOR] = update.message.text
    await update.message.reply_text(
        text=text,
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True,
        ),
    )
    print("Creator: ", context.user_data[FEATURES][Info.CREATOR])

    return Info.GENRE


async def genre(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[FEATURES][Info.GENRE] = update.message.text
    keyboard = ReplyKeyboardMarkup([["Нет аннотации на английском"]],
                                   one_time_keyboard=True, resize_keyboard=True)
    reply_markup = ReplyKeyboardRemove()

    await update.message.reply_text(
        "5/17 Добавьте аннотацию на английском языке",
        reply_markup=keyboard,
    )
    print("Genre: ", context.user_data[FEATURES][Info.GENRE])

    return Info.DESCRIPTION


async def description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = "6/17 Добавьте аннотацию на русском языке"
    keyboard = ReplyKeyboardMarkup([["Нет аннотации на русском языке"]], one_time_keyboard=True, resize_keyboard=True)
    if update.message.text == "Нет аннотации на английском":
        context.user_data[FEATURES][Info.DESCRIPTION] = None
    else:
        context.user_data[FEATURES][Info.DESCRIPTION] = preprocess_string(update.message.text)
    await update.message.reply_text(
        text=text,
        reply_markup=keyboard
    )
    print("Description: ", context.user_data[FEATURES][Info.DESCRIPTION])

    return Info.ABSTRACT


async def abstract(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = "7/17 Укажите ключевые слова на английском языке"
    keyboard = ReplyKeyboardMarkup([["Нет ключевых слов на английском"]], one_time_keyboard=True)
    if update.message.text == "Нет аннотации на русском языке":
        context.user_data[FEATURES][Info.ABSTRACT] = None
    else:
        context.user_data[FEATURES][Info.ABSTRACT] = preprocess_string(update.message.text)
    await update.message.reply_text(
        text=text,
        reply_markup=keyboard
    )
    print("Abstract: ", context.user_data[FEATURES][Info.ABSTRACT])

    return Info.KEYWORDS


async def keywords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = "8/17 Укажите ключевые слова на русском языке"
    keyboard = ReplyKeyboardMarkup([["Нет ключевых слов на русском"]], one_time_keyboard=True, resize_keyboard=True)
    if update.message.text == "Нет ключевых слов на английском":
        context.user_data[FEATURES][Info.KEYWORDS] = None
    else:
        context.user_data[FEATURES][Info.KEYWORDS] = update.message.text
    await update.message.reply_text(
        text=text,
        reply_markup=keyboard
    )
    print("Keywords: ", context.user_data[FEATURES][Info.KEYWORDS])

    return Info.KEYWORDS_RU


async def keywords_ru(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = "9/17 Текст издан в России?\n\nЕсли нет, напишите название страны на русском языке"
    keyboard = ReplyKeyboardMarkup([["Да"]], one_time_keyboard=True, resize_keyboard=True)
    if update.message.text == "Нет ключевых слов на русском":
        context.user_data[FEATURES][Info.KEYWORDS_RU] = None
    else:
        context.user_data[FEATURES][Info.KEYWORDS_RU] = update.message.text

    await update.message.reply_text(
        text=text,
        reply_markup=keyboard
    )
    print("Keywords_ru: ", context.user_data[FEATURES][Info.KEYWORDS_RU])

    return Info.COUNTRY_OF_ORIGIN


async def country_of_origin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "Да":
        context.user_data[FEATURES][Info.COUNTRY_OF_ORIGIN] = "Россия"
    else:
        context.user_data[FEATURES][Info.COUNTRY_OF_ORIGIN] = update.message.text

    if Info.DATE in context.user_data[FEATURES].keys() and context.user_data[FEATURES][Info.DATE] != '':
        text = f"Текст написан в {context.user_data[FEATURES][Info.DATE]} году?\n\n" \
               f"Если нет, напишите год"
        keyboard = ReplyKeyboardMarkup([["Да", "Год неизвестен"]], one_time_keyboard=True)
    else:
        text = "10/17 Укажите год публикации"
        keyboard = ReplyKeyboardMarkup([["Год неизвестен"]], one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        text=text,
        reply_markup=keyboard,
    )
    print("Country of origin: ", context.user_data[FEATURES][Info.COUNTRY_OF_ORIGIN])

    return Info.DATE


async def date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "Год неизвестен":
        context.user_data[FEATURES][Info.DATE] = None
    elif update.message.text != "Да":
        context.user_data[FEATURES][Info.DATE] = update.message.text

    if Info.PUBLISHER in context.user_data[FEATURES].keys() and context.user_data[FEATURES][Info.PUBLISHER] != '':
        text = f"11/17 Текст издан в издательстве/журнале\n\n" \
               f"{context.user_data[FEATURES][Info.PUBLISHER]}\n\n" \
               f"Если нет, укажите издателя"
        keyboard = ReplyKeyboardMarkup([["Да", "Пропустить"]])
    else:
        text = "11/17 Где издан текст?"
        keyboard = ReplyKeyboardMarkup([["Пропустить"]], resize_keyboard=True)

    await update.message.reply_text(
        text=text,
        reply_markup=keyboard,
    )
    print("Date: ", context.user_data[FEATURES][Info.DATE])

    return Info.PUBLISHER


async def publisher(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "Пропустить":
        context.user_data[FEATURES][Info.PUBLISHER] = None
    elif update.message.text != "Да":
        context.user_data[FEATURES][Info.PUBLISHER] = update.message.text

    text = "12/17 Добавьте идентификатор DOI или ISBN\n\n" \
           "DOI (Digital Object Identifier) — для цифровых объектов. \nФормат: 10.18254/S0001228-9-1\n\n" \
           "ISBN (International Standard Book Number) — идентификатор печатных изданий\n" \
           "Формат: 978-5-8021-1573-2\n(10 цифр для изданий до 2007, 13 — после)"
    keyboard = ReplyKeyboardMarkup([["Идентификатора нет"]], resize_keyboard=True)
    await update.message.reply_text(
        text=text,
        reply_markup=keyboard
    )
    print("Publisher: ", context.user_data[FEATURES][Info.PUBLISHER])

    return Info.IDENTIFIER


async def identifier(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = "13/17 Отправьте ссылку на сведения о статье в интернете\n\n" \
           "Будет хорошо, если по ссылке открыт доступ к полнотекстовой версии. "
    keyboard = ReplyKeyboardMarkup([["Пропустить"]], one_time_keyboard=True, resize_keyboard=True)
    if update.message.text == "Идентификатора нет":
        context.user_data[FEATURES][Info.IDENTIFIER] = None
    else:
        context.user_data[FEATURES][Info.IDENTIFIER] = update.message.text
    await update.message.reply_text(
        text=text,
        reply_markup=keyboard
    )
    print("Identifier: ", context.user_data[FEATURES][Info.IDENTIFIER])

    return Info.URL


async def url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = "14/17 Укажите предметное поле текста. Например, философия, цифровая лингвистика"
    if update.message.text == "Пропустить":
        context.user_data[FEATURES][Info.IDENTIFIER] = None
    else:
        link = update.message.text
        if not link.startswith('http://') and not link.startswith('https://'):
            link = 'http://' + link
        context.user_data[FEATURES][Info.URL] = link

    await update.message.reply_text(
        text=text,
        reply_markup=ReplyKeyboardRemove()
    )
    print("URL: ", context.user_data[FEATURES][Info.IDENTIFIER])

    return Info.SUBJECT


async def subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = "15/17 В рамках каких учебных дисциплин используется или может быть использован этот текст? " \
           "Перечислите через запятую"
    keyboard = ReplyKeyboardMarkup([["Пропустить"]], one_time_keyboard=True, resize_keyboard=True)
    context.user_data[FEATURES][Info.SUBJECT] = update.message.text
    await update.message.reply_text(
        text=text,
        reply_markup=keyboard
    )
    print("Subject: ", context.user_data[FEATURES][Info.SUBJECT])

    return Info.MEDIATOR


async def mediator(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = "16/17 Напишите ваше имя и короткий титр. Они будут отображаться вместе с комментарием о тексте. \n\n" \
           "Пример: Аня Кочановская, создательница бота"
    keyboard = ReplyKeyboardMarkup([["Не хочу указывать имя"]], one_time_keyboard=True, resize_keyboard=True)
    if update.message.text == "Пропустить":
        context.user_data[FEATURES][Info.MEDIATOR] = None
    else:
        context.user_data[FEATURES][Info.MEDIATOR] = update.message.text
    await update.message.reply_text(
        text=text,
        reply_markup=keyboard
    )
    print("Mediator: ", context.user_data[FEATURES][Info.MEDIATOR])

    return Info.ADDED_BY


async def added_by(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = "17/17 Напишите рецензию на текст\n" \
            "Почему вы предлагаете этот текст? Вот несколько вопросов, на которые вы можете ответить:\n\n" \
            "1) В какой ситуации и кому полезен этот текст? \n" \
            "2) Каков контекст текста (дисциплина, метод, проект)? " \
            "Что важно понимать про контекст, чтобы прочитать текст с умом? \n" \
            "3) Почему вы читали этот текст?\n" \
            "4) В чём состоят недостатки текста и работы, которая за ним стоит?\n" \
            "5) На какие тексты стоит обратить внимание читателю, когда он прочитает этот текст? \n\n" \
            "Отправьте текст боту одним сообщением. Рецензия и имя будут видны другим пользователям"
    keyboard = ReplyKeyboardMarkup([["Не буду добавлять рецензию"]], one_time_keyboard=True, resize_keyboard=True)

    if update.message.text == "Не хочу указывать имя":
        context.user_data[FEATURES][Info.ADDED_BY] = None
    else:
        context.user_data[FEATURES][Info.ADDED_BY] = update.message.text

    await update.message.reply_text(
        text=text,
        reply_markup=keyboard
    )
    print("Added by: ", context.user_data[FEATURES][Info.ADDED_BY])

    return Info.USER_COMMENT
