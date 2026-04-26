import os, telebot, io, requests, time
from groq import Groq

BOT_TOKEN = os.environ['TELEGRAM_TOKEN']
HF_TOKEN = os.environ['HF_TOKEN']
GROQ_KEY = os.environ['GROQ_KEY']

bot = telebot.TeleBot(BOT_TOKEN)
client = Groq(api_key=GROQ_KEY)

def query_groq_text(prompt):
    chat = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.1-8b-instant",
        temperature=0.7
    )
    return chat.choices[0].message.content

def query_hf_img(prompt):
    API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    response = requests.post(API_URL, headers=headers, json={"inputs": prompt}, timeout=60)
    return response.content

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Sono Will. Testo veloce con Groq. Immagini con /img + descrizione")

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

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    try:
        reply = query_groq_text(message.text)
        bot.reply_to(message, reply)
    except:
        bot.reply_to(message, "Groq ha avuto un problema. Riprova.")

if __name__ == "__main__":
    print("Will bot avviato...")
    while True:
        try:
            bot.polling(none_stop=True, interval=1)
        except:
            time.sleep(5)
