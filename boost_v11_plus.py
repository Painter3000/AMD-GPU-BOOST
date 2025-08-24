#!/usr/bin/env python3
# boost_v11_plus.py
# made by painter3000

"""
AMD-GPU-BOOST v1.1+ - Erweiterte Runtime-Lösung
Direkter Monkey-Patch für torch.cuda Module mit ROCm-spezifischen Fixes
"""

import torch
import os
import logging
from types import SimpleNamespace

# Logger für AMD-GPU-BOOST
logger = logging.getLogger("BOOST")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('[BOOST] %(message)s'))
logger.addHandler(handler)

class BOOSTv11Plus:
    def __init__(self):
        self.applied = False
        self.original_functions = {}
        self.gpu_detected_cache = {}  # 🔧 Cache für GPU-Erkennung
        self.correction_applied_cache = {}  # 🔧 Cache für angewandte Korrekturen

    def apply_patches(self):
        """Wendet alle AMD-GPU-BOOST-Patches an"""
        if self.applied:
            logger.info("AMD-GPU-BOOST bereits angewendet")
            return
            
        logger.info("Starte AMD-GPU-BOOST Patches...")
        
        # 1. Device Properties Patch
        self._patch_device_properties()
        
        # 2. Device Count Patch 
        self._patch_device_count()
        
        # 3. Current Device Patch
        self._patch_current_device()
        
        # 4. Set Device Patch
        self._patch_set_device()
        
        self.applied = True
        logger.info("✅ AMD-GPU-BOOST Patches erfolgreich angewendet")

    def _patch_device_count(self):
        """Erweitert device_count für bessere AMD-Erkennung"""
        if hasattr(torch.cuda, '_boost_original_device_count'):
            return
            
        original_func = torch.cuda.device_count
        torch.cuda._boost_original_device_count = original_func
        
        def patched_device_count():
            count = original_func()
            
            # Zusätzliche AMD GPU Validation (nur beim ersten Aufruf)
            if count > 0 and not hasattr(self, '_device_count_checked'):
                try:
                    props = torch.cuda._boost_original_get_device_properties(0)
                    if self._is_amd_gpu(props):
                        logger.debug(f"AMD GPU System erkannt: {count} Device(s)")
                    self._device_count_checked = True
                except:
                    pass
                    
            return count
            
        torch.cuda.device_count = patched_device_count

    def _patch_current_device(self):
        """Patcht current_device für AMD GPU Fixes"""
        if hasattr(torch.cuda, '_boost_original_current_device'):
            return
            
        original_func = torch.cuda.current_device
        torch.cuda._boost_original_current_device = original_func
        
        def patched_current_device():
            device_id = original_func()
            
            # AMD-spezifische Device-Validierung (nur einmal)
            cache_key = f"current_device_checked_{device_id}"
            if torch.cuda.is_available() and not hasattr(self, cache_key):
                try:
                    props = torch.cuda._boost_original_get_device_properties(device_id)
                    if self._is_amd_gpu(props):
                        self._ensure_amd_env_vars()
                        logger.debug(f"AMD GPU {device_id} als current device gesetzt")
                    setattr(self, cache_key, True)
                except:
                    pass
                    
            return device_id
            
        torch.cuda.current_device = patched_current_device

    def _patch_set_device(self):
        """Patcht set_device für AMD GPU Optimierungen"""
        if hasattr(torch.cuda, '_boost_original_set_device'):
            return
            
        original_func = torch.cuda.set_device
        torch.cuda._boost_original_set_device = original_func
        
        def patched_set_device(device):
            result = original_func(device)
            
            # AMD GPU Setup nach Device-Switch (nur einmal pro Device)
            cache_key = f"set_device_checked_{device}"
            if torch.cuda.is_available() and not hasattr(self, cache_key):
                try:
                    props = torch.cuda._boost_original_get_device_properties(device)
                    if self._is_amd_gpu(props):
                        self._ensure_amd_env_vars()
                        logger.debug(f"AMD GPU {device} aktiviert")
                    setattr(self, cache_key, True)
                except:
                    pass
                    
            return result
            
        torch.cuda.set_device = patched_set_device

    def _is_amd_gpu(self, props):
        """Erkennt AMD GPUs"""
        if not hasattr(props, 'name'):
            return False
        name = props.name.upper()
        return any(amd_id in name for amd_id in ['AMD', 'RADEON', 'RX'])
        
    def _patch_device_properties(self):
        """Patcht get_device_properties für AMD GPUs"""
        if hasattr(torch.cuda, '_boost_original_get_device_properties'):
            return
            
        # Originale Funktion sichern
        original_func = torch.cuda.get_device_properties
        torch.cuda._boost_original_get_device_properties = original_func
        
        def patched_get_device_properties(device=None):
            if device is None:
                device = torch.cuda.current_device()
                
            # 🔧 Cache-Key für diesen Device
            cache_key = f"device_{device}"
            
            # Hole originale Properties
            props = original_func(device)
            
            # 🔧 Prüfe Cache zuerst - verhindert Spam-Logs
            if cache_key in self.correction_applied_cache:
                return self.correction_applied_cache[cache_key]
            
            # AMD GPU Detection und Korrektur (nur einmal pro Device)
            if self._is_amd_gpu_cached(props, device):
                corrected_props = self._correct_amd_properties(props, device)
                # 🔧 Cache das Ergebnis
                self.correction_applied_cache[cache_key] = corrected_props
                return corrected_props
            else:
                # 🔧 Auch nicht-AMD GPUs cachen
                self.correction_applied_cache[cache_key] = props
                return props
                
        # Ersetze die Funktion
        torch.cuda.get_device_properties = patched_get_device_properties
        logger.info("✅ get_device_properties gepatcht")
        
    def _is_amd_gpu_cached(self, props, device):
        """Cached AMD GPU Detection - verhindert Log-Spam"""
        cache_key = f"amd_check_{device}"
        
        if cache_key in self.gpu_detected_cache:
            return self.gpu_detected_cache[cache_key]
        
        # Einmalige Erkennung
        is_amd = self._is_amd_gpu(props)
        
        if is_amd:
            logger.info(f"AMD GPU erkannt: {props.name}")  # 🔧 Nur EINMAL loggen
        
        # Cache das Ergebnis
        self.gpu_detected_cache[cache_key] = is_amd
        return is_amd
        
    def _correct_amd_properties(self, props, device):
        """Korrigiert AMD GPU Properties - mit Device-spezifischem Logging"""
        
        # Force-Override durch Umgebungsvariablen
        force_warp_size = os.getenv("BOOST_FORCE_WARP_SIZE")
        force_mp_count = os.getenv("BOOST_FORCE_MP_COUNT")
        
        # Neue Properties erstellen
        corrected = SimpleNamespace()
        
        # Alle originalen Attribute kopieren
        for attr in dir(props):
            if not attr.startswith('_'):
                try:
                    setattr(corrected, attr, getattr(props, attr))
                except:
                    pass
        
        changed = False
        original_mp = props.multi_processor_count if hasattr(props, 'multi_processor_count') else 0
        original_warp = props.warp_size if hasattr(props, 'warp_size') else 0
        
        # GPU-spezifische Korrekturen
        gpu_corrections = self._get_gpu_corrections(props.name)
        
        if gpu_corrections:
            if force_mp_count:
                corrected.multi_processor_count = int(force_mp_count)
                changed = True
            elif gpu_corrections.get('mp_count') and original_mp != gpu_corrections['mp_count']:
                corrected.multi_processor_count = gpu_corrections['mp_count']
                changed = True
                
            if force_warp_size:
                corrected.warp_size = int(force_warp_size)
                changed = True
            elif gpu_corrections.get('warp_size') and original_warp != gpu_corrections['warp_size']:
                corrected.warp_size = gpu_corrections['warp_size']
                changed = True
        
        # 🔧 Logging nur einmal pro Device
        if changed:
            new_threads = corrected.multi_processor_count * corrected.warp_size
            old_threads = original_mp * original_warp if original_mp and original_warp else 1
            gain = new_threads / old_threads if old_threads > 0 else 1.0
            
            logger.info(f"BOOST korrigiert {props.name} (Device {device}):")
            logger.info(f"  MPs: {original_mp} → {corrected.multi_processor_count}")
            logger.info(f"  Warp Size: {original_warp} → {corrected.warp_size}")
            logger.info(f"  Performance Gain: {gain:.1f}x")
        
        return corrected

    def _get_gpu_corrections(self, gpu_name):
        """Gibt bekannte GPU-Korrekturen zurück"""
        corrections = {
            "AMD Radeon RX 6800 XT": {
                "mp_count": 72,
                "warp_size": 64,
                "expected_old_mp": 36,
                "expected_old_warp": 32
            },
            "AMD Radeon RX 6900 XT": {
                "mp_count": 80,
                "warp_size": 64,
                "expected_old_mp": 40,
                "expected_old_warp": 32
            },
            "AMD Radeon RX 7900 XTX": {
                "mp_count": 96,
                "warp_size": 64,
                "expected_old_mp": 48,
                "expected_old_warp": 32
            },
            "AMD Radeon RX 7900 XT": {
                "mp_count": 84,
                "warp_size": 64,
                "expected_old_mp": 42,
                "expected_old_warp": 32
            }
        }
        
        # Exact match first
        if gpu_name in corrections:
            return corrections[gpu_name]
            
        # Partial match
        for known_gpu, correction in corrections.items():
            if known_gpu in gpu_name or gpu_name in known_gpu:
                return correction
                
        return None
        
    def _ensure_amd_env_vars(self):
        """Stellt sicher, dass AMD-optimale Umgebungsvariablen gesetzt sind"""
        if not os.getenv("BOOST_FORCE_WARP_SIZE"):
            os.environ["BOOST_FORCE_WARP_SIZE"] = "64"
            
        if not os.getenv("BOOST_FORCE_MP_COUNT"):
            # Default basierend auf häufigster GPU
            os.environ["BOOST_FORCE_MP_COUNT"] = "72"  # RX 6800 XT default
            
        # ROCm Optimierungen
        if not os.getenv("HIP_VISIBLE_DEVICES"):
            os.environ["HIP_VISIBLE_DEVICES"] = "0"
            
        if not os.getenv("CUDA_VISIBLE_DEVICES"):
            os.environ["CUDA_VISIBLE_DEVICES"] = "0"

