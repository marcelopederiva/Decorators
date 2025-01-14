# monitor.py
import time
import psutil
from pynvml import nvmlInit, nvmlDeviceGetHandleByIndex, nvmlDeviceGetPowerUsage, nvmlShutdown
import matplotlib.pyplot as plt
from functools import wraps

def monitor_resources(func):
    def init_gpu():
        nvmlInit()
        handle = nvmlDeviceGetHandleByIndex(0)  # Usando GPU 0, adapte conforme necessário
        return handle

    def get_gpu_power(handle):
        return nvmlDeviceGetPowerUsage(handle) / 1000  # Convertendo para Watts

    @wraps(func)
    def wrapper(*args, **kwargs):
        cpu_percentages = []
        ram_usage = []
        gpu_power_usage = []
        timestamps = []
        handle = None

        try:
            handle = init_gpu()
        except Exception as e:
            print(f"Falha ao inicializar NVML: {e}")

        start_time = time.time()

        # Função monitorada
        def monitor():
            while not stop_monitoring:
                timestamps.append(time.time() - start_time)
                cpu_percentages.append(psutil.cpu_percent(interval=0.1))
                ram_usage.append(psutil.virtual_memory().used / (1024 ** 3))  # RAM em GB
                if handle:
                    try:
                        gpu_power_usage.append(get_gpu_power(handle))
                    except:
                        gpu_power_usage.append(0)
                else:
                    gpu_power_usage.append(0)
                time.sleep(0.1)

        # Inicia monitoramento em thread separada
        stop_monitoring = False
        from threading import Thread
        monitor_thread = Thread(target=monitor)
        monitor_thread.start()

        # Executa a função decorada
        result = func(*args, **kwargs)

        # Finaliza monitoramento
        stop_monitoring = True
        monitor_thread.join()

        # Finaliza NVML
        if handle:
            nvmlShutdown()

        # Plota os resultados
        fig, ax1 = plt.subplots(figsize=(10, 6))

        # Eixo esquerdo (GPU Power em Watts)
        ax1.set_xlabel("Tempo (s)")
        ax1.set_ylabel("GPU Power (W)", color="tab:green")
        ax1.plot(timestamps, gpu_power_usage, label="GPU Power (W)", color="tab:green")
        ax1.tick_params(axis="y", labelcolor="tab:green")

        # Eixo direito (CPU Usage %)
        ax2 = ax1.twinx()
        ax2.set_ylabel("CPU Usage (%)", color="tab:blue")
        ax2.plot(timestamps, cpu_percentages, label="CPU Usage (%)", color="tab:blue")
        ax2.tick_params(axis="y", labelcolor="tab:blue")

        # Título
        fig.suptitle("Consumo de Recursos Durante Execução")

        # Legendas
        ax1.legend(loc="upper left")
        ax2.legend(loc="upper right")
        
        plt.savefig("consumo_de_recurso.png")  

        return result

    return wrapper
