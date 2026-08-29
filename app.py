import os
import io
import requests
import tempfile
from flask import Flask, request, jsonify
from PIL import Image

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "mon_token_secret")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID", "")


# ── Vérification webhook Meta ──────────────────────────────────────────────────
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403


# ── Réception des messages ─────────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json()
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" not in value:
            return jsonify({"status": "ok"}), 200

        message = value["messages"][0]
        sender = message["from"]
        msg_type = message["type"]

        if msg_type == "image":
            image_id = message["image"]["id"]
            handle_image(sender, image_id)
        elif msg_type == "text":
            texte = message["text"]["body"].lower()
            if any(w in texte for w in ["bonjour", "salut", "hello", "aide", "help"]):
                send_text(sender,
                    "Bonjour ! Envoyez-moi une vieille photo et je vais la restaurer pour vous.\n\n"
                    "Je peux :\n• Améliorer la netteté\n• Réparer les visages abîmés\n• Réduire le bruit et les rayures"
                )
            else:
                send_text(sender, "Envoyez-moi une photo pour commencer la restauration.")

    except (KeyError, IndexError):
        pass

    return jsonify({"status": "ok"}), 200


# ── Traitement de l'image ──────────────────────────────────────────────────────
def handle_image(sender: str, image_id: str):
    send_text(sender, "Photo reçue ! Restauration en cours... (30-60 secondes)")

    try:
        image_bytes = download_whatsapp_image(image_id)
        restored_bytes = restore_image(image_bytes)
        send_image(sender, restored_bytes)
        send_text(sender, "Voilà votre photo restaurée !")
    except Exception as e:
        print(f"Erreur restauration: {e}")
        send_text(sender, "Désolé, une erreur est survenue. Réessayez avec une autre photo.")


def download_whatsapp_image(image_id: str) -> bytes:
    """Télécharge l'image depuis les serveurs Meta."""
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

    # 1. Récupérer l'URL de téléchargement
    r = requests.get(
        f"https://graph.facebook.com/v19.0/{image_id}",
        headers=headers
    )
    r.raise_for_status()
    url = r.json()["url"]

    # 2. Télécharger l'image
    r2 = requests.get(url, headers=headers)
    r2.raise_for_status()
    return r2.content


def restore_image(image_bytes: bytes) -> bytes:
    """
    Restauration de la photo.
    Utilise GFPGAN (visages) + Real-ESRGAN (super-résolution).
    En attendant l'installation des modèles, applique un traitement PIL basique.
    """
    try:
        from restoration import full_restoration
        return full_restoration(image_bytes)
    except ImportError:
        return basic_enhancement(image_bytes)


def basic_enhancement(image_bytes: bytes) -> bytes:
    """Amélioration basique via PIL (netteté + contraste)."""
    from PIL import ImageEnhance, ImageFilter

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    img = ImageEnhance.Contrast(img).enhance(1.2)
    img = ImageEnhance.Sharpness(img).enhance(1.5)
    img = ImageEnhance.Color(img).enhance(1.1)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


# ── Envoi de messages WhatsApp ─────────────────────────────────────────────────
def send_text(to: str, text: str):
    requests.post(
        f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages",
        headers={
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text}
        }
    )


def send_image(to: str, image_bytes: bytes):
    """Upload l'image sur Meta puis l'envoie."""
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

    # 1. Upload vers Meta
    files = {"file": ("restored.jpg", image_bytes, "image/jpeg"),
             "messaging_product": (None, "whatsapp")}
    r = requests.post(
        f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/media",
        headers=headers,
        files=files
    )
    r.raise_for_status()
    media_id = r.json()["id"]

    # 2. Envoyer le message image
    requests.post(
        f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages",
        headers={**headers, "Content-Type": "application/json"},
        json={
            "messaging_product": "whatsapp",
            "to": to,
            "type": "image",
            "image": {"id": media_id}
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
