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

    # 009.32: small declarative support for read-only / write-only handlers
    _read_only: bool = False
    _write_only: bool = False

    def _mark_as_read_only(self) -> None:
        """Mark this handler as read-only (009.32). handle_write will use a safe default."""
        self._read_only = True
        self._write_only = False

    def _mark_as_write_only(self) -> None:
        """Mark this handler as write-only (009.32). handle_read will use a safe default."""
        self._write_only = True
        self._read_only = False


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
        if getattr(self, "_write_only", False):
            # 009.32: safe default for write-only handlers
            return None
        if self._read_method_name is None:
            raise NotImplementedError("SimpleDelegationHandler: _read_method_name not set and handle_read() not overridden")
        method = self._get_listener_attr(self._read_method_name)
        if method is None:
            raise AttributeError(f"Listener has no method named {self._read_method_name}")
        return method(*args, **kwargs)

    def handle_write(self, *args, **kwargs) -> Any:
        if getattr(self, "_read_only", False):
            # 009.32: safe default for read-only handlers
            return False
        if self._write_method_name is None:
            raise NotImplementedError("SimpleDelegationHandler: _write_method_name not set and handle_write() not overridden")
        method = self._get_listener_attr(self._write_method_name)
        if method is None:
            raise AttributeError(f"Listener has no method named {self._write_method_name}")
        return method(*args, **kwargs)


class ThinDelegationHandler(SimpleDelegationHandler):
    """Convenience base for the most common thin delegation handlers (009.25).

    The majority of our extracted handlers are simple read/write (or read-only)
    wrappers around a listener method. This class makes the declaration even more
    concise while still inheriting all the reusable defaults from
    SimpleDelegationHandler and FeatureHandler (_feature_index_attr support,
    is_supported(), _get_listener_attr, etc.).

    Typical usage for a new thin handler:

        class MyFeatureHandler(ThinDelegationHandler):
            _feature_index_attr = "_my_feature_idx"
            _read_method_name = "read_my_feature"
            _write_method_name = "set_my_feature"   # or None for read-only

    Existing handlers can continue to inherit directly from SimpleDelegationHandler
    or FeatureHandler if they need custom logic.

    009.27: Added optional _declare_attributes(...) helper for even more concise
    single-statement declaration of the three standard attributes.
    """

    def _declare_attributes(self, feature_index_attr: str | None = None,
                            read_method: str | None = None,
                            write_method: str | None = None) -> None:
        """Small declarative helper (009.27) for the three standard thin-handler attributes.

        This is optional. Handlers may still assign the attributes directly.
        """
        if feature_index_attr is not None:
            self._feature_index_attr = feature_index_attr
        if read_method is not None:
            self._read_method_name = read_method
        if write_method is not None:
            self._write_method_name = write_method


class DefaultThinHandler(ThinDelegationHandler):
    """Ultra-light convenience base for the simplest thin delegation handlers (009.29).

    This class combines the reusable patterns we have already developed:
    - ThinDelegationHandler defaults (delegation via _read_method_name / _write_method_name)
    - Reusable is_supported() via _feature_index_attr
    - _get_listener_attr safety
    - _declare_attributes helper (009.27)

    Subclasses can be written with almost zero boilerplate:

        class MyFeatureHandler(DefaultThinHandler):
            def __init__(self, device, listener):
                super().__init__(device, listener,
                                 feature_index_attr="_my_idx",
                                 read_method="read_my",
                                 write_method="set_my")

    Or (if the base is extended with auto-detection in a future micro-chunk) even less.

    Existing handlers can continue to inherit directly from ThinDelegationHandler
    or FeatureHandler if they need custom logic.
    """

    def __init__(self, device: "LogitechDevice", listener: Any,
                 feature_index_attr: str | None = None,
                 read_method: str | None = None,
                 write_method: str | None = None):
        super().__init__(device)
        self.listener = listener
        # Auto-register via the declarative helper (supports both explicit args
        # and class attributes already present on the subclass).
        fi = feature_index_attr or getattr(self, "_feature_index_attr", None)
        rm = read_method or getattr(self, "_read_method_name", None)
        wm = write_method or getattr(self, "_write_method_name", None)
        if fi or rm or wm:
            self._declare_attributes(
                feature_index_attr=fi,
                read_method=rm,
                write_method=wm
            )


class RecommendedThinHandler(DefaultThinHandler):
    """Recommended starting point for the simplest thin delegation handlers (009.33).

    This class bundles the best practices and reusable patterns developed across
    TASK-009:

    - Reusable `is_supported()` via `_feature_index_attr`
    - Thin delegation via `_read_method_name` / `_write_method_name`
    - `_get_listener_attr(...)` safety
    - Declarative `_declare_attributes(...)` helper (009.27)
    - Automatic respect for `_read_only` / `_write_only` markers (009.32)

    Recommended usage for a brand-new simple handler:

        class MyFeatureHandler(RecommendedThinHandler):
            def __init__(self, device, listener):
                super().__init__(device, listener,
                                 feature_index_attr="_my_idx",
                                 read_method="read_my",
                                 write_method="set_my")

    Or (for read-only cases):

        class MyReadOnlyHandler(RecommendedThinHandler):
            def __init__(self, device, listener):
                super().__init__(device, listener,
                                 feature_index_attr="_my_idx",
                                 read_method="read_my")
                self._mark_as_read_only()

    Existing handlers can continue to inherit directly from `DefaultThinHandler`,
    `ThinDelegationHandler`, or `FeatureHandler` if they need custom logic.

    Recommended Usage (minimal boilerplate for a new simple thin handler):

        class MyFeatureHandler(RecommendedThinHandler):
            def __init__(self, device, listener):
                super().__init__(device, listener,
                                 feature_index_attr="_my_idx",
                                 read_method="read_my",
                                 write_method="set_my")

    For a read-only handler:

        class MyReadOnlyHandler(RecommendedThinHandler):
            def __init__(self, device, listener):
                super().__init__(device, listener,
                                 feature_index_attr="_my_idx",
                                 read_method="read_my")
                self._mark_as_read_only()
    """

    # No additional implementation required — the value is the clear
    # recommended shape + the bundled patterns from the preceding refinements.
    pass


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