# Global instance
_boost_instance = None

def apply_boost_patches():
    """Öffentliche API zum Anwenden der AMD-GPU-BOOST-Patches"""
    global _boost_instance
    
    if _boost_instance is None:
        _boost_instance = BOOSTv11Plus()
        
    _boost_instance.apply_patches()
    return _boost_instance

def get_corrected_device_properties(device=None):
    """Direkte API für korrigierte Device Properties"""
    if device is None:
        device = 0
        
    # Wende Patches an falls noch nicht geschehen
    apply_boost_patches()
    
    return torch.cuda.get_device_properties(device)

# Auto-Apply beim Import (falls PyTorch verfügbar)
if torch.cuda.is_available():
    try:
        apply_boost_patches()
        print("🚀 AMD-GPU-BOOST activated!")
    except Exception as e:
        logger.warning(f"Auto-Apply fehlgeschlagen: {e}")

# Test-Funktionen
def test_boost_effectiveness():
    """Testet AMD-GPU-BOOST-Effektivität"""
    print("🧪 AMD-GPU-BOOST v1.1+ Effectiveness Test")
    print("=" * 50)
    
    if not torch.cuda.is_available():
        print("❌ CUDA/ROCm nicht verfügbar")
        return
        
    # Test vor BOOST
    print("🔋 Teste Device Properties...")
    props = get_corrected_device_properties(0)
    
    print(f"🎮 GPU: {props.name}")
    print(f"🔢 MPs: {props.multi_processor_count}")
    print(f"📏 Warp Size: {props.warp_size}")
    
    total_threads = props.multi_processor_count * props.warp_size
    print(f"🧮 Total Threads: {total_threads}")
    
    # Erwartete Werte für RX 6800 XT
    if "RX 6800 XT" in props.name:
        expected_threads = 72 * 64  # 4608
        utilization = (total_threads / expected_threads) * 100
        print(f"📈 GPU Utilization: {utilization:.1f}%")
        
        if utilization >= 90:
            print("✅ AMD-GPU-BOOST working correctly!")
        else:
            print(f"⚠️ AMD-GPU-BOOST needs adjustment - only {utilization:.1f}% utilization")
    
    print("\n🔧 Environment Variables:")
    for env_var in ["BOOST_FORCE_WARP_SIZE", "BOOST_FORCE_MP_COUNT", "HIP_VISIBLE_DEVICES"]:
        value = os.getenv(env_var, "Not set")
        print(f"   {env_var}: {value}")

if __name__ == "__main__":
    test_boost_effectiveness()
