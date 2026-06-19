"""
Minimal skeleton for the cleaner LogitechDevice + FeatureHandler architecture (TASK-009).

This is the first tiny, low-risk extraction step. The goal is to prove the pattern
works while keeping 100% backward compatibility with all existing mouse, keyboard,
and light behavior.

Only one feature (Litra illumination) is extracted in this initial micro-chunk.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type

from core.hid_discovery import classify_device_kind


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

    # 009.40/009.46: small protected helper for standardized logging of unsupported operations
    def _log_unsupported(self, operation: str, **context) -> None:
        """Standardized logging for unsupported read/write attempts on a handler.

        Replaces ad-hoc print statements across handlers with a consistent format.
        Usage examples:
            self._log_unsupported("write")
            self._log_unsupported("read", device=self.device)
        """
        label = self._get_operation_label(operation) if hasattr(self, "_get_operation_label") else f"{operation} {self._get_friendly_name()}"
        device_key = self._get_device_key_for_log()
        msg = f"[{label}] not supported for device {device_key}"
        if context:
            # Keep it simple and safe; do not assume any particular context keys
            extra = " ".join(f"{k}={v}" for k, v in context.items())
            msg = f"{msg} ({extra})"
        print(msg)

    # 009.43: small optional friendly display name for handlers (used in logging, debug, future UI)
    _friendly_name: str | None = None

    def _get_friendly_name(self) -> str:
        """Return a human-readable name for this handler (for logging/debug/future UI).

        If `_friendly_name` is set on the class, use it. Otherwise derive a reasonable default
        from the class name (e.g., "ReportRateHandler" → "Report Rate").
        """
        if self._friendly_name:
            return self._friendly_name
        name = self.__class__.__name__
        if name.endswith("Handler"):
            name = name[:-7]
        # Insert spaces before uppercase letters (simple camelCase → Title Case)
        friendly = "".join(" " + c if c.isupper() and i > 0 else c for i, c in enumerate(name))
        return friendly.strip() or name

    # 009.46: small helper for standardized friendly labels for successful operations / debug
    def _get_operation_label(self, operation: str) -> str:
        """Return a human-readable label for a common operation on this handler (for logging/debug/future UI).

        Examples:
            handler._get_operation_label("read") → "Read Report Rate"
            handler._get_operation_label("set")  → "Set LED Effect"
        Uses the already-declared friendly name (from 009.43) when available.
        """
        friendly = self._get_friendly_name()
        op = operation.strip().capitalize() if operation else "Operation"
        return f"{op} {friendly}"

    # 009.49: small protected helper for standardized device identifier in logging/debug
    def _get_device_key_for_log(self) -> str:
        """Return a best-effort stable identifier for this handler's device (for logging and debug).

        Prefers the device's .key if present, then falls back to product_id, then "unknown".
        This centralizes ad-hoc getattr(device, "key") / product_id patterns across handlers.
        """
        if self.device is None:
            return "unknown"
        key = getattr(self.device, "key", None)
        if key:
            return str(key)
        return str(getattr(self.device, "product_id", "unknown"))


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
            # 009.32/009.40: safe default + standardized logging for write-only handlers
            self._log_unsupported("read")
            return None
        if self._read_method_name is None:
            raise NotImplementedError("SimpleDelegationHandler: _read_method_name not set and handle_read() not overridden")
        method = self._get_listener_attr(self._read_method_name)
        if method is None:
            raise AttributeError(f"Listener has no method named {self._read_method_name}")
        return method(*args, **kwargs)

    def handle_write(self, *args, **kwargs) -> Any:
        if getattr(self, "_read_only", False):
            # 009.32/009.40: safe default + standardized logging for read-only handlers
            self._log_unsupported("write")
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

    For a read-only handler (using the declarative marker):

        class MyReadOnlyHandler(RecommendedThinHandler):
            def __init__(self, device, listener):
                super().__init__(device, listener,
                                 feature_index_attr="_my_idx",
                                 read_method="read_my")
                self._mark_as_read_only()

    Using the declarative helper (alternative style):

        class MyFeatureHandler(RecommendedThinHandler):
            def __init__(self, device, listener):
                super().__init__(device, listener)
                self._declare_attributes(
                    feature_index_attr="_my_idx",
                    read_method="read_my",
                    write_method="set_my"
                )

    Handlers can still override methods if custom logic is needed.

    Full Recommended Pattern for a Brand-New Thin Handler (current best practice):

        class MyFeatureHandler(RecommendedThinHandler):
            '''Example of the full modern recommended shape (009.33-009.50).'''

            def __init__(self, device, listener):
                super().__init__(device, listener,
                                 feature_index_attr="_my_idx",
                                 read_method="read_my",
                                 write_method="set_my")
                # For one-way handlers:
                # self._mark_as_read_only()   # or _mark_as_write_only()

            # Optional: safe attribute access from the listener
            # def _get_something(self):
            #     return self._get_listener_attr("_some_listener_attr")

            # The helpers below are automatically available for consistent logging/debug:
            #   self._get_friendly_name()
            #   self._get_operation_label("read")
            #   self._get_success_label("read")
            #   self._get_device_key_for_log()     # stable device identifier for logs
            #   self._log_unsupported("write")

    Existing handlers can continue to inherit directly from `DefaultThinHandler`,
    `ThinDelegationHandler`, or `FeatureHandler` if they need custom logic.
    """

    # No additional implementation required — the value is the clear
    # recommended shape + the bundled patterns from the preceding refinements.
    pass


