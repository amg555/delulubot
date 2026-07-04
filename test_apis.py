import os, requests
from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()

token = os.getenv('TELEGRAM_TOKEN')
groq_key = os.getenv('GROQ_API_KEY')

r = requests.get(f'https://api.telegram.org/bot{token}/getMe', timeout=10).json()
print(f'Telegram: @{r["result"]["username"]}')

gc = OpenAI(api_key=groq_key, base_url='https://api.groq.com/openai/v1')
resp = gc.chat.completions.create(model=os.getenv('GROQ_MODEL'), messages=[{'role':'user','content':'say ok'}], max_tokens=10)
print(f'Groq: OK - {resp.choices[0].message.content}')

u = requests.get(f'https://api.telegram.org/bot{token}/getUpdates', timeout=10).json()
print(f'Updates: {len(u["result"])}')
