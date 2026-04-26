import telebot
import requests
import os
import io
from flask import Flask
import threading

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROQ_KEY = os.environ.get('GROQ_KEY')
HF_TOKEN = os.environ.get('HF_TOKEN')

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Will online - Groq + HF"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

def query_groq_testo(prompt):
    headers = {"Authorization": f"Bearer {GROQ_KEY}"}
    data = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "Sei Will, assistente sarcastico, intelligente e diretto. Rispondi breve."},
            {"role": "user", "content": prompt}
        ]
    }
    r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data, timeout=30)
    return r.json()['choices'][0]['message']['content']

def query_hf_img(prompt):
    API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    r = requests.post(API_URL, headers=headers, json={"inputs": prompt}, timeout=60)
    return r.content

@bot.message_handler(commands=['img'])
def handle_image(message):
    prompt = message.text.replace('/img', '').strip()
    if not prompt:
        bot.reply_to(message, "Es: /img un gatto samurai a Roma")
        return
    bot.reply_to(message, "Genero con HF... 20-30 sec ⏳")
    try:
        img = query_hf_img(prompt)
        if b'error' in img[:100]:
            bot.reply_to(message, "HF sta caricando. Riprova tra 30 sec.")
            return
        bot.send_photo(message.chat.id, io.BytesIO(img))
    except:
        bot.reply_to(message, "Quota HF finita per oggi o errore.")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Sono Will. Testo veloce con Groq.\nImmagini con /img + descrizione")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    try:
        reply = query_groq_testo(message.text)
        bot.reply_to(message, reply)
    except:
        bot.reply_to(message, "Errore Groq. Key giusta?")

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.polling()
