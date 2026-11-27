"""Log area and status bar at the bottom of the window."""

import tkinter as tk
from tkinter import ttk


class LogPanel:
    def __init__(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X)
        self.text = tk.Text(frame, wrap="word", state="disabled", height=5)
        scroll = tk.Scrollbar(frame, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill=tk.Y)

    def append(self, line: str) -> None:
        self.text.config(state="normal")
        self.text.insert(tk.END, line + "\n")
        self.text.yview(tk.END)
        self.text.config(state="disabled")

    def clear(self) -> None:
        self.text.config(state="normal")
        self.text.delete("1.0", tk.END)
        self.text.config(state="disabled")

    def get_text(self) -> str:
        return self.text.get("1.0", "end")


class StatusBar:
    def __init__(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X)
        self.label = ttk.Label(frame, text="Info: ")
        self.label.pack(side=tk.LEFT, padx=10)

    def set(self, text) -> None:
        self.label.config(text=f"Info: {text}")