class UltraThinHandler(RecommendedThinHandler):
    """Ultra-light convenience base for the absolute simplest thin handlers (009.38).

    This class inherits from `RecommendedThinHandler` and is intended for the most
    common, pure thin-delegation cases where the handler is literally just a
    one-to-one forwarder to a listener method (plus the reusable `is_supported()`
    check).

    For the absolute simplest handler, the declaration can be extremely concise:

        class MyUltraSimpleHandler(UltraThinHandler):
            def __init__(self, device, listener):
                super().__init__(device, listener,
                                 feature_index_attr="_my_idx",
                                 read_method="read_my",
                                 write_method="set_my")

    Or (for read-only ultra-simple cases):

        class MyUltraSimpleReadOnlyHandler(UltraThinHandler):
            def __init__(self, device, listener):
                super().__init__(device, listener,
                                 feature_index_attr="_my_idx",
                                 read_method="read_my")
                self._mark_as_read_only()

    Existing handlers can continue to inherit from `RecommendedThinHandler`,
    `DefaultThinHandler`, `ThinDelegationHandler`, or `FeatureHandler` if they
    need more flexibility or custom logic.
    """

    # No additional implementation required — the value is the even more
    # concise shape for the absolute simplest pure thin cases.
    pass


class LogitechDevice:
    """Very lightweight base for a Logitech HID++ device.

    Over time this will hold identity, a collection of FeatureHandlers,
    per-device state, etc. For now it is deliberately minimal.
    """

    kind: str = "unknown"

    def __init__(self, product_id: int, name: str = "", key: Optional[str] = None):
        self.product_id = product_id
        self.name = name
        self.key = key or str(product_id)
        self._handlers: Dict[str, FeatureHandler] = {}
        self._listener: Any = None
        self._cfg: Optional[dict] = None

    def add_handler(self, name: str, handler: FeatureHandler) -> None:
        self._handlers[name] = handler

    def get_handler(self, name: str) -> Optional[FeatureHandler]:
        return self._handlers.get(name)

    def has_handler(self, name: str) -> bool:
        return name in self._handlers


class MouseDevice(LogitechDevice):
    """Logitech mouse (DPI, SmartShift, gestures, etc.)."""

    kind = "mouse"


class KeyboardDevice(LogitechDevice):
    """Logitech keyboard (backlight, FN inversion, etc.)."""

    kind = "keyboard"


