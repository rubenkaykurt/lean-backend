# backend_suscripciones/main.py

from flask import Flask, request, jsonify, redirect
import stripe
import os
from dotenv import load_dotenv
import requests
from flask_cors import CORS


load_dotenv()

app = Flask(__name__)
CORS(app)  # ← Esto permite solicitudes desde otros dominios como terapyel.com

print("⚙️ Flask está corriendo desde Render.")

@app.route("/")
def home():
    return "Backend funcionando correctamente ✅"

# Configurar Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# URL del frontend (donde redirigir tras el pago)
SUCCESS_URL = os.getenv("SUCCESS_URL", "https://www.terapyel.com/panel-gpt")
CANCEL_URL = os.getenv("CANCEL_URL", "https://www.terapyel.com/asistente-formulacion")

# Endpoint para crear la sesión de pago
@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    try:
        print("➡️ Solicitud recibida correctamente. Procediendo a crear sesión.")

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{
                "price": os.getenv("STRIPE_PRICE_ID"),
                "quantity": 1,
            }],
            success_url=SUCCESS_URL + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=CANCEL_URL,
        )

        print("✅ Sesión creada:", session.id)
        return jsonify({"url": session.url})
    except Exception as e:
        print("❌ Error creando sesión:", str(e))
        return jsonify(error=str(e)), 400

# Webhook para recibir notificación de Stripe y crear usuario en Lean Automation
@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except Exception as e:
        return str(e), 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_email = session.get("customer_email")
        if customer_email:
            # Aquí se llama a Lean Automation para crear el usuario
            try:
                requests.post("https://api.leanautomation.com/create-user", json={
                    "email": customer_email,
                    "plan": "suscripcion-ia"
                })
            except Exception as e:
                print("Error al crear usuario en Lean Automation:", e)

    return "", 200

# Para test rápido
@app.route("/ping")
def ping():
    return "pong"

if __name__ == "__main__":
    app.run(debug=True)
