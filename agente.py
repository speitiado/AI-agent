from json import tool
import os
from typing import Annotated, Literal
from dotenv import load_dotenv
from openai import BaseModel
from pydantic import Field
import requests
from typing_extensions import TypedDict
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langgraph import tool
from langgraph.graph.message import add_messages
load_dotenv()
llm = init_chat_model("openai:gpt-4.1",temperature=0)

class messageClassifier(BaseModel):
    messsage_type : Literal["libre","climatica"] = Field(
        ...,
        description = "clasifica si el mensaje del usuario requiere una respuesta comun (libre) o una respuesta  especifica (climatica)"
    )

@tool("get_current_weather", description="Obtiene el clima actual de una ciudad del mundo.")
def get_current_weather(city: str, units: str = "metric", lang: str = "es") -> dict:
    """
    Devuelve el clima actual para una ciudad específica usando OpenWeatherMap.

    Args:
        city (str): Nombre de la ciudad (por ejemplo, "Madrid", "Buenos Aires").
        units (str): Unidades de medida ("metric" para °C, "imperial" para °F).
        lang (str): Idioma de la respuesta de la API (por defecto español).

    Returns:
        dict: Información del clima actual con temperatura, humedad, etc.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return {"error": "Falta la API key de OpenWeatherMap."}

    url = (
        f"https://api.openweathermap.org/data/2.5/weather?"
        f"q={city}&appid={api_key}&units={units}&lang={lang}"
    )

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if response.status_code != 200:
            return {"error": data.get("message", "Error al obtener el clima.")}

        weather_info = {
            "ciudad": data["name"],
            "pais": data["sys"]["country"],
            "condicion": data["weather"][0]["description"],
            "temperatura": data["main"]["temp"],
            "sensacion_termica": data["main"]["feels_like"],
            "humedad": data["main"]["humidity"],
            "viento": data["wind"]["speed"],
            "icono": f"https://openweathermap.org/img/wn/{data['weather'][0]['icon']}@2x.png"
        }

        return weather_info

    except Exception as e:
        return {"error": f"Ocurrió un error al consultar el clima: {str(e)}"}


class State(TypedDict):
    messages: Annotated[list, add_messages]
    message_type: str | None

def clasify_message(state: State):
    last_message = state["messages"][-1]
    classifier_llm = llm.with_structured_output(messageClassifier)

    result = classifier_llm.invoke([
        {
            "role" : "system",
            "content" : """
                Clasifica el mensaje del usuario ya sea:
                -'libre': si pregunta por operaciones matematicas, quiere saber tu opinion sobre algun topico de conversacion o necesita realizar alguna tarea.
                -'climatica': si pregunta para saber el estado climatico de alguna ciudad o la temperatura
            """
        },
        {"role":"user","content":last_message.content}
    ])
    return {"message_type": result.message_type}

def chatbot(state: State):
    return {"messages": [llm.invoke(state["messages"])]}

def router (state: State):
    message_type = state.get("message_type", "libre")
    if message_type == "climatica": 
        return {"next": "especifica"}
    
    return {"next":"libre"}

def agente_libre(state: State):
    last_message = state["messages"][-1]

    messages = [
        {
            "role" : "system",
            "content" : """
               Eres un asistente conversacional que entiende la intención del usuario. 
               Cualquier pregunta del usuario que realice trataras de reponderle con la mejor informacion posible.
               Si realiza preguntas logicas o matematicas, respondele siendo lo mas claro posible.
            """
        },
        {"role":"user","content":last_message.content}
    ]
    reply = llm.invoke(messages)
    return {"messages": [{"role": "asisstant", "content": reply.content}]}

def agente_clima():
    pass

graph_builder = StateGraph(State)

def chatbot(state: State):
    return {"messages": [llm.invoke(state["messages"])]}

graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
graph = graph_builder.compile()

def stream_graph_updates(user_input: str):
    for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)


while True:
    try:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        stream_graph_updates(user_input)
    except:
        # fallback if input() is not available
        user_input = "What do you know about LangGraph?"
        print("User: " + user_input)
        stream_graph_updates(user_input)
        break

