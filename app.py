import chainlit as cl
import openai
from langsmith import traceable
from langsmith.wrappers import wrap_openai

from config_llm import config, model_kwargs
from prompts import BASE_SYSTEM_PROMPT
from config_app import config_area

from rag_pipeline import get_query_engine

from dotenv import load_dotenv
load_dotenv()

# Initialize the OpenAI async client
client = wrap_openai(openai.AsyncClient(api_key=config["api_key"], base_url=config["endpoint_url"]))

# Initialize the query engine
query_engine = get_query_engine()

@traceable
@cl.on_message
async def on_message(message: cl.Message):
    # Maintain an array of messages in the user session
    message_history = cl.user_session.get("message_history", [])

    # Add system prompt to the start of the message history if not already present
    if (not message_history or message_history[0].get("role") != "system"):
        system_prompt = BASE_SYSTEM_PROMPT.format(config_area=config_area)
        message_history.insert(0, {"role": "system", "content": system_prompt})
        # print("System prompt:" + system_prompt)
    
    print("Chat interface: message received:" + message.content)
    
    # Get context from RAG
    rag_response = query_engine.query(message.content)
    rag_context = str(rag_response)
    print("RAG context: " + rag_context)
    
    # Append RAG context and user message to message history
    message_history.append({"role": "user", "content": f"Context: {rag_context}\n\nQuestion: {message.content}"})
        
    response_message = cl.Message(content="")
    await response_message.send()

    stream = await client.chat.completions.create(
        messages=message_history,
        stream=True, **model_kwargs
    )
    async for part in stream:
        if token := part.choices[0].delta.content or "":
            await response_message.stream_token(token)

    await response_message.update()

    # Record the AI's response in the history
    message_history.append({"role": "assistant", "content": response_message.content})
    cl.user_session.set("message_history", message_history)


if __name__ == "__main__":
    cl.main()