def guess_whisper_model(gpu_freemem_mb: int | float) -> str:
    """Source: https://github.com/openai/whisper"""
    if gpu_freemem_mb > 10000:
        return "large"
    elif gpu_freemem_mb > 5000:
        return "medium"
    elif gpu_freemem_mb > 2000:
        return "small"
    elif gpu_freemem_mb > 100:
        return "base"
    return ""


def get_max_gpu_memory() -> int:
    try:
        import pynvml

        pynvml.nvmlInit()
        max_mem = 0
        for idx in range(pynvml.nvmlDeviceGetCount()):
            h = pynvml.nvmlDeviceGetHandleByIndex(idx)
            info = pynvml.nvmlDeviceGetMemoryInfo(h)
            if max_mem < info.free:
                max_mem = info.free

        pynvml.nvmlShutdown()
        return max_mem
    except ImportError:
        raise ImportError(
            "In order to run the server, you need to have whisper installed locally."
        )
