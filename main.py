import os
import time

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


def task_starter():
    """Главная функция, которая запускает весь процесс:
    1) подключается к HubSpot API находит нужные сделки и лиды
    2) генерирует и отправляет письмо
    3) изменяет статус сделки + properties лида"""

    contacts_url = 'https://api.hubapi.com/crm/v3/objects/contacts?properties=prompt,email,is_prompt_sent'
    deals_url_update = "https://api.hubapi.com/crm/v4/objects/deals?associations=contact&contactId&properties=prompt,email,is_prompt_sent"
    headers = {
        "Authorization": f"Bearer {os.getenv('HUBSPOT_PRIVATE_APPS_API_KEY')}"
    }
    response = requests.get(deals_url_update, headers=headers)
    response_contacts = requests.get(contacts_url, headers=headers)

    if response.status_code == 200:
        data = response.json()

        for deal in data["results"]:  # находим созданную сделку
            if "associations" in deal:
                contact_id = deal['associations']['contacts']['results'][0]['id']
                deal_id = deal["id"]

                contact_data = response_contacts.json()

                for contact in contact_data["results"]:  # находим привязаный лид к сделке
                    if contact["id"] == contact_id:
                        if contact["properties"]["is_prompt_sent"] == "no":
                            lead_contact = contact["id"]
                            client_email = contact["properties"]["email"]
                            client_prompt = contact["properties"]["prompt"]
                            print("запускаем функцию отправки письма")
                            # отправляем письмо на почту
                            top_bikes_email_sender(
                                client_email, chat_gpt_request(client_prompt)
                            )
                            print("закрываем функцию отправки письма")
                            update_url = f'https://api.hubapi.com/crm/v3/objects/contacts/{lead_contact}'  # обновляем в контакте is_prompt_sent на "yes"
                            update_payload_contact = {
                                "properties": {
                                    "is_prompt_sent": "yes"
                                }
                            }
                            response = requests.patch(update_url, json=update_payload_contact, headers=headers)

                            if response.status_code == 200:
                                print(f"Значение 'is_prompt_sent' обновлено для контакта {lead_contact}.")
                            else:
                                print(f"Произошла ошибка при обновлении значения 'is_prompt_sent' для контакта {lead_contact}:")
                                print(response.status_code, response.text)

                            update_url_deal = f'https://api.hubapi.com/crm/v3/objects/deals/{deal_id}'  # обновляем в сделке статус на "Presentation Scheduled"
                            update_payload_deal = {
                                "properties": {
                                    "dealstage": "presentationscheduled"
                                }
                            }
                            response = requests.patch(update_url_deal, json=update_payload_deal, headers=headers)

                            if response.status_code == 200:
                                # else оставил для лчушей читаемости кода
                                print("Статус сделки успешно обновлен")
                            else:
                                print("Произошла ошибка при обновлении статуса сделки:",
                                      response.text)

if __name__ == "__main__":
    while True:
        print("стартуем", datetime.now())
        task_starter()
        time.sleep(30)
