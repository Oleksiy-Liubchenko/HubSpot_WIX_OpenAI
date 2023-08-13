import os
import openai as openai
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

DEALS_URL = "https://api.hubapi.com/crm/v3/objects/deals"


def chat_gpt_request(your_question: str) -> str:
    """Функция должна получить ваш
  prompt и выдать ответ Chat GPT"""

    openai.api_key = os.getenv("OPEN_AI_API_KEY")
    model_engine = "text-davinci-003"

    completion = openai.Completion.create(
        engine=model_engine,
        prompt=your_question,
        max_tokens=2048,
        temperature=0.5,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )

    return completion.choices[0].text


def top_bikes_email_sender(email: str, text: str) -> None:
    """Функция отправляет емейл на почту
    с заданым текстом(в нашем случае open ai prompt)"""

    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")

    sender_email = smtp_username
    receiver_email = email
    subject = "ТОП 3 шоссейных велосипеда для тебя"
    message_text = text

    # Создание объекта письма
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject

    # Добавление текста письма
    msg.attach(MIMEText(message_text, "plain"))

    try:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(smtp_username, smtp_password)
        server.sendmail(
            sender_email,
            receiver_email,
            msg.as_string()
        )
        server.quit()
        print("Письмо успешно отправлено")
    except Exception as e:
        print("Произошла ошибка при отправке письма:", str(e))


def string_cleaner(prompt: str) -> str:
    """Функция сделана для того, чтобы убрать лишние
     ключевые слова из запроса, который приходит в
     контакт из парамметров заявки
     и оставить чистый prompt для Chat GPT"""

    cleaned_prompt = prompt[8:]
    email_tag = "[почта -"
    if cleaned_prompt.endswith("]"):
        start_index = cleaned_prompt.rfind(email_tag)
        if start_index != -1:
            cleaned_prompt = cleaned_prompt[:start_index]
    return cleaned_prompt


def email_fetching_from_prompt(prompt: str) -> str:
    """Функция извлекает из данных заявки почту клиента,
    на которую нужно отправить email"""

    email_start = "[почта - "
    email_end = "]"
    email_index_start = prompt.rfind(email_start)
    email_index_end = prompt.rfind(email_end)
    if email_index_start != -1 and email_index_end != -1:
        email = prompt[
                email_index_start +
                len(email_start):email_index_end
                ]
        return email


def task_starter() -> None:
    """Главная функция, которая запускает весь процесс:
    1) подключается к HubSpot API находит нужные сделки
    2) генерирует и отправляет письмо
    3) изменяет статус сделки"""

    headers = {
        "Authorization": f"Bearer {os.getenv('HUBSPOT_PRIVATE_APPS_API_KEY')}"
    }
    response = requests.get(DEALS_URL, headers=headers)

    if response.status_code == 200:

        data = response.json()
        for deal in data["results"]:

            if deal["properties"]["dealstage"] == "appointmentscheduled" and \
                    deal["properties"]["dealname"][0:8] == "[prompt]":

                dirty_prompt = deal["properties"]["dealname"]
                client_email = email_fetching_from_prompt(dirty_prompt)
                clean_prompt = string_cleaner(dirty_prompt)

                print("Подготовка к отправке письма")
                top_bikes_email_sender(
                    client_email, chat_gpt_request(clean_prompt)
                )

                data = {
                    "properties": {
                        "dealstage": "presentationscheduled"
                    }
                }
                update_url = f"{DEALS_URL}/{deal['id']}"
                response = requests.patch(update_url, json=data, headers=headers)

                if response.status_code == 200:
                    # else оставил для лчушей читаемости кода
                    print("Статус сделки успешно обновлен")
                else:
                    print("Произошла ошибка при обновлении статуса сделки:",
                          response.text)
    else:
        print('Ошибка при выполнении запроса:', response.content)


task_starter()
