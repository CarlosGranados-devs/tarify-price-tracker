import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Cargar automáticamente las variables del archivo .env
load_dotenv()

# Variables de Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip('"\'')
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip('"\'')

# Variables SMTP
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", os.getenv("SMTP_USER", ""))
EMAIL_TO = os.getenv("EMAIL_TO", "")


def enviar_alerta_telegram(nombre_producto, precio_anterior, precio_nuevo, url):
    """
    Envía una notificación push a Telegram cuando un producto baja de precio.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Notifications] Telegram no configurado (falta TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID en .env).")
        return False

    descuento = round(((precio_anterior - precio_nuevo) / precio_anterior) * 100, 2)
    
    mensaje = (
        f"🚨 <b>¡ALERTA DE BAJA DE PRECIO EN TARIFY!</b> 🚨\n\n"
        f"📦 <b>Producto:</b> {nombre_producto}\n"
        f"💵 <b>Precio anterior:</b> ${precio_anterior:.2f} USD\n"
        f"🔥 <b>Nuevo precio:</b> ${precio_nuevo:.2f} USD\n"
        f"📉 <b>Descuento:</b> {descuento}%\n\n"
        f"🔗 <a href='{url}'>Ver oferta en la tienda</a>"
    )

    endpoint = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:
        res = requests.post(endpoint, json=payload, timeout=8)
        if res.status_code == 200:
            print(f"[Notifications] Alerta enviada a Telegram para: '{nombre_producto}'")
            return True
        else:
            print(f"[Notifications Error] Fallo Telegram HTTP {res.status_code}: {res.text}")
            return False
    except Exception as e:
        print(f"[Notifications Error] Excepción al enviar a Telegram: {e}")
        return False


def enviar_alerta_email(nombre_producto, precio_anterior, precio_nuevo, url):
    """
    Envía un correo electrónico HTML formal cuando detecta una baja de precio.
    """
    if not SMTP_USER or not SMTP_PASSWORD or not EMAIL_TO:
        print("[Notifications] Email omitido (falta configurar credenciales SMTP en .env).")
        return False

    descuento = round(((precio_anterior - precio_nuevo) / precio_anterior) * 100, 2)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔥 Descuento Detectado: {nombre_producto} (-{descuento}%)"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    html_content = f"""
    <html>
      <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #181a20; color: #f1f5f9; padding: 30px;">
        <div style="max-width: 520px; margin: 0 auto; background: #20232b; padding: 30px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
          <h2 style="color: #3B82F6; margin-top: 0; font-size: 1.5rem;">Tarify Price Intelligence</h2>
          <p style="color: #94a3b8; font-size: 0.95rem;">Un producto en tu lista de seguimiento ha bajado de precio.</p>
          <hr style="border: 0; height: 1px; background: #334155; margin: 20px 0;" />
          <h3 style="font-size: 1.2rem; color: #ffffff;">{nombre_producto}</h3>
          <p style="margin: 10px 0;"><strong>Precio anterior:</strong> <span style="text-decoration: line-through; color: #94a3b8;">${precio_anterior:.2f} USD</span></p>
          <p style="margin: 10px 0;"><strong>Nuevo precio:</strong> <span style="color: #10B981; font-size: 1.5rem; font-weight: bold;">${precio_nuevo:.2f} USD</span></p>
          <p style="color: #EF4444; font-weight: bold; font-size: 1.1rem; margin-top: 15px;">Ahorras un {descuento}%</p>
          <br/>
          <a href="{url}" style="background-color: #3B82F6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 10px; display: inline-block; font-weight: bold;">Ver en Tienda</a>
        </div>
      </body>
    </html>
    """

    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        print(f"[Notifications] Correo enviado exitosamente a: {EMAIL_TO}")
        return True
    except Exception as e:
        print(f"[Notifications Error] Excepción al enviar Email: {e}")
        return False