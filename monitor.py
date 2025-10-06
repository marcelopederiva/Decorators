# monitor.py
import time
import psutil
try:
    from pynvml import (
        nvmlInit, 
        nvmlDeviceGetHandleByIndex, 
        nvmlDeviceGetPowerUsage,
        nvmlDeviceGetMemoryInfo,
        nvmlShutdown
    )
    NVML_AVAILABLE = True
except ImportError:
    try:
        import nvidia_smi
        NVML_AVAILABLE = True
    except ImportError:
        NVML_AVAILABLE = False
        print("Aviso: nvidia-ml-py não está instalado. Métricas de GPU não estarão disponíveis.")

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


def monitor_resources_2(func):
    def init_gpu():
        nvmlInit()
        handle = nvmlDeviceGetHandleByIndex(0)  # Usando GPU 0, adapte conforme necessário
        return handle

    def get_gpu_memory(handle):
        try:
            mem_info = nvmlDeviceGetMemoryInfo(handle)
            return mem_info.used / (1024 ** 3)  # Convertendo para GB
        except Exception as e:
            print(f"Erro ao obter memória GPU: {e}")
            return 0

    @wraps(func)
    def wrapper(*args, **kwargs):
        cpu_percentages = []
        ram_usage = []
        gpu_memory_usage = []
        timestamps = []
        handle = None
        gpu_available = False

        try:
            handle = init_gpu()
            gpu_available = True
            print("GPU inicializada com sucesso para monitoramento")
        except Exception as e:
            print(f"Falha ao inicializar NVML: {e}")
            print("Continuando sem monitoramento de GPU...")

        start_time = time.time()

        # Função monitorada
        def monitor():
            while not stop_monitoring:
                timestamps.append(time.time() - start_time)
                cpu_percentages.append(psutil.cpu_percent(interval=0.1))
                ram_usage.append(psutil.virtual_memory().used / (1024 ** 3))  # RAM em GB
                
                if handle and gpu_available:
                    gpu_mem = get_gpu_memory(handle)
                    gpu_memory_usage.append(gpu_mem)
                else:
                    gpu_memory_usage.append(0)
                    
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
            try:
                nvmlShutdown()
            except:
                pass

        # Debug: imprime estatísticas
        print(f"\nEstatísticas de monitoramento:")
        print(f"GPU Memory - Min: {min(gpu_memory_usage):.2f} GB, Max: {max(gpu_memory_usage):.2f} GB, Média: {sum(gpu_memory_usage)/len(gpu_memory_usage):.2f} GB")
        print(f"CPU - Min: {min(cpu_percentages):.1f}%, Max: {max(cpu_percentages):.1f}%, Média: {sum(cpu_percentages)/len(cpu_percentages):.1f}%")
        print(f"RAM - Min: {min(ram_usage):.2f} GB, Max: {max(ram_usage):.2f} GB, Média: {sum(ram_usage)/len(ram_usage):.2f} GB")

        # Plota os 3 gráficos separados
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12))

        # Gráfico 1: GPU Memory
        ax1.plot(timestamps, gpu_memory_usage, label="GPU Memory (GB)", color="tab:green", linewidth=2)
        ax1.set_xlabel("Tempo (s)")
        ax1.set_ylabel("GPU Memory (GB)", color="tab:green")
        ax1.tick_params(axis="y", labelcolor="tab:green")
        ax1.set_title("Uso de Memória GPU")
        ax1.legend(loc="upper left")
        ax1.grid(True, alpha=0.3)
        if not gpu_available or max(gpu_memory_usage) == 0:
            ax1.text(0.5, 0.5, 'GPU não disponível ou sem uso', 
                    transform=ax1.transAxes, ha='center', va='center', 
                    fontsize=12, color='red', alpha=0.5)

        # Gráfico 2: CPU Usage
        ax2.plot(timestamps, cpu_percentages, label="CPU Usage (%)", color="tab:blue", linewidth=2)
        ax2.set_xlabel("Tempo (s)")
        ax2.set_ylabel("CPU Usage (%)", color="tab:blue")
        ax2.tick_params(axis="y", labelcolor="tab:blue")
        ax2.set_title("Uso de CPU")
        ax2.legend(loc="upper left")
        ax2.grid(True, alpha=0.3)

        # Gráfico 3: RAM Usage
        ax3.plot(timestamps, ram_usage, label="RAM Usage (GB)", color="tab:red", linewidth=2)
        ax3.set_xlabel("Tempo (s)")
        ax3.set_ylabel("RAM Usage (GB)", color="tab:red")
        ax3.tick_params(axis="y", labelcolor="tab:red")
        ax3.set_title("Uso de RAM")
        ax3.legend(loc="upper left")
        ax3.grid(True, alpha=0.3)

        # Título geral
        fig.suptitle("Monitoramento de Recursos Durante Execução", fontsize=14, y=0.995)
        
        plt.tight_layout()
        plt.savefig("consumo_de_recursos_detalhado.png", dpi=300, bbox_inches='tight')
        plt.close()

        return result

    return wrapper
