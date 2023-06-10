import re
import pymorphy2
import nltk
import json
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from nltk import FreqDist
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')


def preprocess_string(string):

    # убирает нумерацию, если она была
    no_forward_numeration = r'^\d+\.?\s+'
    string = re.sub(no_forward_numeration, '', string)

    # убирает повтор в начале типа Орлова 2016 — Орлова Г. А. Собирая проект...
    # academic_double = r'.*\d{4}\s—'
    # string = re.sub(academic_double, "", string)
    academic_double = r'.*\d{4}\s(—|―)\s'
    string = re.sub(academic_double, "", string)

    # устраняем разрывы в словах типа «историче- ская»
    string = re.sub(r'-\s', '', string)
    string = re.sub(r'www.\s', 'www.', string)
    string = re.sub(r'://\s', '://', string)
    string = re.sub(r'\.\s[-—–]', '.', string)

    return string


def is_cyrillic_char(char):
    # Возвращаем True, если символ находится в диапазоне кириллических символов Unicode
    return 'а' <= char <= 'я' or 'А' <= char <= 'Я'


def publication_authors(string):

    if is_cyrillic_char(string[0]) == True:
        names = re.findall(r'([А-Я][а-я]+)\s([А-Я]\.)\s?([А-Я]\.)?', string)
    else:
        names = re.findall(r'([A-Z][a-z]+)\s([A-Z]\.)\s?([A-Z]\.)?', string)

    # добавляем точки после инициалов, если их нет
    authors = '; '.join([
        ' '.join([
            name[0],  # Фамилия
            name[1] + '.' if len(name[1]) == 1 else name[1],  # Первый инициал, с точкой если ее нет
            name[2] + '.' if name[2] and len(name[2]) == 1 else name[2]  # Второй инициал, с точкой если ее нет
        ]) for name in names
    ])
    # print(authors)
    return authors


def publication_name(string, authors):
    if is_cyrillic_char(string[0]):
        # ищем за инициалами и до слэша
        match = re.search(r"(?:(?<=[А-Я]\.)|(?<=[А-Я]\s[А-Я])|(?<=[а-я]\s[А-Я]))([^.]+?)(?:\/)", string)

        if match:
            text_title = match.group(1).strip()
            return text_title

        else:
            # print('тута')
            if '/' in string:
                match = re.search(r"^[^/]+", string)
                if match:
                    text_title = match.group(0).strip()
                    return text_title
            else:
                r = '(?:(?<=[А-Я]\.\s[А-Я]\.)|(?<=[А-Я]\s[А-Я]))([.*]+?)(?=\s*[А-Я]\.[\sА-Я]|\.?\s+[А-Я][\w]*:)'

                match = re.search(r, string)
                if match:
                    text_title = match.group(1).strip()
                    return text_title
                else:
                    text_title = ''
                    return text_title

    else:
        if authors:
            delete_author = re.findall(r'([A-Z][a-z]+)\s([A-Z]\.)\s?([A-Z]\.)?', string)
            last = " ".join(delete_author[-1])
            merging_authors = str()
            for tuple in delete_author[0:-1]:
                one_entity = " ".join(tuple)
                merging_authors = merging_authors + one_entity.strip() + ', '

            merging_authors = merging_authors + last
            string = string.replace(merging_authors, '')

        match = re.search(r'^[^.?!\[\/]+', string)
        if match is not None:
            text_title = match.group(0).strip()
        else:
            text_title = ""

        if match:
            return text_title
        else:
            text_title = ""
            return text_title


def publication_publisher(string):

    # ищем издателя между слэшем и годом публикации
    match = re.search(r'(?<=/\s).*?(?=[.,]\s\d{4})', string)

    if match:
        first_match = match.group(0)

        # проверяем, есть ли сокращенный город и двоеточие
        # если есть, они требуют доп. обработки
        if ':' not in first_match:
            publisher = match.group(0).strip()
            return publisher
        else:
            try:
                second_match = re.search(r"[A-ZА-Я][\w]*\.:\s*.+", first_match)
                publisher = second_match.group(0).strip()
                return publisher
            except:
                publisher = ''
                return publisher

    # если слэша не было:
    else:
        match = re.search(r"(?:[А-Яа-я]{,15}|[A-Za-z]+:)[^:]{,50}[.,]\s+\d{4}", string)

        if match:
            match = match.group(0)
            publisher = match[0:-6].strip()
            return publisher
        else:
            publisher = ''
            return publisher



# функция достает год публикации
def publication_year(string):

    year = ''.join(re.findall(r'[12]\d{3}\.', string)).rstrip('.')
    return year


# функция достает URL
def publication_url(string):

    url = ''.join(re.findall(r'URL:\s*(\S+)\s*[\. ]', string))

    if url:
        return url
    else:
        url = None
        return url

#
# text = 'Эппле 2017 ― Эппле Н. Внешняя политика памяти // InLiberty. 2017. 31 марта. URL: http://www.inliberty.ru/blog/2546-Vneshnyaya-politika-pamyati.'


def get_text_info(text: str):
    text = preprocess_string(text)
    authors = publication_authors(text)
    return {
        "bibliographicCitation": text,
        "title": publication_name(text, authors),
        "authors": authors,
        "year": publication_year(text),
        "url": publication_url(text),
        "publisher": publication_publisher(text)
    }


def lemmatize_rus(text):
    stopwords_rus = set(stopwords.words('russian'))

    morph = pymorphy2.MorphAnalyzer()
    tokens = nltk.word_tokenize(text.lower(), language='russian')

    lemmas = []
    for token in tokens:
        if token not in stopwords_rus and token.isalnum():
            lemmas.append(morph.parse(token)[0].normal_form)

    freq_dist = dict(FreqDist(lemmas))
    freq_dist = json.dumps(freq_dist)
    return freq_dist


def lemmatize_eng(text):
    if text is not None:
        text = text.lower()
        words = word_tokenize(text)
        words = [word for word in words if word not in stopwords.words('english')]
        words = [word for word in words if word.isalnum()]
        lemmatizer = WordNetLemmatizer()

        lemmas = [lemmatizer.lemmatize(word) for word in words]

        freq_dist = dict(FreqDist(lemmas))
        freq_dist = json.dumps(freq_dist)
        return freq_dist
    else:
        return None

