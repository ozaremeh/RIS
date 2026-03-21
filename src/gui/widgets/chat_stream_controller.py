from PyQt6.QtWidgets import QApplication

from gui.widgets.message_block import MessageBlock


class ChatStreamController:
    """
    Streaming controller for the QScrollArea + QVBoxLayout chat UI.

    Behavior:
    - When assistant starts responding: jump to TOP of the new block.
    - While streaming: DO NOT auto-scroll.
    - After streaming: DO NOT auto-scroll.
    - User may scroll manually at any time.
    """

    def __init__(self, message_layout, typing_start, typing_stop, scroll_area):
        self.message_layout = message_layout
        self._typing_start = typing_start
        self._typing_stop = typing_stop
        self.scroll_area = scroll_area

        self._current_block = None
        self._current_text = ""

    # --------------------------------------------------------------
    # Assistant block lifecycle
    # --------------------------------------------------------------

    def start_assistant_block(self):
        """Create a new assistant message block for streaming."""
        self._current_text = "Assistant: "
        block = MessageBlock(self._current_text, role="assistant")

        # Add block to layout
        self.message_layout.addWidget(block)
        self._current_block = block

        QApplication.processEvents()

        # Jump to the TOP of the new assistant message
        self._scroll_to_widget_top(block)

    def append_token(self, token: str):
        """Append a streamed token to the current assistant block."""
        if not self._current_block:
            return

        self._current_text += token
        self._current_block.set_text(self._current_text)

        # Keep UI responsive, but DO NOT scroll
        QApplication.processEvents()

    def finalize(self):
        """Finish the assistant block. No auto-scroll."""
        self._current_block = None
        self._current_text = ""

    # --------------------------------------------------------------
    # Internal helpers
    # --------------------------------------------------------------

    def _scroll_to_widget_top(self, widget):
        """
        Scroll the QScrollArea so that the top of the given widget
        is aligned with the top of the viewport.
        """
        bar = self.scroll_area.verticalScrollBar()
        y = widget.y()
        bar.setValue(y)
