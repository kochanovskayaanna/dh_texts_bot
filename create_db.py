import sqlite3

# Подключение к базе данных и создание курсора
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Создание таблицы "users"
cursor.execute('''CREATE TABLE texts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        bibliographic_citation TEXT,
                        title TEXT,
                        creator TEXT,
                        genre TEXT,
                        description TEXT,
                        abstract TEXT,
                        keywords TEXT,
                        keywords_ru TEXT,
                        country_of_origin TEXT,
                        date TEXT,
                        publisher TEXT,
                        identifier TEXT,
                        subject TEXT,
                        mediator TEXT,
                        added TEXT,
                        chat_id INTEGER, // must be TEXT
                        added_by TEXT,
                        user_comment TEXT,
                        status TEXT
                  )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text_id INTEGER,
        review TEXT,
        chat_id TEXT,
        added_by TEXT,
        FOREIGN KEY (text_id) REFERENCES texts (id)
    )
''')

conn.commit()
conn.close()