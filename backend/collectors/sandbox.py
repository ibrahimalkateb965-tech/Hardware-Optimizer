from typing import Any, Dict
from datetime import datetime, timezone

def get_sandbox_profile(profile_name: str = "default") -> Dict[str, Any]:
    """Returns deterministic synthetic hardware inventories for sandbox testing."""
    now_str = datetime.now(timezone.utc).isoformat()
    
    if profile_name == "misconfigured_desktop":
        return {
            "CollectedAt": now_str,
            "OperatingSystem": {"Caption": "Microsoft Windows 11 Pro", "Version": "10.0.22631", "OSArchitecture": "64-bit"},
            "ComputerSystem": {"Model": "Custom Desktop PC", "TotalPhysicalMemory": 34359738368},
            "CPU": {
                "Details": {"Name": "AMD Ryzen 9 5900X 12-Core Processor", "NumberOfCores": 12, "NumberOfLogicalProcessors": 24},
                "ActivePowerScheme": "Power Scheme GUID: [GUID] (Balanced)",
                "StartupAppsCount": 24
            },
            "GPU": {
                "Controllers": [{"Name": "NVIDIA GeForce RTX 3080", "AdapterRAM": 10737418240, "DriverVersion": "31.0.15.5244"}],
                "HAGSMode": 1,  # Disabled
                "GameModeEnabled": 0
            },
            "RAM": {
                "TotalModules": 1,  # Single channel
                "Modules": [{"DeviceLocator": "DIMM 0", "Capacity": 34359738368, "Speed": 3600, "ConfiguredClockSpeed": 2133}], # XMP off
                "PageFiles": [{"Name": "C:\\pagefile.sys", "AllocatedBaseSize": 4096}],
                "MemoryManagement": {"MemoryCompression": False}
            },
            "Storage": {
                "TrimStatusRaw": "NTFS DisableDeleteNotify = 1",  # TRIM Disabled
                "Disks": [{"FriendlyName": "Samsung SSD 980 PRO 1TB", "MediaType": "SSD", "BusType": "NVMe", "Size": 1000204886016, "HealthStatus": "Healthy"}],
                "Volumes": [{"DriveLetter": "C", "SizeRemaining": 25000000000, "Size": 1000204886016}]
            },
            "PowerThermal": {
                "Battery": None,
                "ThermalZones": None,
                "PowerPlansRaw": "High Performance and Balanced available"
            }
        }
    
    # Default Profile (Dell G3 3500 verified sample)
    return {
        "CollectedAt": now_str,
        "OperatingSystem": {
            "Caption": "Microsoft Windows 11 Pro",
            "Version": "10.0.26300",
            "OSArchitecture": "64-bit",
            "TotalVisibleMemorySize": 16565952,
            "FreePhysicalMemory": 1403952
        },
        "ComputerSystem": {
            "Model": "G3 3500",
            "TotalPhysicalMemory": 16963534848,
            "NumberOfLogicalProcessors": 12
        },
        "CPU": {
            "Details": {
                "Name": "Intel(R) Core(TM) i7-10750H CPU @ 2.60GHz",
                "NumberOfCores": 6,
                "NumberOfLogicalProcessors": 12,
                "MaxClockSpeed": 2592
            },
            "ActivePowerScheme": "Power Scheme GUID: [GUID] (Balanced)",
            "StartupAppsCount": 18
        },
        "GPU": {
            "Controllers": [
                {"Name": "NVIDIA GeForce GTX 1650", "AdapterRAM": 4293918720, "DriverVersion": "32.0.15.7700"},
                {"Name": "Intel(R) UHD Graphics", "AdapterRAM": 1073741824, "DriverVersion": "31.0.101.2125"}
            ],
            "HAGSMode": None,
            "GameModeEnabled": None
        },
        "RAM": {
            "TotalModules": 2,
            "Modules": [
                {"DeviceLocator": "DIMM A", "Capacity": 8589934592, "Speed": 3200, "ConfiguredClockSpeed": 2933},
                {"DeviceLocator": "DIMM B", "Capacity": 8589934592, "Speed": 3200, "ConfiguredClockSpeed": 2933}
            ],
            "PageFiles": [{"Name": "C:\\pagefile.sys", "AllocatedBaseSize": 4096}],
            "MemoryManagement": {"MemoryCompression": True}
        },
        "Storage": {
            "TrimStatusRaw": "NTFS DisableDeleteNotify = 0",
            "Disks": [
                {"FriendlyName": "IM2P33F3 NVMe ADATA 256GB", "MediaType": "SSD", "BusType": "NVMe", "Size": 256060514304, "HealthStatus": "Healthy"},
                {"FriendlyName": "ST1000LM035-1RK172", "MediaType": "HDD", "BusType": "SATA", "Size": 1000204886016, "HealthStatus": "Healthy"}
            ],
            "Volumes": [
                {"DriveLetter": "C", "FileSystemType": "NTFS", "SizeRemaining": 11093884928, "Size": 253337849856},
                {"DriveLetter": "D", "FileSystemType": "NTFS", "SizeRemaining": 16568627200, "Size": 249561083904}
            ]
        },
        "PowerThermal": {
            "Battery": {"EstimatedChargeRemaining": 100, "BatteryStatus": 2},
            "ThermalZones": None,
            "PowerPlansRaw": "Existing Power Schemes (* Active) (Balanced) *"
        }
    }
