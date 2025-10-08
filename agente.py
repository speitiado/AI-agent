import os
import re
from typing import Annotated, Literal
from dotenv import load_dotenv
from pydantic import Field, BaseModel
import requests
from typing_extensions import TypedDict
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from langchain.tools import tool
from langgraph.graph.message import add_messages
load_dotenv()
llm = init_chat_model("openai:gpt-4o")

class messageClassifier(BaseModel):
    message_type : Literal["libre","climatica"] = Field(
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
    city = city.strip().lower()
    city = re.sub(r"(el clima en|cómo está|cómo estará|qué temperatura hay en|dime el clima de|hoy en|mañana en)", "", city, flags=re.IGNORECASE)
    city = city.strip().title()
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
    # Acceso seguro al contenido del mensaje
    if isinstance(last_message, dict):
        user_content = last_message.get("content", "")
    else:
        user_content = getattr(last_message, "content", str(last_message))
    classifier_llm = llm.with_structured_output(messageClassifier, method="function_calling")

    result = classifier_llm.invoke([
        {
            "role" : "system",
            "content" : """
                Clasifica el mensaje del usuario ya sea:
                -'libre': si pregunta por operaciones matematicas, quiere saber tu opinion sobre algun topico de conversacion o necesita realizar alguna tarea.
                -'climatica': si pregunta para saber el estado climatico de alguna ciudad o la temperatura
            """
        },
        {"role":"user","content":user_content}
    ])


    return {"message_type": result.message_type}


def router(state: State):
    print(f"DEBUG routing to: {state.get('message_type')}")
    return state

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
        {"role":"user","content":last_message["content"]}
    ]
    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}

def agente_clima(state: State):
    last_message = state["messages"][-1]
    llm_with_tools = llm.bind_tools([get_current_weather])
    
    messages = [
        {
            "role" : "system",
            "content" : """
                Sos un asistente especializado del clima.
                Brinda el estado climatico de la ciudad que el usuario pida.
                Debes brindar temperatura, el estado del clima y como se encontraran los cielos.
                Responde siempre con lenguaje natural y con informacion verificada de la tool del clima, tambien responde siempre de manera amigable y clara
            """
        },
        {"role":"user","content":last_message["content"]}
    ]
    reply = llm_with_tools.invoke(messages)
    print("DEBUG reply:", reply)
    return {"messages":[{"role":"assistant", "content": reply.content}]}

graph_builder = StateGraph(State)

graph_builder.add_node("classifier", clasify_message)
graph_builder.add_node("router", router)
graph_builder.add_node("libre", agente_libre)
graph_builder.add_node("especifica", agente_clima)

graph_builder.add_edge(START, "classifier")
graph_builder.add_conditional_edges(
    "router",
    lambda state: state.get("message_type"),
    path_map={"climatica": "especifica", "libre": "libre"}
)
graph_builder.add_edge("libre", END)
graph_builder.add_edge("especifica", END)
graph = graph_builder.compile()



def run_chatbot():
    state = {"messages": [], "message_type": None}

    while True:
        user_input = input("Message: ")
        if user_input == "exit":
            print("Bye")
            break

        state["messages"] = state.get("messages", []) + [
            {"role": "user", "content": user_input}
        ]

        state = graph.invoke(state)

        if state.get("messages") and len(state["messages"]) > 0:
            last_message = state["messages"][-1]
            # Acceso correcto al contenido
            if isinstance(last_message, dict):
                print(f"Assistant: {last_message['content']}")
            else:
                print(f"Assistant: {getattr(last_message, 'content', str(last_message))}")


if __name__ == "__main__":
    run_chatbot()