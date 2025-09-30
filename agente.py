import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def consultar_gpt(mensaje, historial):
    messages = historial + [{"role": "user", "content": mensaje}]
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # rápido y económico
        messages=messages
    )
    return response.choices[0].message.content

# Acciones simuladas
def crear_reunion(mensaje):
    return "📅 Reunión creada: mañana a las 10:00 (simulada)."

def enviar_notificacion(mensaje):
    return "🔔 Notificación enviada (simulada)."

def procesar_pago(mensaje):
    return "💳 Pago procesado con éxito (simulado)."

acciones = {
    "reunion": crear_reunion,
    "notificacion": enviar_notificacion,
    "pago": procesar_pago
}

def detectar_accion(mensaje):
    mensaje_l = mensaje.lower()
    if "reunion" in mensaje_l or "agendar" in mensaje_l:
        return "reunion"
    if "notificar" in mensaje_l or "avísame" in mensaje_l:
        return "notificacion"
    if "pago" in mensaje_l or "cobrar" in mensaje_l:
        return "pago"
    return "conversar"

def main():
    historial = []
    print("🤖 Agente AI listo (escribí 'salir' para terminar)\n")

    while True:
        user_input = input("Tú: ")
        if user_input.lower() == "salir":
            break

        accion = detectar_accion(user_input)

        if accion == "conversar":
            respuesta = consultar_gpt(user_input, historial)
            historial.append({"role": "user", "content": user_input})
            historial.append({"role": "assistant", "content": respuesta})
        else:
            respuesta = acciones[accion](user_input)

        print("Agente:", respuesta, "\n")

if __name__ == "__main__":
    main()
