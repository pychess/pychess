import platform
import sys


def get_cpu():
    result = {}

    # Operating system
    result["platform"] = sys.platform
    result["windows"] = result["platform"] == "win32"
    result["linux"] = result["platform"].startswith("linux")
    result["mac"] = result["platform"] == "darwin"
    result["release"] = platform.release().lower()
    result["binext"] = ".exe" if result["windows"] else ""

    # Number of bits
    result["bitness"] = (
        "64" if platform.machine().endswith("64") or sys.maxsize > 2**32 else "32"
    )

    # Instruction sets
    try:
        info = ""
        with open("/proc/cpuinfo") as f:
            info = f.read()
        result["popcnt"] = "popcnt" in info
        result["bmi2"] = "bmi2" in info
    except OSError:
        # Logic not fully true
        guess = result["bitness"] == "64"
        result["popcnt"] = guess
        result["bmi2"] = guess
    return result
