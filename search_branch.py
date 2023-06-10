from typing import List

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
from telegram_bot_pagination import InlineKeyboardPaginator

from states import *
from db import *
from difflib import SequenceMatcher


async def scenario_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = "Как будем искать данные?"

    keyboard = [
        ["По автору"],
        ["В названии"],
        ["В ключевых словах"],
        # ["В аннотациях"],
        ["По имени загрузившего"]
    ]

    if update.callback_query is None:
        message = update.message
    else:
        message = update.callback_query.message
    await message.reply_text(text=text, reply_markup=ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True
    ))

    return Search.START_SEARCH


async def ask_search_by(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "По автору":
        reply = "Введите автора"
        search_by = Search.BY_AUTHOR
    elif text == "В названии":
        reply = "Что вы ищете?"
        search_by = Search.BY_ARTICLE
    elif text == "В ключевых словах":
        reply = "Введите ключевые слова"
        search_by = Search.BY_KEYWORDS
    elif text == "В аннотациях":
        reply = "Что вы ищете?"
        context.user_data[Search.SEARCH_COLUMNS] = ["title", "creator", "description", "abstract"]
        search_by = Search.IN_ANNOTS
    elif text == "По имени загрузившего":
        reply = "Кого вы ищете?"
        search_by = Search.BY_UPLOADER
    else:
        reply = "Выберите корректный тип поиска!"
        search_by = Search.START_SEARCH

    await update.message.reply_text(
        text=reply,
        reply_markup=ReplyKeyboardRemove() if search_by != Search.START_SEARCH else ReplyKeyboardMarkup([
            ["По автору"],
            ["В названии"],
            ["В ключевых словах"],
            # ["В аннотациях"],
            ["По имени загрузившего"]
        ], one_time_keyboard=True)
    )
    return search_by


def get_db_rows(columns, target_ids):
    columns_str = ', '.join(columns)
    cursor.execute(f'SELECT id, {columns_str} FROM texts')
    rows = cursor.fetchall()
    targets = [''.join([row[idx + 1] if row[idx + 1] is not None else '' for idx in target_ids]) for row in rows]
    return rows, targets


def get_reviews(text_id):
    cursor.execute(f"SELECT * FROM reviews WHERE text_id={text_id}")
    rows = cursor.fetchall()
    return rows


async def search_text(update: Update, context: ContextTypes.DEFAULT_TYPE, search_columns: List[str],
                      target_ids, likeness_func, likeness_coef, result_format: str) -> int:
    query = update.message.text
    context.user_data[Search.SEARCH_COLUMNS] = search_columns
    rows, target_rows = get_db_rows(search_columns, target_ids)
    # есть фиктивный аргумент coef  в функции check_entry
    maximum_likeness = likeness_func(query, target_rows, likeness_coef)
    if len(maximum_likeness) == 0:
        keyboard = ReplyKeyboardMarkup([["Назад к поиску"], ["Добавить текст в базу"]], one_time_keyboard=True)
        await update.message.reply_text(
            text="Ничего не нашлось",
            reply_markup=keyboard,
        )
        return Search.NORES
    elif len(maximum_likeness) == 1:
        await update.message.reply_text(text="Нашелся один текст")

        coef, text_ind = maximum_likeness[0]
        row_str = result_format.format(1, *rows[text_ind][1:])
        row_str = row_str[row_str.find(' ') + 1:]
        await update.message.reply_text(
            text=row_str,
            parse_mode="markdown"
        )

        return await one_result(update, context, rows[text_ind])
    else:
        text = f"Найдено {pluralize_matches(len(maximum_likeness))}\n\n"
        if len(maximum_likeness) <= 5:
            text += "Чтобы открыть сведения о тексте, нажмите на кнопку с номером текста"
        else:
            text += "Чтобы открыть сведения о тексте, нажмите на кнопку с номером текста. " \
                    "Между страницами с результатами поиска можно переключаться по нижнему ряду кнопок"
        await update.message.reply_text(
            text=text,
            parse_mode="markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        pages_list = []
        text_ids = []
        matched_rows = []
        for i, res in enumerate(maximum_likeness):
            coef, text_ind = res
            text_id, *row = rows[text_ind]
            row_str = result_format.format(i + 1, *row)

            matched_rows.append(rows[text_ind])
            pages_list.append(row_str)
            text_ids.append(text_id)

        page_size = 5
        pages = ['\n'.join(pages_list[i:i + page_size]) for i in range(0, len(pages_list), page_size)]

        paginator = InlineKeyboardPaginator(
            len(pages),
            data_pattern='character#{page}'
        )
        buttons = [InlineKeyboardButton(f'{i+1}', callback_data='chosen#{}'.format(i+1)) for i in range(page_size)
                   if i + 1 <= len(pages_list)]
        paginator.add_before(*buttons)

        await update.message.reply_text(
            text=pages[0],
            reply_markup=paginator.markup,
            parse_mode='markdown'
        )
        context.user_data["pages"] = pages_list
        context.user_data["text_ids"] = text_ids
        context.user_data["page_size"] = page_size
        context.user_data["rows"] = rows
        context.user_data["matched_rows"] = matched_rows
        return Search.PAGINATOR


async def paginator_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    pages_list = context.user_data["pages"]
    page_size = context.user_data["page_size"]
    pages = ['\n'.join(pages_list[i:i + page_size]) for i in range(0, len(pages_list), page_size)]
    page = int(query.data.split('#')[1])
    paginator = InlineKeyboardPaginator(
        len(pages),
        current_page=page,
        data_pattern='character#{page}'
    )

    buttons = [InlineKeyboardButton(f'{((page - 1) * page_size) + (i + 1)}', callback_data='chosen#{}'.format(i + 1)) for i in
               range(page_size) if ((page - 1) * page_size) + (i + 1) <= len(pages_list)]
    paginator.add_before(*buttons)
    await query.edit_message_text(
        text=pages[page - 1],
        reply_markup=paginator.markup,
        parse_mode='markdown'
    )


async def handle_chosen_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    chosen = int(query.data.split('#')[1])
    matched_rows = context.user_data["matched_rows"]
    row = matched_rows[chosen-1]
    print(f"{chosen=}")
    print(row)
    return await one_result(update, context, row)


async def one_result(update: Update, context: ContextTypes.DEFAULT_TYPE, row) -> int:
    text_id = row[0]
    reviews = get_reviews(text_id)
    context.user_data[Search.REVIEWS_CONTAINER] = reviews
    context.user_data["text_id"] = text_id

    cursor.execute(f'SELECT * FROM texts WHERE id={text_id}')
    names = list(map(lambda x: x[0], cursor.description))
    row = cursor.fetchall()[0]
    assert len(names) == len(row)

    existing_values = {}
    for name, value in zip(names, row):
        if name in fields_repr_dict and value not in [None, ""]:
            existing_values[name] = value

    if len(reviews) == 0:
        text = "Других рецензий на этот текст пока нет"
        buttons = [["Написать рецензию"], ["Назад к поиску"]]
    else:
        text = f"На текст {pluralize_matches_reviews(len(reviews))}"
        buttons = [["Читать рецензии"], ["Написать рецензию"], ["Назад к поиску"]]

    if update.message is None:
        message = update.callback_query.message
    else:
        message = update.message

    text_info = create_text_info(existing_values)
    for text_block in text_info:
        await message.reply_text(
            text=text_block,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="markdown"
        )
    await message.reply_text(text, reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True))

    return Search.REVIEW_BRANCH


def create_text_info(fields_dict):
    text = "*Сведения о тексте*\n\n" + \
           (f"Библиографическая ссылка: {fields_dict['bibliographic_citation']}\n\n" if 'bibliographic_citation' in fields_dict else "") + \
           (f"Название: {fields_dict['title']}\n" if 'title' in fields_dict else "") + \
           (f"Автор: {fields_dict['creator']}\n" if 'creator' in fields_dict else "") + \
           (f"Жанр: {fields_dict['genre']}\n\n" if 'genre' in fields_dict else "") + \
           (f"Страна публикации: {fields_dict['country_of_origin']}\n" if 'country_of_origin' in fields_dict else "") + \
           (f"Год: {fields_dict['date']}\n" if 'date' in fields_dict else "") + \
           (f"Издатель: {fields_dict['publisher']}\n\n" if 'publisher' in fields_dict else "") + \
           (f"Идентификатор: {fields_dict['identifier']}\n" if 'identifier' in fields_dict else "") + \
           (f"URL: [Текст доступен по ссылке]({fields_dict['url']})\n\n" if 'url' in fields_dict else "")

    text2 = (f"Аннотация на английском: {fields_dict['description']}\n\n" if 'description' in fields_dict else "") + \
            (f"Аннотация на русском: {fields_dict['abstract']}\n\n" if 'abstract' in fields_dict else "") + \
            (f"Ключевые слова на английском: {fields_dict['keywords']}\n" if 'keywords' in fields_dict else "") + \
            (f"Ключевые слова на русском: {fields_dict['keywords_ru']}\n" if 'keywords_ru' in fields_dict else "")

    text3 = (f"Предметная область: {fields_dict['subject']}\n\n" if 'subject' in fields_dict else "") + \
            (f"Учебные дисциплины: {fields_dict['mediator']}\n\n" if 'mediator' in fields_dict else "") + \
            (f"Кто добавил: {fields_dict['added_by']}\n\n" if 'added_by' in fields_dict else "") + \
            (f"Рецензия загрузившего: {fields_dict['user_comment']}\n" if 'user_comment' in fields_dict else "")

    return text, text2, text3


async def review_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message.text
    if message == "Написать рецензию":
        text = "Напишите ваше имя и короткий титр. Они будут отображаться вместе с комментарием о тексте. \n\n" \
               "Пример: Аня Кочановская, создательница бота"
        keyboard = ReplyKeyboardMarkup([["Не хочу указывать имя"], ["Назад к поиску"]], one_time_keyboard=True)

        await update.message.reply_text(
            text=text,
            reply_markup=keyboard
        )
        return Search.WRITE_REVIEW

    elif message == "Назад к поиску":
        return await scenario_search(update, context)
    elif message == "Читать рецензии":
        buttons = [["Написать рецензию"], ["Назад к поиску"]]
        for review in context.user_data[Search.REVIEWS_CONTAINER]:
            text_of_review = review[2]
            await update.message.reply_text(
                text=text_of_review,
                reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True)
            )
        return Search.REVIEW_BRANCH
    else:
        return Search.REVIEW_BRANCH


