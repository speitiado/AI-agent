import os
from langgraph.graph import StateGraph, END
from typing import TypedDict
from langchain_openai import ChatOpenAI, OpenAI
from langchain.prompts import ChatPromptTemplate
import requests
import tomllib
import json
from dotenv import load_dotenv
load_dotenv()  

llm = ChatOpenAI(model="gpt-4o", temperature=0)
with open("prompt.toml", "rb") as f:
    prompts = tomllib.load(f)

formatter_prompt = ChatPromptTemplate.from_messages([
    ("system", prompts["output_formatter"]["system"]),
    ("human", prompts["output_formatter"]["human"])
])
orchestrator_prompt = ChatPromptTemplate.from_messages([
    ("system", prompts["orchestrator"]["system"]),
    ("human", prompts["orchestrator"]["human"])
])

class WeatherState(TypedDict,  total=False):
    city: str
    raw_data: dict
    output: dict
    route: str


def input_parser(state: dict) -> dict:
    city_cleaned = state["city"].strip().title()
    state["city"] = city_cleaned
    return state


def orchestrator(state: dict) -> dict:
    inputs = {"input": state["city"]}
    response = llm.invoke(orchestrator_prompt.format_messages(**inputs))

    try:
        decision = json.loads(response.content)
    except Exception:
        # fallback seguro si no es JSON válido
        state["output"] = {"response": "No entendí tu consulta. Pregúntame por una ciudad para ver el clima."}
        state["route"] = "chat"
        return state

    # Normalizar claves posibles ("\"response\"" → "response")
    if any(k.strip('"') == "response" for k in decision.keys()):
        value = list(decision.values())[0]
        state["output"] = {"response": value}
        state["route"] = "chat"
    elif decision.get("action") == "weather":
        state["city"] = decision["city"]
        state["route"] = "weather"
    else:
        state["output"] = {"response": "No entendí tu consulta. Pregúntame por una ciudad para ver el clima."}
        state["route"] = "chat"

    return state

def weather_fetcher(state: dict) -> dict:
    city = state["city"]

    # Mapeo de códigos meteorológicos a texto
    WEATHER_CODES = {
        0: "Despejado",
        1: "Principalmente despejado",
        2: "Parcialmente nublado",
        3: "Nublado",
        45: "Niebla",
        48: "Niebla con escarcha",
        51: "Llovizna ligera",
        53: "Llovizna moderada",
        55: "Llovizna densa",
        61: "Lluvia ligera",
        63: "Lluvia moderada",
        65: "Lluvia intensa",
        71: "Nieve ligera",
        73: "Nieve moderada",
        75: "Nieve intensa",
        95: "Tormenta ligera o moderada",
        99: "Tormenta con granizo"
    }

    try:
        # Paso 1: geocodificar ciudad → lat/lon
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=es&format=json"
        geo_resp = requests.get(geo_url).json()

        if "results" not in geo_resp or len(geo_resp["results"]) == 0:
            state["raw_data"] = None
            return state

        lat = geo_resp["results"][0]["latitude"]
        lon = geo_resp["results"][0]["longitude"]

        # Paso 2: obtener clima actual
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_resp = requests.get(weather_url).json()

        temp = weather_resp["current_weather"]["temperature"]
        code = weather_resp["current_weather"]["weathercode"]

        condition = WEATHER_CODES.get(code, f"Código {code} (desconocido)")

        state["raw_data"] = {
            "temperature": f"{temp} °C",
            "condition": condition
        }

    except Exception as e:
        state["raw_data"] = {"error": str(e)}

    return state

def output_formatter(state: dict) -> dict:
    inputs = {
        "city": state["city"],
        "raw_data": state["raw_data"] if state.get("raw_data") else "None"
    }

    response = llm.invoke(formatter_prompt.format_messages(**inputs))

    try:
        state["output"] = json.loads(response.content)
    except Exception:
        state["output"] = {
            "city": state["city"],
            "temperature": None,
            "condition": None,
            "success": False,
            "error": "Error al generar JSON en el LLM."
        }
    return state


workflow = StateGraph(WeatherState)

workflow.add_node("orchestrator", orchestrator)
workflow.set_entry_point("orchestrator")

workflow.add_node("input_parser", input_parser)
workflow.add_node("weather_fetcher", weather_fetcher)
workflow.add_node("output_formatter", output_formatter)

workflow.add_conditional_edges(
    "orchestrator",
    lambda state: state["route"],
    {
        "weather": "input_parser",
        "chat": END,
    },
)

workflow.add_edge("input_parser", "weather_fetcher")
workflow.add_edge("weather_fetcher", "output_formatter")
workflow.add_edge("output_formatter", END)

graph = workflow.compile()

if __name__ == "__main__":
    print("🤖 Agente del clima iniciado. Escribe 'salir' para terminar.\n")

    while True:
        user_input = input("👤 Tú: ")

        if user_input.lower() in ["salir", "exit", "quit"]:
            print("🤖 Agente: ¡Hasta luego! ☀️")
            break

        result = graph.invoke({"city": user_input})

        # Mostrar respuesta en JSON formateado
        print("🤖 Agente:")
        print(json.dumps(result["output"], indent=2, ensure_ascii=False))
        print()
