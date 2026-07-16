from speace_core.cellular_brain.system_assimilation import WindowsSystemAssimilator
from speace_core.cellular_brain.system_assimilation.assimilation_models import SystemAssimilationConfig

a = WindowsSystemAssimilator(config=SystemAssimilationConfig(
    enable_assimilation=True, allow_wmi_queries=True
))
r = a.assimilate()
print("Processes:", r.process_count)
print("Services:", r.service_count)
print("Devices:", r.device_count)
print("Storage:", len(r.storage_devices))
for d in r.storage_devices:
    size = d.get("size_bytes", 0) / (1024**3)
    free = d.get("free_bytes", 0) / (1024**3)
    print(f"  {d.get('device_id','?')}: {free:.1f}GB free / {size:.1f}GB total")
print("Admin:", r.system_info.is_admin)
print("Assimilation OK")
