import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from main import ejecutar_pipeline_monitoreo

def iniciar_programador(intervalo_minutos: int = 1):
    """
    Inicializa un scheduler en segundo plano para ejecutar 
    el pipeline de monitoreo periódicamente.
    """
    scheduler = BackgroundScheduler()
    
    # Agregar la tarea repetitiva con margen de tolerancia y ejecución inmediata
    scheduler.add_job(
        ejecutar_pipeline_monitoreo,
        'interval',
        minutes=intervalo_minutos,
        id='job_monitoreo_precios',
        next_run_time=datetime.now(),  # Ejecuta una vez al arrancar
        misfire_grace_time=30          # Da 30 segundos de margen antes de marcar retraso
    )
    
    scheduler.start()
    print("=" * 60)
    print(f"[SCHEDULER] Servicio iniciado. Ejecutando ciclo cada {intervalo_minutos} minuto(s).")
    print("[SCHEDULER] Presiona CTRL+C para detener la ejecución.")
    print("=" * 60)

    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("\n[SCHEDULER] Servicio detenido limpiamente.")

if __name__ == "__main__":
    iniciar_programador(intervalo_minutos=1)