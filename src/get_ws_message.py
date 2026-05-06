import json
import os
import logging
import tempfile
import urllib.request

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info(f"Incoming event: {json.dumps(event)}")

    http_method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod", "")
    query_params = event.get("queryStringParameters") or {}

    if http_method == "GET":
        return handle_verification(query_params)
    elif http_method == "POST":
        return handle_message(event)
    else:
        return {"statusCode": 405, "body": json.dumps({"message": "Method not allowed"})}


def handle_verification(params):
    """
    Meta llama a este endpoint con GET para verificar el webhook.
    Debes responder con hub.challenge si el token coincide.
    """
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN")

    if mode == "subscribe" and token == verify_token:
        logger.info("Webhook verificado correctamente")
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/plain"},
            "body": challenge,
        }

    logger.warning(f"Verificación fallida. token recibido: {token}")
    return {"statusCode": 403, "body": json.dumps({"message": "Forbidden"})}


def handle_message(event):
    """
    Meta envía los mensajes de WhatsApp vía POST.
    """
    try:
        body = json.loads(event.get("body", "{}"))
        logger.info(f"Payload recibido: {json.dumps(body)}")

        # Extraer mensajes
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])

                for message in messages:
                    process_message(message, value)

        return {"statusCode": 200, "body": json.dumps({"status": "ok"})}

    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")
        return {"statusCode": 500, "body": json.dumps({"message": str(e)})}


def process_message(message, value):
    """
    Procesa un mensaje individual de WhatsApp.
    Aquí puedes agregar tu lógica de negocio.
    """
    msg_type = message.get("type")
    from_number = message.get("from")
    msg_id = message.get("id")
    timestamp = message.get("timestamp")

    logger.info(f"Mensaje de {from_number} | tipo: {msg_type} | id: {msg_id}")

    if msg_type == "text":
        text = message.get("text", {}).get("body", "")
        logger.info(f"Texto: {text}")
        # TODO: agregar lógica de respuesta o guardar en DynamoDB

    elif msg_type == "image":
        image = message.get("image", {})
        logger.info(f"Imagen recibida: {image.get('id')}")

    elif msg_type == "audio":
        audio = message.get("audio", {})
        media_id = audio.get("id")
        audio_url = audio.get("url")
        logger.info(f"Audio recibido: {media_id}")
        transcript = transcribe_whatsapp_audio(media_id, audio_url)
        if transcript:
            print(f"[Transcripción] {transcript}")
            logger.info(f"Transcripción del audio: {transcript}")

    elif msg_type == "interactive":
        interactive = message.get("interactive", {})
        logger.info(f"Mensaje interactivo: {interactive}")

    else:
        logger.info(f"Tipo de mensaje no manejado: {msg_type}")


def transcribe_whatsapp_audio(media_id: str, audio_url: str | None = None) -> str | None:
    """
    Descarga el audio de WhatsApp y lo transcribe con faster-whisper.
    Usa la URL del webhook si está disponible, sino la obtiene de la API de Meta.
    """
    api_token = os.environ.get("WHATSAPP_API_TOKEN")
    if not api_token:
        logger.error("Falta variable de entorno WHATSAPP_API_TOKEN")
        return None

    # Paso 1: obtener la URL de descarga
    if not audio_url:
        meta_url = f"https://graph.facebook.com/v21.0/{media_id}"
        req = urllib.request.Request(meta_url, headers={"Authorization": f"Bearer {api_token}"})
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                audio_url = data.get("url")
        except Exception as e:
            logger.error(f"Error obteniendo URL del audio: {e}")
            return None

    if not audio_url:
        logger.error(f"Meta API no devolvió URL para media_id={media_id}")
        return None

    # Paso 2: descargar el archivo de audio a /tmp
    logger.info(f"Descargando audio desde URL de Meta para media_id={media_id}")
    dl_req = urllib.request.Request(audio_url, headers={"Authorization": f"Bearer {api_token}"})
    try:
        with urllib.request.urlopen(dl_req) as resp:
            audio_bytes = resp.read()
    except Exception as e:
        logger.error(f"Error descargando audio (media_id={media_id}): {e}")
        return None

    # Paso 3: transcribir con faster-whisper (caché en /tmp)
    tmp_path = None
    try:
        import os as _os
        _os.environ["HF_HOME"] = "/tmp/hf"
        _os.environ["TRANSFORMERS_CACHE"] = "/tmp/hf"

        from faster_whisper import WhisperModel

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False, dir="/tmp") as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        model = WhisperModel("base", device="cpu", compute_type="int8", download_root="/tmp/whisper")
        segments, _ = model.transcribe(tmp_path, beam_size=5)
        transcript = " ".join(seg.text for seg in segments).strip()
        return transcript
    except Exception as e:
        logger.error(f"Error transcribiendo audio: {e}")
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def send_whatsapp_message(to_number, text):
    """
    Envía un mensaje de texto de vuelta al usuario.
    Requiere WHATSAPP_API_TOKEN y WHATSAPP_PHONE_NUMBER_ID como env vars.
    """
    api_token = os.environ.get("WHATSAPP_API_TOKEN")
    phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")

    if not api_token or not phone_number_id:
        logger.error("Faltan variables de entorno WHATSAPP_API_TOKEN o WHATSAPP_PHONE_NUMBER_ID")
        return False

    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    payload = json.dumps({
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text},
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            logger.info(f"Mensaje enviado: {result}")
            return True
    except Exception as e:
        logger.error(f"Error enviando mensaje de WhatsApp: {e}")
        return False
