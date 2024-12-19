import requests
from bs4 import BeautifulSoup
from dateparser import parse as parse_date
import psycopg2


def get_db_connection():
    return psycopg2.connect(
        host="postgres_database",  
        dbname="news",             
        user="root",               
        password="root"            
    )


def save_news_to_db(news):
    connection = get_db_connection()
    cursor = connection.cursor()

    for item in news:
        print(f"Сохраняем новость: {item['title']}, Категория: {item['category']}")
        
        
        cursor.execute("""
            INSERT INTO news (title, date, link, category)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (link) DO UPDATE
            SET category = CASE 
                WHEN news.category LIKE %s THEN news.category
                ELSE news.category || ', ' || EXCLUDED.category
            END
        """, (item['title'], item['date'], item['link'], item['category'], '%' + item['category'] + '%'))

    connection.commit()
    cursor.close()
    connection.close()
    print(f"Новость сохранена в базу данных.")




def process_and_save_news_item(item, section):
    title_tag = item.find('a')
    date_tag = item.find('time')

    if title_tag and date_tag:
        title = title_tag.text.strip()
        date_text = date_tag.text.strip()
        date = parse_date(date_text, languages=['ru'])

        if not date:
            print(f"Ошибка обработки даты: {date_text}")
            return

        link = f"https://polit74.ru{title_tag['href']}"
        news_item = {
            'title': title,
            'date': date,
            'link': link,
            'category': section
        }
        
        
        save_news_to_db([news_item])


def process_and_save_preview_item(item, section):
    title_tag = item.find('a')
    date_tag = item.find('time')

    if title_tag and date_tag:
        title = title_tag.text.strip()
        date_text = date_tag.text.strip()
        date = parse_date(date_text, languages=['ru'])

        if not date:
            print(f"Ошибка обработки даты: {date_text}")
            return

        link = f"https://polit74.ru{title_tag['href']}"
        news_item = {
            'title': title,
            'date': date,
            'link': link,
            'category': section
        }
        
        
        save_news_to_db([news_item])

def parse_and_save_polit74(section, start_page, end_page):
    base_url = f'https://polit74.ru/{section}/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }

    for page_num in range(start_page, end_page + 1):
        url = f'{base_url}?PAGEN_1={page_num}'
        print(f'Парсим страницу {page_num} раздела {section}...')

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Ошибка загрузки страницы: {url}")
            break

        soup = BeautifulSoup(response.content, 'html.parser')

        
        news_items = soup.find_all('div', class_='block-list__item')
        for item in news_items:
            process_and_save_news_item(item, section)

        preview_items = soup.find_all('div', class_='preview__title')
        for item in preview_items:
            process_and_save_preview_item(item, section)

def main():
    sections = ['novosti', 'politics', 'economics', 'society', 'incident', 'culture-i-sport']
    pages_per_iteration = 3
    max_iterations = 100

    for iteration in range(max_iterations):
        print(f"\n=== Итерация {iteration + 1} ===")
        start_page = iteration * pages_per_iteration + 1
        end_page = start_page + pages_per_iteration - 1

        for section in sections:
            parse_and_save_polit74(section, start_page, end_page)

if __name__ == "__main__":
    main()
