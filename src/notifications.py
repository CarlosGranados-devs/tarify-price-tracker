import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuración vía variables de entorno o valores por defecto
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
NOTIFY_EMAIL_TO = os.getenv("NOTIFY_EMAIL_TO", "")

def enviar_alerta_telegram(nombre_producto, precio_anterior, precio_nuevo, url):
    """
    Envía un mensaje de alerta a un chat/canal de Telegram cuando baja un precio.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Notifications] Telegram no configurado (falta BOT_TOKEN o CHAT_ID).")
        return False

    descuento = round(((precio_anterior - precio_nuevo) / precio_anterior) * 100, 2)
    
    mensaje = (
        f"🚨 <b>¡ALERTA DE BAJA DE PRECIO EN TARIFY!</b> 🚨\n\n"
        f"📦 <b>Producto:</b> {nombre_producto}\n"
        f"💵 <b>Precio anterior:</b> ${precio_anterior:.2f} USD\n"
        f"🔥 <b>Nuevo precio:</b> ${precio_nuevo:.2f} USD\n"
        f"📉 <b>Descuento:</b> {descuento}%\n\n"
        f"🔗 <a href='{url}'>Ver producto en la tienda</a>"
    )

    endpoint = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }

    try:
        res = requests.post(endpoint, json=payload, timeout=5)
        if res.status_code == 200:
            print(f"[Notifications] Alerta enviada a Telegram para: {nombre_producto}")
            return True
        else:
            print(f"[Notifications Error] Error Telegram HTTP {res.status_code}: {res.text}")
            return False
    except Exception as e:
        print(f"[Notifications Error] Excepción al enviar a Telegram: {e}")
        return False


def enviar_alerta_email(nombre_producto, precio_anterior, precio_nuevo, url):
    """
    Envía un correo electrónico HTML de notificación con la oferta.
    """
    if not SMTP_USER or not SMTP_PASSWORD or not NOTIFY_EMAIL_TO:
        print("[Notifications] Email no configurado (falta SMTP_USER, SMTP_PASSWORD o NOTIFY_EMAIL_TO).")
        return False

    descuento = round(((precio_anterior - precio_nuevo) / precio_anterior) * 100, 2)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔥 Bajó de precio: {nombre_producto} (-{descuento}%)"
    msg["From"] = SMTP_USER
    msg["To"] = NOTIFY_EMAIL_TO

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #181a20; color: #f1f5f9; padding: 20px;">
        <div style="max-width: 500px; margin: 0 auto; background: #20232b; padding: 25px; border-radius: 16px;">
          <h2 style="color: #3B82F6; margin-top: 0;">Tarify Price Alert</h2>
          <p>¡El producto que estás monitoreando ha alcanzado un precio más bajo!</p>
          <hr style="border: 1px solid #333;" />
          <h3>{nombre_producto}</h3>
          <p><strong>Precio anterior:</strong> <span style="text-decoration: line-through; color: #94a3b8;">${precio_anterior:.2f} USD</span></p>
          <p><strong>Nuevo precio:</strong> <span style="color: #10B981; font-size: 1.4rem; font-weight: bold;">${precio_nuevo:.2f} USD</span></p>
          <p style="color: #EF4444; font-weight: bold;">Ahorro del {descuento}%</p>
          <br/>
          <a href="{url}" style="background-color: #3B82F6; color: white; padding: 12px 20px; text-decoration: none; border-radius: 8px; display: inline-block;">Ir a la tienda</a>
        </div>
      </body>
    </html>
    """

    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, NOTIFY_EMAIL_TO, msg.as_string())
        print(f"[Notifications] Correo enviado exitosamente a {NOTIFY_EMAIL_TO}")
        return True
    except Exception as e:
        print(f"[Notifications Error] Excepción al enviar Email: {e}")
        return False