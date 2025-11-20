#!/usr/bin/env python3
"""
Device Mapper Utility
Resolves /dev/serial/by-id symlinks to actual device paths
"""

import os
import glob
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def resolve_device_symlink(symlink_path):
    """
    Resolve a symlink to its actual device path.
    
    Args:
        symlink_path: Path to the symlink (e.g., /dev/serial/by-id/usb-1a86_USB_Serial-if00-port0)
    
    Returns:
        Resolved device path (e.g., /dev/ttyUSB0) or None if not found
    """
    try:
        if os.path.islink(symlink_path):
            # Resolve the symlink
            resolved = os.path.realpath(symlink_path)
            logger.info(f"Resolved {symlink_path} -> {resolved}")
            return resolved
        elif os.path.exists(symlink_path):
            # It's a direct device path, return as-is
            logger.info(f"Direct device path: {symlink_path}")
            return symlink_path
        else:
            logger.warning(f"Device not found: {symlink_path}")
            return None
    except Exception as e:
        logger.error(f"Error resolving {symlink_path}: {e}")
        return None

def find_all_serial_devices():
    """
    Find all available serial devices on the system.
    
    Returns:
        Dictionary mapping device paths to their by-id symlinks (if any)
    """
    devices = {}
    
    # Check /dev/serial/by-id for stable identifiers
    by_id_path = Path("/dev/serial/by-id")
    if by_id_path.exists():
        for symlink in by_id_path.iterdir():
            if symlink.is_symlink():
                try:
                    resolved = os.path.realpath(str(symlink))
                    devices[resolved] = str(symlink)
                    logger.info(f"Found device: {resolved} (by-id: {symlink.name})")
                except Exception as e:
                    logger.error(f"Error processing {symlink}: {e}")
    
    # Also check for direct device paths
    for pattern in ["/dev/ttyUSB*", "/dev/ttyACM*", "/dev/ttyS*"]:
        for device in glob.glob(pattern):
            if device not in devices:
                devices[device] = None
                logger.info(f"Found device: {device} (no by-id)")
    
    return devices

def get_device_from_config(config_device):
    """
    Convert a device specification from config to actual device path.
    Handles both direct paths and by-id symlinks.
    
    Args:
        config_device: Device path from configuration (can be direct or by-id)
    
    Returns:
        Actual device path or None if not found
    """
    # If it's a by-id path pattern, try to find matching device
    if "by-id" in config_device:
        # User may have specified the full path or just the directory
        if config_device == "/dev/serial/by-id":
            # Return all by-id devices
            devices = find_all_serial_devices()
            by_id_devices = [dev for dev, symlink in devices.items() if symlink]
            if by_id_devices:
                logger.info(f"Found {len(by_id_devices)} by-id devices")
                return by_id_devices[0]  # Return the first one
            return None
        else:
            # Specific by-id path
            return resolve_device_symlink(config_device)
    else:
        # Direct device path
        if os.path.exists(config_device):
            return config_device
        else:
            logger.warning(f"Device not found: {config_device}")
            return None

def map_config_device(config_device, prefer_by_id=False):
    """
    Map a device from config to an actual usable device path.
    
    Args:
        config_device: Device specification from config
        prefer_by_id: If True, return by-id path if available
    
    Returns:
        Tuple of (actual_device_path, by_id_path)
    """
    if "by-id" in config_device:
        # Find the first available serial device
        devices = find_all_serial_devices()
        if devices:
            actual_path = list(devices.keys())[0]
            by_id_path = devices[actual_path]
            logger.info(f"Mapped by-id request to: {actual_path}")
            return (actual_path, by_id_path)
        return (None, None)
    else:
        # Direct path - check if it has a by-id equivalent
        resolved = resolve_device_symlink(config_device)
        if resolved:
            devices = find_all_serial_devices()
            by_id = devices.get(resolved)
            return (resolved, by_id)
        return (None, None)

if __name__ == "__main__":
    # Test the device mapper
    logging.basicConfig(level=logging.INFO)
    
    print("\n=== Available Serial Devices ===")
    devices = find_all_serial_devices()
    for device, by_id in devices.items():
        if by_id:
            print(f"{device} -> {by_id}")
        else:
            print(f"{device}")
    
    print("\n=== Testing Device Resolution ===")
    test_paths = [
        "/dev/ttyUSB0",
        "/dev/serial/by-id",
        "/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0"
    ]
    
    for path in test_paths:
        if os.path.exists(path):
            actual, by_id = map_config_device(path)
            print(f"\nConfig: {path}")
            print(f"  Actual: {actual}")
            print(f"  By-ID:  {by_id or 'N/A'}")
