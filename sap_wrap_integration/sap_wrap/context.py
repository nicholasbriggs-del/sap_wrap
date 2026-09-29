from __future__ import annotations

from typing import Any, Iterable

from frappe.model.document import Document


class DocumentTemplateProxy:
    """Lightweight proxy that turns None values into empty strings for templates."""

    __slots__ = ("_doc",)

    def __init__(self, doc: Document):
        object.__setattr__(self, "_doc", doc)

    def __getattr__(self, attr: str) -> Any:
        try:
            value = getattr(self._doc, attr)
        except AttributeError as exc:
            # fallback for dynamically added fields (e.g. workflow_state)
            if hasattr(self._doc, "get"):
                value = self._doc.get(attr)
            else:
                raise exc
        if callable(value):
            return value
        return _sanitize_value(value)

    def __getitem__(self, key: str) -> Any:
        if not hasattr(self._doc, "get"):
            raise KeyError(key)
        value = self._doc.get(key)
        if value is None:
            return ""
        return _sanitize_value(value)

    def __iter__(self) -> Iterable[str]:
        return iter(self._doc.as_dict())

    def get(self, key: str, default: Any = None) -> Any:
        value = self._doc.get(key)
        if value is None:
            return default if default is not None else ""
        return _sanitize_value(value)

    def as_dict(self) -> dict[str, Any]:
        return _sanitize_value(self._doc.as_dict())

    def items(self):
        return self.as_dict().items()

    def keys(self):
        return self.as_dict().keys()

    def values(self):
        return self.as_dict().values()

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<DocumentTemplateProxy {self._doc}>"


def _sanitize_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, Document):
        return wrap_doc_for_template(value)
    if isinstance(value, list):
        return [_sanitize_value(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_value(v) for v in value)
    if isinstance(value, dict):
        return {k: _sanitize_value(v) for k, v in value.items()}
    return value


def wrap_doc_for_template(doc: Document | None) -> DocumentTemplateProxy | None:
    if doc is None:
        return None
    if isinstance(doc, DocumentTemplateProxy):
        return doc
    return DocumentTemplateProxy(doc)
