import datetime
import logging

from telegram import __version__ as TG_VER, Message

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 5):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
# project files
import adding_info_branch as add_info
from search_branch import *
from br_reference import lemmatize_eng, lemmatize_rus
from db import *

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (
        "Что вы хотите сделать?\n\nЧтобы прервать работу, отправьте команду /stop"
    )
    """Select an action: Adding parent/child or show data."""
    buttons = [
        [InlineKeyboardButton("Добавить текст", callback_data=str(SCENARIO_ADD))],
        [InlineKeyboardButton("Найти текст", callback_data=str(SCENARIO_PACKET))],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    # If we're starting over we don't need to send a new message
    if context.user_data.get(START_OVER):
        text = (
            "\nГотово! Хотите добавить еще?"
        )
        if update.callback_query is not None:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        else:
            await update.message.reply_text(text=text, reply_markup=keyboard)
    else:
        await update.message.reply_text(
            "Привет!\n"
            "\nЭто бот для работы с репозиторием научных текстов о Digital Humanities, написанных на русском языке.\n"
            "\nЦель проекта — собирать тексты русскоязычных авторов, чтобы отслеживать векторы развития научной "
            "мысли в области DH в России и навигировать студентов среди множества этих текстов. "
            "По всем вопросам — @kochanovskayaanna\n"
        )
        await update.message.reply_text(text=text, reply_markup=keyboard)

    context.user_data[START_OVER] = False
    return CHOOSING_SCENARIO


async def scenario_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = "Предстоит добавить:\n\n" \
           "— библиографическую ссылку\n" \
           "— название текста\n" \
           "— имена авторов и сведения о публикации\n" \
           "— место и год публикации\n" \
           "— ключевые слова и аннотации\n" \
           "— идентификатор DOI или ESBN\n" \
           "— информацию о том, как текст используется или может быть использован в образовательных целях\n\n" \
           "Добавьте библиографическую ссылку на первом шаге, попробуем распознать метаданные из неё. \n\n" \
           "В конце можно представиться и добавить рецензию на текст, она будет общедоступна. " \
           "Часть шагов можно пропустить, но постарайтесь ответить на все вопросы. \n\n" \
           "В конце будет возможность проверить корректность ввода и исправить ошибки. " \
           "Данные сохранятся только после финального подтверждения."

    buttons = [
        [
            InlineKeyboardButton(text="Начать", callback_data=str(ADD_DATA)),
            InlineKeyboardButton(text="Назад", callback_data=str(END)),
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    if update.callback_query is None:
        await update.message.reply_text(text=text, reply_markup=keyboard)
    else:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return CONFIRMATION


async def no_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text

    if choice == "Назад к поиску":
        return await scenario_search(update, context)
    elif choice == "Добавить текст в базу":
        await scenario_add(update, context)
    else:
        # Некорректный выбор, повторить показ клавиатуры
        return await context.user_data[Search.SEARCH_BY](update, context)


async def handle_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "Не буду добавлять рецензию":
        return await scenario_search(update, context)

    text_id = context.user_data["text_id"]
    review = update.message.text
    chat_id = context.user_data["chat_id"]
    added_by = context.user_data["added_by"]

    query = f"INSERT INTO reviews (" \
            f"text_id, review, chat_id, added_by) " \
            f"VALUES (?, ?, ?, ?)"
    values = (
        text_id, review, chat_id, added_by
    )

    cursor.execute(query, values)
    conn.commit()

    context.user_data[START_OVER] = True
    await start(update, context)
    return END


async def end_scenario_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return to top level conversation."""
    context.user_data[START_OVER] = True
    await start(update, context)

    return END


async def end_scenario_add_packet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return to top level conversation."""
    context.user_data[START_OVER] = True
    await start(update, context)

    return END


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End Conversation by command."""
    await update.message.reply_text("Вы завершили работу. Чтобы начать сначала, отправьте команду /start")
    return END


async def stop_nested(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Вы завершили работу. Чтобы начать сначала, отправьте команду /start")

    return STOPPING


async def answer_user_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "Не буду добавлять рецензию":
        context.user_data[FEATURES][Info.USER_COMMENT] = None
    else:
        context.user_data[FEATURES][Info.USER_COMMENT] = update.message.text
    return await finish_adding_info(update, context)


async def finish_adding_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = "Сведения о тексте\n\n" \
           f"Библиографическая ссылка: {context.user_data[FEATURES][Info.BIBLIOGRAPHIC_CITATION]}\n\n" \
           f"Название: {context.user_data[FEATURES][Info.TITLE]}\n" \
           f"Автор: {context.user_data[FEATURES][Info.CREATOR]}\n" \
           f"Жанр: {context.user_data[FEATURES][Info.GENRE]}\n\n" \
           f"Страна публикации: {context.user_data[FEATURES][Info.COUNTRY_OF_ORIGIN]}\n" \
           f"Год: {context.user_data[FEATURES][Info.DATE]}\n" \
           f"Издатель: {context.user_data[FEATURES][Info.PUBLISHER]}\n\n" \
           f"Идентификатор: {context.user_data[FEATURES][Info.IDENTIFIER]}\n" \
           f"URL: {context.user_data[FEATURES][Info.URL]}\n\n"

    text2 = f"Аннотация на английском: {context.user_data[FEATURES][Info.DESCRIPTION]}\n\n" \
            f"Аннотация на русском: {context.user_data[FEATURES][Info.ABSTRACT]}\n\n" \
            f"Ключевые слова на английском: {context.user_data[FEATURES][Info.KEYWORDS]}\n" \
            f"Ключевые слова на русском: {context.user_data[FEATURES][Info.KEYWORDS_RU]}\n"

    text3 = f"Предметная область: {context.user_data[FEATURES][Info.SUBJECT]}\n" \
            f"Учебные дисциплины: {context.user_data[FEATURES][Info.MEDIATOR]}\n\n" \
            f"Кто добавил: {context.user_data[FEATURES][Info.ADDED_BY]}\n" \
            f"Рецензия: {context.user_data[FEATURES][Info.USER_COMMENT]}\n"

    await update.message.reply_text(
        text=text,
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        text=text2,
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        text=text3,
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text("Данные верны?",
                                    reply_markup=ReplyKeyboardMarkup([["Верно, сохранить"],
                                                                      ["Есть ошибка"]],
                                                                     one_time_keyboard=True))

    return Info.EDIT_FIELD


async def edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    if choice == "Верно, сохранить":
        await update.message.reply_text("Данные сохранены")
        context.user_data[START_OVER] = True
        await start(update, context)
        save_info(update, context)
        return END
    elif choice == "Есть ошибка":
        await update.message.reply_text("Выберите, какой тип данных нужно исправить",
                                        reply_markup=ReplyKeyboardMarkup(fields_buttons, one_time_keyboard=True))
        return Info.EDIT_FIELD_CHOSEN
    else:
        await update.message.reply_text("Некорректный тип")
        return Info.EDIT_FIELD


async def edit_field_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chosen_field = update.message.text
    if chosen_field in fields:
        context.user_data["chosen_field"] = chosen_field  # Сохраняем выбранное поле в контексте
    else:
        await update.message.reply_text("Такого типа данных нет. Выберите из списка",
                                        reply_markup=ReplyKeyboardMarkup(fields_buttons, one_time_keyboard=True))
        return Info.EDIT_FIELD_CHOSEN

    await update.message.reply_text("Отправьте новые данные или оставьте прежний вариант",
                                    reply_markup=ReplyKeyboardMarkup([["Оставить как есть"]], one_time_keyboard=True))
    return Info.EDIT_FIELD_VALUE


async def edit_field_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_value = update.message.text
    if new_value != "Оставить как есть":
        chosen_field = context.user_data.get("chosen_field")  # Получаем выбранное поле из контекста
        context.user_data[FEATURES][fields[chosen_field]] = new_value
        text = "Данные изменены"
    else:
        text = "Оставляю как есть"

    await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(fields_buttons))
    return await finish_adding_info(update, context)


def save_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    bibliographic_citation = context.user_data[FEATURES][Info.BIBLIOGRAPHIC_CITATION]
    title = context.user_data[FEATURES][Info.TITLE]
    creator = context.user_data[FEATURES][Info.CREATOR]
    genre = context.user_data[FEATURES][Info.GENRE]
    description = context.user_data[FEATURES][Info.DESCRIPTION]
    description_freq = lemmatize_eng(context.user_data[FEATURES][Info.DESCRIPTION])
    abstract = context.user_data[FEATURES][Info.ABSTRACT]
    abstract_freq = lemmatize_rus(context.user_data[FEATURES][Info.ABSTRACT])
    keywords = context.user_data[FEATURES][Info.KEYWORDS]
    keywords_ru = context.user_data[FEATURES][Info.KEYWORDS_RU]
    country_of_origin = context.user_data[FEATURES][Info.COUNTRY_OF_ORIGIN]
    date = context.user_data[FEATURES][Info.DATE]
    publisher = context.user_data[FEATURES][Info.PUBLISHER]
    identifier = context.user_data[FEATURES][Info.IDENTIFIER]
    url = context.user_data[FEATURES][Info.URL]
    subject = context.user_data[FEATURES][Info.SUBJECT]
    mediator = context.user_data[FEATURES][Info.MEDIATOR]
    added = datetime.date.today()
    chat_id = update.message.from_user["username"]
    added_by = context.user_data[FEATURES][Info.ADDED_BY]
    user_comment = context.user_data[FEATURES][Info.USER_COMMENT]
    status = "open"

    query = f"INSERT INTO texts (" \
            f"bibliographic_citation, title, creator, genre, description, description_freq, abstract, " \
            f"abstract_freq, keywords, keywords_ru, country_of_origin, date, publisher, identifier, url, " \
            f"subject, mediator, added, chat_id, added_by, user_comment, " \
            f"status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    values = (
        bibliographic_citation, title, creator, genre, description, description_freq, abstract, abstract_freq,
        keywords, keywords_ru, country_of_origin, date, publisher, identifier, url, subject, mediator, added, chat_id,
        added_by, user_comment, status)

    cursor.execute(query, values)
    conn.commit()
    return True




async def end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()

    text = "Вы завершили работу. Чтобы начать сначала, отправьте команду /start"
    await update.callback_query.edit_message_text(text=text)

    return END


async def start_extract(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print("EXTRACTION")
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "Тут тоже пусто 🐥"
    )
    context.user_data[START_OVER] = True
    await start(update, context)
    return END


def main() -> None:
    token = ''
    application = Application.builder().token(token).build()
    add_data_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(scenario_add, pattern="^" + str(SCENARIO_ADD) + "$"),
            CallbackQueryHandler(add_info.request_bibliographic_citation, pattern="^" + str(ADD_DATA) + "$"),
            CommandHandler("add_text", scenario_add)
        ],
        states={
            CONFIRMATION: [
                CallbackQueryHandler(add_info.request_bibliographic_citation, pattern="^" + str(ADD_DATA) + "$")
            ],
            Info.BIBLIOGRAPHIC_CITATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_info.bibliographic_citation),
                CallbackQueryHandler(add_info.bibliographic_citation, pattern="^" + str(SKIP) + "$")
            ],
            Info.TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_info.title),
                         CallbackQueryHandler(add_info.title, pattern="^" + str(SKIP) + "$")],
            Info.CONFIRM_NO_DUPLICATES: [CallbackQueryHandler(add_info.title, pattern="^" + str(SKIP) + "$")],
            Info.CREATOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_info.creator),
                           CallbackQueryHandler(add_info.creator, pattern="^" + str(SKIP) + "$")],
            Info.GENRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_info.genre)],
            Info.DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_info.description),
                               CallbackQueryHandler(add_info.description, pattern="^" + str(SKIP) + "$")],
            Info.ABSTRACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_info.abstract),
                            CallbackQueryHandler(add_info.abstract, pattern="^" + str(SKIP) + "$")],
            Info.KEYWORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_info.keywords),
                            CallbackQueryHandler(add_info.keywords, pattern="^" + str(SKIP) + "$")],
            Info.KEYWORDS_RU: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_info.keywords_ru),
                               CallbackQueryHandler(add_info.keywords_ru, pattern="^" + str(SKIP) + "$")],
            Info.COUNTRY_OF_ORIGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_info.country_of_origin),
                                     CallbackQueryHandler(add_info.country_of_origin, pattern="^" + str(SKIP) + "$")],
            Info.DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_info.date),
                        CallbackQueryHandler(add_info.date, pattern="^" + str(SKIP) + "$"),
                        CallbackQueryHandler(add_info.date, pattern="^" + str(YES) + "$")],
            Info.PUBLISHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_info.publisher),
                             CallbackQueryHandler(add_info.publisher, pattern="^" + str(SKIP) + "$"),
                             CallbackQueryHandler(add_info.publisher, pattern="^" + str(YES) + "$")],
            Info.IDENTIFIER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_info.identifier),
                              CallbackQueryHandler(add_info.identifier, pattern="^" + str(SKIP) + "$")],
            Info.URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_info.url),
                       CallbackQueryHandler(add_info.url, pattern="^" + str(SKIP) + "$")],
            Info.SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_info.subject)],
            Info.MEDIATOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_info.mediator),
                            CallbackQueryHandler(add_info.mediator, pattern="^" + str(SKIP) + "$")],
            Info.ADDED_BY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_info.added_by),
                            CallbackQueryHandler(add_info.added_by, pattern="^" + str(SKIP) + "$")],
            Info.USER_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, answer_user_comment),
                                CallbackQueryHandler(finish_adding_info, pattern="^" + str(SKIP) + "$")],
            Info.EDIT_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_field)],
            Info.EDIT_FIELD_CHOSEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_field_chosen)],
            Info.EDIT_FIELD_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_field_value)],
        },
        fallbacks=[
            CallbackQueryHandler(end_scenario_add, pattern="^" + str(END) + "$"),
            CommandHandler("stop", stop_nested),
        ],
        map_to_parent={
            # Return to top level menu
            END: CHOOSING_SCENARIO,
            # End conversation altogether
            STOPPING: STOPPING,
        },
    )

    search_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(scenario_search, pattern="^" + str(SCENARIO_PACKET) + "$"),
                      CommandHandler("search", scenario_search)],
        states={
            # SHOWING: [CallbackQueryHandler(start, pattern="^" + str(END) + "$")],
            Search.START_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_search_by)],
            Search.BY_AUTHOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_by_author)],
            Search.BY_ARTICLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_by_article)],
            Search.BY_KEYWORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_by_keywords)],
            Search.IN_ANNOTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_in_annots)],
            Search.BY_UPLOADER: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_by_uploader)],
            Search.NORES: [MessageHandler(filters.TEXT & ~filters.COMMAND, no_results)],
            Search.REVIEW_BRANCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, review_handler)],
            Search.REVIEW_HANDLER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_review)],
            Search.WRITE_REVIEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, users_name_handler)],
            Search.PAGINATOR: [CallbackQueryHandler(paginator_results, pattern='^character#'),
                               CallbackQueryHandler(handle_chosen_text, pattern='^chosen#[\d]+$')],
        },
        fallbacks=[
            CallbackQueryHandler(end_scenario_add_packet, pattern="^" + str(END) + "$"),
            CommandHandler("stop", stop),
            CommandHandler("search", scenario_search)
        ],
        map_to_parent={
            # Return to top level menu
            END: CHOOSING_SCENARIO,
            # End conversation altogether
            STOPPING: END,
        },
    )

    selection_handlers = [
        add_data_conv,
        search_conv,
        CallbackQueryHandler(end, pattern="^" + str(END) + "$"),
    ]

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_SCENARIO: selection_handlers,
            STOPPING: [CommandHandler("start", start)],
        },
        fallbacks=[CommandHandler("stop", stop)],
    )

    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
