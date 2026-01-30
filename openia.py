import os
from openai import OpenAI
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def preguntar_gpt(texto):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un asistente que ayuda a organizar tareas."},
            {"role": "user", "content": texto}
        ]
    )

    return response.choices[0].message.content