async def users_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message.text
    if message == "Назад к поиску":
        return await scenario_search(update, context)
    if message == "Не хочу указывать имя":
        context.user_data["added_by"] = "Anonim"
    else:
        context.user_data["added_by"] = message
    context.user_data["chat_id"] = update.message.from_user["username"]
    return await ask_review(update, context)


async def ask_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = "Напишите рецензию на текст\n" \
           "Почему вы предлагаете этот текст? Вот несколько вопросов, на которые вы можете ответить:\n\n" \
           "1) В какой ситуации и кому полезен этот текст? \n" \
           "2) Каков контекст текста (дисциплина, метод, проект)? " \
           "Что важно понимать про контекст, чтобы прочитать текст с умом? \n" \
           "3) Почему вы читали этот текст?\n" \
           "4) В чём состоят недостатки текста и работы, которая за ним стоит?\n" \
           "5) На какие тексты стоит обратить внимание читателю, когда он прочитает этот текст? \n\n" \
           "Отправьте текст боту одним сообщением. Рецензия и имя будут видны другим пользователям"
    keyboard = ReplyKeyboardMarkup([["Не буду добавлять рецензию"]], one_time_keyboard=True)
    await update.message.reply_text(
        text=text,
        reply_markup=keyboard
    )
    return Search.REVIEW_HANDLER