class OtherDevice(LogitechDevice):
    """Non-mouse, non-keyboard Logitech devices (Litra Beam, webcams, etc.)."""

    kind = "other"


_DEVICE_KIND_CLASSES: Dict[str, Type[LogitechDevice]] = {
    "mouse": MouseDevice,
    "keyboard": KeyboardDevice,
    "other": OtherDevice,
}


def _normalize_product_id(value: Any, default: int = 0) -> Any:
    """Coerce product_id to int when possible; preserve legacy non-numeric values."""
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _device_kind_from_identity(identity: Any) -> Optional[str]:
    """Read a pre-classified device_kind from a dict or tuple identity block."""
    if not identity:
        return None
    if isinstance(identity, dict):
        kind = identity.get("device_kind")
        return str(kind) if kind else None
    try:
        kind = dict(identity).get("device_kind")
        return str(kind) if kind else None
    except (TypeError, ValueError):
        return None


def _discovered_feature_ids_from_listener(listener: Any) -> set[int]:
    """Best-effort feature-id set from a HID++ listener for classify_device_kind."""
    if listener is None:
        return set()
    if hasattr(listener, "_discovered_feature_ids"):
        try:
            return {int(fid) for fid in listener._discovered_feature_ids()}
        except Exception:
            pass
    if hasattr(listener, "_discovered_feature_inventory"):
        try:
            inv = listener._discovered_feature_inventory()
            return {
                int(entry["feature_id"])
                for entry in inv
                if entry.get("feature_id") is not None
            }
        except Exception:
            pass
    return set()


def _resolve_device_kind(
    kind: Optional[str],
    listener: Any,
    *,
    product_id: int = 0,
    name: str = "",
    product_name: Optional[str] = None,
) -> str:
    """Resolve device kind from an explicit string or listener/capability signals."""
    if kind:
        return kind

    dev = getattr(listener, "connected_device", None) if listener is not None else None
    if dev is not None:
        inventory = getattr(dev, "capability_inventory", None)
        if inventory is not None:
            cached = _device_kind_from_identity(getattr(inventory, "device_identity", None))
            if cached and cached != "unknown":
                return cached

    pid = _normalize_product_id(product_id, 0)
    if not pid and dev is not None:
        pid = _normalize_product_id(getattr(dev, "product_id", 0), 0)

    pname = product_name or name
    if not pname and dev is not None:
        pname = (
            getattr(dev, "product_name", None)
            or getattr(dev, "display_name", None)
            or ""
        )

    feats = _discovered_feature_ids_from_listener(listener)
    return classify_device_kind(pid, pname, None, feats)


def create_logitech_device(
    kind: Optional[str],
    listener: Any,
    cfg: Optional[dict],
    **kwargs: Any,
) -> LogitechDevice:
    """Create the appropriate LogitechDevice subclass for the device kind.

    When ``kind`` is omitted, classification uses ``classify_device_kind`` with
    identity and capability signals from ``listener`` (and optional kwargs).
    """
    product_id = _normalize_product_id(kwargs.get("product_id", 0), 0)
    resolved_kind = _resolve_device_kind(
        kind,
        listener,
        product_id=product_id,
        name=str(kwargs.get("name", "") or ""),
        product_name=kwargs.get("product_name"),
    )
    cls = _DEVICE_KIND_CLASSES.get(resolved_kind, LogitechDevice)
    name = str(kwargs.get("name", "") or "")
    key = kwargs.get("key")
    device = cls(product_id, name, key)
    device._listener = listener
    device._cfg = cfg
    if cls is LogitechDevice:
        device.kind = resolved_kind
    return device


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
    device = create_logitech_device(
        kind=None,
        listener=listener,
        cfg=cfg,
        product_id=pid,
        name=name,
        key=key,
    )

    try:
        handler = handler_cls(device, listener)
        device.add_handler(handler_name, handler)
        return device
    except Exception:
        return None
