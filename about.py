import tkinter as tk
import webbrowser
from tkinter import Toplevel, Label, Button


class About:
    def __init__(self, app):
        self.dialog = Toplevel(app)
        self.dialog.title("About")
        self.dialog.geometry("500x400")
        self.dialog.transient(app)
        self.dialog.grab_set()

        tk.Label(
            self.dialog,
            text=f"{app.title()}",
            wraplength=300,
            justify="center",
            font=("Arial", 12, "bold"),
        ).pack(pady=10)

        Label(
            self.dialog,
            text="Version 1.0",
            font=("Arial", 10),
        ).pack()

        about_message = (
            "This program is designed for creating graphs and executing algorithms"
            "written in the Lua programming language on those graphs. It allows users"
            "to easily build directed and undirected graphs, assign weights to edges,"
            "and name vertices. The software supports dynamic interaction with graphs"
            "through Lua scripts, enabling the execution of various algorithms to"
            "manipulate the graph's structure and behavior."
        )
        tk.Label(
            self.dialog,
            text=about_message,
            wraplength=400,
            justify="left",
        ).pack(pady=10)

        self.label_github = tk.Label(
            self.dialog,
            text="https://github.com/saulopz/grafuria",
            font=("Arial", 10),
            fg="blue",
            cursor="hand2",
        )
        self.label_github.pack(pady=1)
        self.label_github.bind("<Button-1>", self.open_url)

        Label(
            self.dialog,
            text="Developed by Saulo Popov Zambiasi",
            font=("Arial", 10),
        ).pack(pady=1)

        self.label_email = Label(
            self.dialog,
            text="saulopz@gmail.com",
            font=("Arial", 10),
        ).pack(pady=1)

        Button(
            self.dialog,
            text="Fechar",
            command=self.dialog.destroy,
        ).pack(pady=20)

    def open_url(self, event):
        url = event.widget.cget("text")
        webbrowser.open(url)
