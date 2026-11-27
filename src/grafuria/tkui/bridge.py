"""
Thread-safe bridge between the script thread and Tkinter.

Tkinter is not thread-safe: only the main thread may touch widgets. The
script thread changes the model and either enqueues UI calls
(run_in_ui) or marks elements as dirty (mark_dirty). The bridge drains
both periodically in the main thread.
"""

import queue
import sys
import threading


class UiBridge:
    PUMP_MS = 16  # ~60 redraws per second

    def __init__(self, widget):
        self._widget = widget
        self._queue: queue.SimpleQueue = queue.SimpleQueue()
        self._dirty: set = set()
        self._lock = threading.Lock()
        self._after_id = None

    @staticmethod
    def in_ui_thread() -> bool:
        return threading.current_thread() is threading.main_thread()

    def start(self) -> None:
        self._after_id = self._widget.after(self.PUMP_MS, self._pump)

    def stop(self) -> None:
        if self._after_id is not None:
            self._widget.after_cancel(self._after_id)
            self._after_id = None

    def run_in_ui(self, fn, *args) -> None:
        """
        Runs fn(*args) in the UI thread: immediately when already there,
        otherwise on the next pump, preserving call order.
        """
        if self.in_ui_thread():
            fn(*args)
        else:
            self._queue.put((fn, args))

    def mark_dirty(self, view) -> None:
        """
        Asks for view.draw(). From another thread, repeated requests for
        the same view between two pumps become a single redraw.
        """
        if self.in_ui_thread():
            view.draw()
        else:
            with self._lock:
                self._dirty.add(view)

    def _pump(self) -> None:
        while True:
            try:
                fn, args = self._queue.get_nowait()
            except queue.Empty:
                break
            try:
                fn(*args)
            except Exception as e:  # never let the pump die
                print(f"[grafuria] UI callback error: {e}", file=sys.stderr)
        with self._lock:
            dirty, self._dirty = self._dirty, set()
        for view in dirty:
            try:
                if view.model.view is view:  # skip views destroyed meanwhile
                    view.draw()
            except Exception as e:
                print(f"[grafuria] redraw error: {e}", file=sys.stderr)
        self._after_id = self._widget.after(self.PUMP_MS, self._pump)
