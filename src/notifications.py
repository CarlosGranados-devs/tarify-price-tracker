import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "notificaciones@monitordeprecios.com")
EMAIL_TO = os.getenv("EMAIL_TO", "usuario@ejemplo.com")

def enviar_alerta_email(nombre_producto: str, url: str, precio_anterior: float, precio_nuevo: float, porcentaje: float):
    """
    Construye y envia un correo de alerta de variacion de precio.
    Si las credenciales no son validas, realiza una simulacion (Mock).
    """
    signo = "+" if porcentaje > 0 else ""
    asunto = f"[ALERTA PRECIO] {nombre_producto[:30]} ({signo}{porcentaje:.2f}%)"

    cuerpo = f"""
    Hola,

    Se ha detectado un cambio de precio en uno de los productos monitoreados:

    Producto: {nombre_producto}
    Precio Anterior: GBP {precio_anterior:.2f}
    Precio Nuevo: GBP {precio_nuevo:.2f}
    Variacion: {signo}{porcentaje:.2f}%
    Enlace: {url}

    Atentamente,
    Monitor de Precios SaaS
    """

    mensaje = MIMEMultipart()
    mensaje["From"] = EMAIL_FROM
    mensaje["To"] = EMAIL_TO
    mensaje["Subject"] = asunto
    mensaje.attach(MIMEText(cuerpo, "plain"))

    # Si no hay credenciales minimas cargadas
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"[NOTIFICACION MOCK] Correo simulado a '{EMAIL_TO}' | Asunto: {asunto}")
        return True

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(mensaje)
        server.quit()
        print(f"[NOTIFICACION EXITOSA] Correo enviado a {EMAIL_TO}")
        return True
    except Exception as error:
        print(f"[NOTIFICACION MOCK - FALLBACK] No se pudo autenticar en SMTP ({error}).")
        print(f"[NOTIFICACION MOCK] Correo simulado a '{EMAIL_TO}' | Asunto: {asunto}")
        return True

if __name__ == "__main__":
    enviar_alerta_email(
        nombre_producto="A Light in the Attic",
        url="https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        precio_anterior=51.77,
        precio_nuevo=45.00,
        porcentaje=-13.08
    )