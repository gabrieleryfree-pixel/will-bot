import os
import telegram
import io
import requests
import time
from groq import Groq
import json

BOT_TOKEN = os.environ['TELEGRAM_TOKEN']
HF_TOKEN = os.environ['HF_TOKEN']
GROQ_KEY = os.environ['GROQ_API_KEY']

MEMORY_FILE = 'chat_memory.json'
bot = telegram.Bot(token=BOT_TOKEN)
client = Groq(api_key=GROQ_KEY)

def load_memory():
    try:
        with open(MEMORY_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_memory(memory):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f)

async def handle_start(update):
    await update.message.reply_text("Ciao! Sono Will 🤖\nDi cosa hai bisogno?")

async def handle_img(update, context):
    prompt = ' '.join(context.args)
    if not prompt:
        await update.message.reply_text("Descrivimi cosa vuoi vedere 👀")
        return
    await update.message.reply_text("Sto generando... 20-30 sec ⏳")
    try:
        img = query_hf_img(prompt)
        if b'error' in img[:100]:
            await update.message.reply_text("Ops, sono un po' lento... Riprova tra 30 sec.")
            return
        await update.message.reply_photo(io.BytesIO(img))
    except:
        await update.message.reply_text("Scusa, non posso generare immagini adesso 😕")

async def handle_text(update):
    chat_id = str(update.message.chat.id)
    memory = load_memory()
    user_history = memory.get(chat_id, [])
    
    user_history.append(update.message.text)
    memory[chat_id] = user_history[-10:]
    save_memory(memory)
    
    try:
        context = ' '.join(user_history)
        reply = query_groq_text(context)
        await update.message.reply_text(reply)
    except:
        await update.message.reply_text("Scusa, sto avendo un problemilla... Riprova tra un po'.")

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

def main():
    print("Will bot avviato...")
    application = telegram.ext.ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(telegram.ext.CommandHandler('start', handle_start))
    application.add_handler(telegram.ext.CommandHandler('img', handle_img))
    application.add_handler(telegram.ext.MessageHandler(telegram.ext.filters.TEXT & ~telegram.ext.filters.COMMAND, handle_text))
    application.run_polling()

if __name__ == "__main__":
    main()
