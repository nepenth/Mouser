"""
Minimal skeleton for the cleaner LogitechDevice + FeatureHandler architecture (TASK-009).

This is the first tiny, low-risk extraction step. The goal is to prove the pattern
works while keeping 100% backward compatibility with all existing mouse, keyboard,
and light behavior.

Only one feature (Litra illumination) is extracted in this initial micro-chunk.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class FeatureHandler:
    """Base class for a single HID++ feature handler.

    Concrete handlers implement the actual read/write logic for one feature
    (e.g., Litra illumination, Battery, SmartShift, etc.).

    009.10: Added a reusable default `is_supported()` implementation based on
    a class attribute `_feature_index_attr` (the name of the listener attribute
    that holds the feature index). Handlers can still override if they need
    custom logic.
    """

    # Optional: name of the listener attribute that holds the feature index
    # (e.g. "_report_rate_idx", "_battery_idx"). If set, the default
    # is_supported() implementation will use it.
    _feature_index_attr: str | None = None

    def __init__(self, device: "LogitechDevice"):
        self.device = device

    def is_supported(self) -> bool:
        """Return True if this feature is present on the device.

        Default implementation (009.10): checks whether the listener attribute
        named in `_feature_index_attr` is not None. Override for custom logic.
        """
        if self._feature_index_attr is None:
            # No default attribute declared — subclasses must override.
            return False
        listener = getattr(self, "listener", None) or getattr(self.device, "_listener", None)
        if listener is None:
            # Fallback: look for the attribute on self (some handlers store it directly)
            listener = self
        return getattr(listener, self._feature_index_attr, None) is not None

    def handle_read(self, *args, **kwargs) -> Any:
        """Perform a read operation for this feature."""
        raise NotImplementedError

    def handle_write(self, *args, **kwargs) -> Any:
        """Perform a write operation for this feature."""
        raise NotImplementedError

    # 009.14: small protected helper for safe listener attribute access
    def _get_listener_attr(self, attr_name: str, default: Any = None) -> Any:
        """Safely retrieve an attribute from the listener (or self if stored there).

        Returns `default` if the attribute is missing. This centralizes direct
        getattr(self.listener, ...) calls and makes future changes safer.
        """
        listener = getattr(self, "listener", None)
        if listener is None:
            # Some handlers store attributes directly on self
            listener = self
        return getattr(listener, attr_name, default)


class SimpleDelegationHandler(FeatureHandler):
    """Lightweight base for handlers that are essentially thin wrappers around listener methods (009.12).

    Subclasses can declare:
        _read_method_name = "read_xxx"
        _write_method_name = "set_xxx"

    The default handle_read() / handle_write() will then forward to self.listener.<method>(*args, **kwargs).

    Handlers that need custom logic can still override the methods or inherit directly from FeatureHandler.
    """

    _read_method_name: str | None = None
    _write_method_name: str | None = None

    def handle_read(self, *args, **kwargs) -> Any:
        if self._read_method_name is None:
            raise NotImplementedError("SimpleDelegationHandler: _read_method_name not set and handle_read() not overridden")
        method = self._get_listener_attr(self._read_method_name)
        if method is None:
            raise AttributeError(f"Listener has no method named {self._read_method_name}")
        return method(*args, **kwargs)

    def handle_write(self, *args, **kwargs) -> Any:
        if self._write_method_name is None:
            raise NotImplementedError("SimpleDelegationHandler: _write_method_name not set and handle_write() not overridden")
        method = self._get_listener_attr(self._write_method_name)
        if method is None:
            raise AttributeError(f"Listener has no method named {self._write_method_name}")
        return method(*args, **kwargs)


class LogitechDevice:
    """Very lightweight base for a Logitech HID++ device.

    Over time this will hold identity, a collection of FeatureHandlers,
    per-device state, etc. For now it is deliberately minimal.
    """

    def __init__(self, product_id: int, name: str = "", key: Optional[str] = None):
        self.product_id = product_id
        self.name = name
        self.key = key or str(product_id)
        self._handlers: Dict[str, FeatureHandler] = {}

    def add_handler(self, name: str, handler: FeatureHandler) -> None:
        self._handlers[name] = handler

    def get_handler(self, name: str) -> Optional[FeatureHandler]:
        return self._handlers.get(name)

    def has_handler(self, name: str) -> bool:
        return name in self._handlers


def maybe_attach_handler(
    listener: Any,
    handler_cls: type,
    cfg: Optional[dict],
    device_key_fallback: Optional[str] = None,
    device_name_fallback: Optional[str] = None,
    product_id_fallback: Optional[int] = None,
    feature_attr: str = "_xxx_idx",   # e.g. "_litra_illumination_idx"
    handler_name: str = "xxx",        # e.g. "litra_illumination"
) -> Optional["LogitechDevice"]:
    """Tiny reusable helper for lazy FeatureHandler attachment (009.6).

    Returns the (possibly newly created) LogitechDevice with the handler attached,
    or None if attachment was not possible / not needed.
    """
    if not (handler_cls and listener and cfg is not None):
        return None

    # Check if the feature is present on this listener
    if getattr(listener, feature_attr, None) is None:
        return None

    # Build a minimal device key / identity
    dev = getattr(listener, "connected_device", None)
    pid = getattr(dev, "product_id", 0) if dev else (product_id_fallback or 0)
    name = getattr(dev, "name", device_name_fallback or "Device") if dev else (device_name_fallback or "Device")
    key = getattr(dev, "key", None) if dev else device_key_fallback or str(pid)

    # Create or reuse a device object on the listener for attachment bookkeeping
    # (Engine will cache the device; here we just create a transient one for the handler)
    device = LogitechDevice(pid, name, key)

    try:
        handler = handler_cls(device, listener)
        device.add_handler(handler_name, handler)
        return device
    except Exception:
        return None
