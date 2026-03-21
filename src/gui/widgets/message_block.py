import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QTimer, QUrl
import tempfile


class MessageBlock(QWidget):
    """Message bubble with KaTeX-rendered math (including mhchem) using QWebEngineView."""

    def __init__(self, text: str, role: str = "system"):
        super().__init__()

        self.role = role
        self._current_text = text

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        self.web = QWebEngineView(self)
        self.web.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        # Enable local JS execution (required for KaTeX)
        settings = self.web.settings()
        settings.setAttribute(settings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(settings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(settings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(settings.WebAttribute.JavascriptCanOpenWindows, True)
        settings.setAttribute(settings.WebAttribute.AllowRunningInsecureContent, True)

        self.web.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.web.setFixedHeight(40)

        layout.addWidget(self.web)

        self._render_html(text)
        self.web.loadFinished.connect(self._update_height)

    # --------------------------------------------------------------
    # Rendering
    # --------------------------------------------------------------

    def _render_html(self, text: str):
        """Render the message text using KaTeX (inline + block math + mhchem)."""

        base_dir = os.path.dirname(os.path.abspath(__file__))
        katex_dir = os.path.abspath(os.path.join(base_dir, "..", "katex"))

        katex_css = f"file:///{katex_dir}/katex.min.css".replace("\\", "/")
        katex_js = f"file:///{katex_dir}/katex.min.js".replace("\\", "/")
        mhchem_js = f"file:///{katex_dir}/mhchem.min.js".replace("\\", "/")
        autorender_js = f"file:///{katex_dir}/auto-render.min.js".replace("\\", "/")

        safe_text = self._escape_html(text)

        # DOCTYPE must be at column 0
        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="{katex_css}">
<script src="{katex_js}"></script>
<script src="{mhchem_js}"></script>
<script src="{autorender_js}"></script>
<style>
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 16px;
    margin: 0;
    padding: 0;
    color: {self._color_for_role()};
}}
.bubble {{
    padding: 4px;
    white-space: pre-wrap;
    word-wrap: break-word;
}}
</style>
</head>
<body>
<div class="bubble">{safe_text}</div>
<script>
renderMathInElement(document.body, {{
    delimiters: [
        {{left:"$$", right:"$$", display:true}},
        {{left:"$", right:"$", display:false}},
        {{left:"\\\\(", right:"\\\\)", display:false}},
        {{left:"\\\\[", right:"\\\\]", display:true}}
    ]
}});
setTimeout(() => {{ document.title = "render-complete"; }}, 20);
</script>
</body>
</html>
"""


        # Load HTML from a temporary file so QtWebEngine executes JS
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        tmp.write(html.encode("utf-8"))
        tmp.flush()

        self.web.load(QUrl.fromLocalFile(tmp.name))

    # --------------------------------------------------------------
    # Auto-resize logic
    # --------------------------------------------------------------

    def _update_height(self):
        QTimer.singleShot(50, self._compute_height)

    def _compute_height(self):
        js = "document.body.scrollHeight"
        self.web.page().runJavaScript(js, self._apply_height)

    def _apply_height(self, height):
        if height and height > 0:
            self.web.setFixedHeight(height + 10)
            self.updateGeometry()

    # --------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------

    def _escape_html(self, text: str) -> str:
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
        )

    def _color_for_role(self):
        if self.role == "user":
            return "#007aff"
        elif self.role == "assistant":
            return "#34c759"
        return "black"

    # --------------------------------------------------------------
    # Streaming support
    # --------------------------------------------------------------

    def set_text(self, text: str):
        self._current_text = text
        self._render_html(text)

    def sizeHint(self):
        return self.web.sizeHint()