async def search_by_author(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[Search.SEARCH_BY] = search_by_author
    search_columns = ["title", "creator", "date"]
    target_ids = [1]
    likeness_func = get_maximum_likeness
    likeness_coef = 0.7
    result_format = "{}) {} {} ({})\n"
    return await search_text(update, context, search_columns, target_ids, likeness_func, likeness_coef, result_format)


async def search_by_article(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[Search.SEARCH_BY] = search_by_article
    search_columns = ["title", "creator", "date"]
    target_ids = [0]
    likeness_func = get_maximum_likeness
    likeness_coef = 0.5
    result_format = "{}) {} {} ({})\n"
    return await search_text(update, context, search_columns, target_ids, likeness_func, likeness_coef, result_format)


async def search_by_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[Search.SEARCH_BY] = search_by_keywords
    search_columns = ["title", "creator", "keywords", "keywords_ru", "date"]
    target_ids = [2, 3]
    likeness_func = check_entry
    likeness_coef = 0
    result_format = "{0}) {2} {1} ({5}) \n\n{3} {4}\n\n"
    return await search_text(update, context, search_columns, target_ids, likeness_func, likeness_coef, result_format)


async def search_by_uploader(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[Search.SEARCH_BY] = search_by_uploader
    search_columns = ["title", "creator", "added_by", "date"]
    target_ids = [2]
    likeness_func = get_maximum_likeness
    likeness_coef = 0.5
    result_format = "{0}) {2} {1} ({4})\n{3}\n\n"
    return await search_text(update, context, search_columns, target_ids, likeness_func, likeness_coef, result_format)


# вот это надо исправлять
async def search_in_annots(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[Search.SEARCH_BY] = search_in_annots
    query = update.message.text
    columns = context.user_data[Search.SEARCH_COLUMNS]
    columns_str = ', '.join(columns)
    cursor.execute(f'SELECT {columns_str} FROM texts')
    rows = cursor.fetchall()
    result = [row[2] + row[3] for row in rows]
    maximum_likeness = []
    for i, result_seq in enumerate(result):
        if query in result_seq:
            maximum_likeness.append(i)

    text = f"Найдено {pluralize_matches(len(maximum_likeness))}\n\n"
    for i, res in enumerate(maximum_likeness):
        row_str = "; ".join(rows[res])
        text += f"{i + 1}: {row_str}\n"

    await update.message.reply_text(
        text=text,
        reply_markup=ReplyKeyboardRemove()
    )
    return END


def get_maximum_likeness(user_input, db, threshold):
    user_input = user_input.lower()
    db = [s.lower() for s in db]

    matches = []
    for i, s in enumerate(db):
        matcher = SequenceMatcher(None, user_input, s)
        lcs_length = matcher.find_longest_match(0, len(user_input), 0, len(s)).size
        metric = lcs_length / len(user_input)
        if metric >= threshold:
            matches.append((metric, i))
    matches.sort(key=lambda x: x[0], reverse=True)
    return matches


def pluralize_matches(count):
    if count % 10 == 1 and count % 100 != 11:
        return f"{count} совпадение"
    elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
        return f"{count} совпадения"
    else:
        return f"{count} совпадений"


def pluralize_matches_reviews(count):
    if count % 10 == 1 and count % 100 != 11:
        return f"написана {count} рецензия"
    elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
        return f"написано {count} рецензии"
    else:
        return f"написано {count} рецензий"


def check_entry(user_input, db, threshold):
    entries = []
    for i, keyword_seq in enumerate(db):
        if user_input in keyword_seq:
            entries.append((1.0, i))
    return entries
