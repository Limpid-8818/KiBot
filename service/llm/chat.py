from openai import OpenAI


async def chat_handler(settings: dict, text: str) -> str:
    try:
        client = OpenAI(
            api_key=settings["llm_key"],
            base_url=settings["llm_base"],
        )
        response = client.chat.completions.create(
            model=settings["llm_model"],
            messages=[{"role": "user", "content": text}],
            temperature=0.7
        )
        reply = response.choices[0].message.content.strip()
        return reply
    except Exception as e:
        return f"Error: {str(e)}"
