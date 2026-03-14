import requests
from django.conf import settings

def call_chat_api(messages):
    """
    Calls the OpenRouter API with the provided messages.
    """
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # "HTTP-Referer": "http://localhost:8000", # Optional
        # "X-Title": "Livestock Disease Prediction", # Optional
    }
    
    # Keep only the last 6 messages to manage context window
    messages = messages[-6:]
    
    data = {
        "model": settings.OPENROUTER_MODEL,
        "messages": messages,
        "max_tokens": 1500, # Limit tokens to reduce cost
    }
    
    try:
        response = requests.post(settings.OPENROUTER_API_URL, headers=headers, json=data)
        if response.status_code == 200:
            res_json = response.json()
            return res_json['choices'][0]['message']['content']
        else:
            return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Exception: {str(e)}"

def generate_ai_report(disease, symptoms):
    """
    Generates a detailed report for the predicted disease using AI.
    """
    prompt = (
        f"You are 'CliniPaws', an expert AI veterinarian assistant. A livestock animal has been diagnosed with '{disease}' "
        f"based on the following symptoms: {symptoms}.\n\n"
        "Please provide a comprehensive report in **English and URDU LANGUAGE** (use Urdu script also English) NOTE that first complete report in english and then write complete report in urdu(not mix both).\n"
        "The Urdu section must be **HIGHLY STRUCTURED** using bullet points and clear headings.\n\n"
        "Format the output clearly with the following sections:\n\n"
        "1. **Disease Description (بیماری کی تفصیل)**:\n"
        "Explain the disease in detail in Urdu and English.\n"
        "- Use bullet points for key facts in Urdu.\n\n"
        "2. **Early Stages (ابتدائی علامات)**:\n"
        "What to look for initially.\n"
        "- List symptoms in Urdu using bullet points (•).\n\n"
        "3. **Immediate Actions (فوری اقدامات)**:\n"
        "What the farmer should do immediately.\n"
        "- Step-by-step guide in Urdu using numbered lists (1, 2, 3).\n\n"
        "4. **Recommended Medicines (تجویز کردہ ادویات)**:\n"
        "List medicines. Write medicine names in English (Capitalized) but explain usage in Urdu.\n"
        "- Example: OXYTETRACYCLINE - (اردو میں استعمال کا طریقہ)\n\n"
        "5. **Additional Advice (مزید مشورے)**:\n"
        "Precautions and diet.\n"
        "- Use bullet points for diet and care tips in Urdu.\n\n"
        "Please ensure that the Urdu text is written with correct grammar and presented in a professional format"
        "IMPORTANT NOTE: Do not include any special characters such as asterisk, dash, slash, at symbol, dot, hash, or any other similar signs. Headings must be bold. Keep the Urdu and English sections completely separate. Do not use any Hindi words; if a term needs to be non-Urdu, use the English equivalent instead."
    )
    
    messages = [{"role": "user", "content": prompt}]
    return call_chat_api(messages)
