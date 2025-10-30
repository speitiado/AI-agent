import operator
from dotenv import load_dotenv
from langchain.tools import tool
from langchain.chat_models import init_chat_model
from langchain.messages import AnyMessage
from typing_extensions import TypedDict, Annotated
from langchain.messages import SystemMessage
import os
load_dotenv()

model = init_chat_model(
    "openai:gpt-5-mini",
    temperature=0
)

class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int



def node_solucion_modem(messages: MessagesState):
    pass

def node_consultar_planes(messages: MessagesState):
    pass

def node_procesar_pago(messages: MessagesState):
    pass


def router(messages: MessagesState):
    mensaje_l = messages.lower()
    

def main():
  pass

if __name__ == "__main__":
    main()
