import os
import json
import tkinter as tk


# -------------------------
# Properties class
# -------------------------
class Properties:
    """
    Class to manage properties of a lua script in a GUI using tkinter.
    It loads properties from a JSON file, displays them in a GUI.

    Attributes
    ----------
    frame : tkinter.Frame
        The frame where the properties are displayed.
    attr : dict
        The properties loaded from the JSON file.
    filename : str
        The name of the JSON file.
    name : str
        The name of the script file without extension.
    """
    def __init__(self, frame, filename):
        """
        Parameters
        ----------
        frame : tkinter.Frame
            The frame where the properties are displayed.
        filename : str
            The path and name of the script file.
        """
        self.frame = frame
        self.attr = None
        name, extension = os.path.splitext(filename)
        self.filename = name + ".json"
        self.name = os.path.splitext(os.path.basename(filename))[0]
        print(self.filename)
        self.load()
        self.show()

    # --------------------------
    # Show
    # --------------------------
    def show(self):
        """
        Show the properties in the GUI.
        """
        self.clear()
        row = 0

        tk.Label(
            self.frame,
            text=f"Properties: {self.name}",
            font=("Segoe UI", 10, "bold"),
            anchor="w"
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(4, 2), padx=(2, 2))
        row += 1
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=1)
        row += 1

        for key, value in self.attr.items():
            if key.endswith("_min") or key.endswith("_max"):
                continue

            if isinstance(value, bool):
                var = tk.BooleanVar(value=value)
                label = tk.Label(self.frame, text=key)
                label.grid(row=row, column=0, sticky="w", padx=(0, 5))
                cb = tk.Checkbutton(self.frame, variable=var, command=self.save)
                cb.grid(row=row, column=1, sticky="e", padx=(2, 2))
                self.attr[key] = var
                row += 1

            elif isinstance(value, int):
                min_key = f"{key}_min"
                max_key = f"{key}_max"
                if min_key in self.attr and max_key in self.attr:
                    min_val = self.attr[min_key]
                    max_val = self.attr[max_key]
                    var = tk.IntVar(value=value)

                    label = tk.Label(self.frame, text=key)
                    label.grid(row=row, column=0, sticky="w", padx=(0, 5))

                    scale = tk.Scale(
                        self.frame,
                        from_=min_val,
                        to=max_val,
                        orient="horizontal",
                        variable=var,
                        showvalue=False,
                        command=lambda val, k=key, v=var: self.set_attr(k, v.get()) or self.save() or scale_label_value.config(text=v.get())
                    )
                    scale.grid(row=row, column=1, sticky="ew")

                    scale_label_value = tk.Label(self.frame, text=var.get())
                    scale_label_value.grid(row=row, column=1, sticky="w", padx=(2, 10))

                    self.attr[key] = var
                    row += 1
                else:
                    label = tk.Label(self.frame, text=key)
                    label.grid(row=row, column=0, sticky="w", padx=(0, 5))
                    entry = tk.Entry(self.frame)
                    entry.insert(0, str(value))
                    entry.bind("<FocusOut>", lambda e, k=key, w=entry: self.set_attr(k, int(w.get())) or self.save())
                    entry.grid(row=row, column=1, sticky="ew")
                    row += 1

            elif isinstance(value, (float, complex)):
                label = tk.Label(self.frame, text=key)
                label.grid(row=row, column=0, sticky="w", padx=(0, 5))
                entry = tk.Entry(self.frame)
                entry.insert(0, str(value))
                entry.bind("<FocusOut>", lambda e, k=key, w=entry: self.set_attr(k, float(w.get())) or self.save())
                entry.grid(row=row, column=1, sticky="ew")
                row += 1

            else:  # assume string
                label = tk.Label(self.frame, text=key)
                label.grid(row=row, column=0, sticky="w", padx=(0, 5))
                entry = tk.Entry(self.frame)
                entry.insert(0, value)
                entry.bind("<FocusOut>", lambda e, k=key, w=entry: self.set_attr(k, w.get()) or self.save())
                entry.grid(row=row, column=1, sticky="ew")
                row += 1

    # --------------------------
    # Get Attribute
    # --------------------------
    def get_attr(self, name):
        """
        Get the value of an attribute.

        Parameters
        ----------
        name : str
            The name of the attribute.

        Returns
        -------
        object
            The value of the attribute.
        """
        try:
            val = self.attr[name]
            return val.get() if isinstance(val, (tk.BooleanVar, tk.IntVar, tk.DoubleVar)) else val
        except KeyError:
            return None

    # --------------------------
    # Set Attribute
    # --------------------------
    def set_attr(self, name, value):
        """
        Set the value of an attribute.

        Parameters
        ----------
        name : str
            The name of the attribute.
        value : object
            The value to set.
        """
        if isinstance(self.attr[name], (tk.BooleanVar, tk.IntVar, tk.DoubleVar)):
            self.attr[name].set(value)
        else:
            self.attr[name] = value

    # --------------------------
    # Load
    # --------------------------
    def load(self):
        """
        Load the properties from a JSON file.
        """
        if not os.path.exists(self.filename):
            self.attr = {}  # ou algum default seguro
            return
        try:
            with open(self.filename, "r", encoding="utf-8") as filename:
                self.attr = json.load(filename)
        except json.JSONDecodeError as e:
            print(f"JSON Error:'{self.attr}': {e}")
            self.attr = {}

    # --------------------------
    # Save
    # --------------------------
    def save(self):
        """
        Save the properties to a JSON file.
        """
        serializable = {}
        for key, value in self.attr.items():
            if isinstance(value, (tk.BooleanVar, tk.IntVar, tk.DoubleVar)):
                serializable[key] = value.get()
            else:
                serializable[key] = value
        try:
            with open(self.filename, "w", encoding="utf-8") as filename:
                json.dump(serializable, filename, indent=4)
        except json.JSONDecodeError as e:
            self.log(f"JSON Error:'{self.attr}': {e}")
        except FileNotFoundError:
            self.log(f"File not found: {self.filename}")
        except PermissionError:
            self.log(f"Permission denied: {self.filename}")

    # --------------------------
    # Clear
    # --------------------------
    def clear(self):
        """
        Clear the frame by destroying all widgets.
        """
        for widget in self.frame.winfo_children():
            widget.destroy()

    # --------------------------
    # Log
    # --------------------------
    def log(self, msg):
        """
        Log a message to the console.
        """
        print(msg)
