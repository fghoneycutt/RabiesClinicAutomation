import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox

from core import run_automation


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Shelterluv Intake Automation")
        self.root.geometry("700x500")

        self.file_path = tk.StringVar()
        self.running = False

        # FILE PICKER
        tk.Label(root, text="Input File (.xlsx or .tsv):").pack(pady=5)

        file_frame = tk.Frame(root)
        file_frame.pack(fill="x", padx=10)

        tk.Entry(file_frame, textvariable=self.file_path).pack(side="left", fill="x", expand=True)

        tk.Button(file_frame, text="Browse", command=self.browse_file).pack(side="left", padx=5)

        # START BUTTON
        self.start_btn = tk.Button(
            root,
            text="Start Automation",
            bg="green",
            fg="white",
            height=2,
            command=self.start
        )
        self.start_btn.pack(pady=10)

        # LOG
        self.log_box = scrolledtext.ScrolledText(root, height=20)
        self.log_box.pack(fill="both", expand=True, padx=10, pady=10)

    def browse_file(self):
        file = filedialog.askopenfilename(
            filetypes=[("Excel/TSV Files", "*.xlsx *.tsv")]
        )
        if file:
            self.file_path.set(file)

    def log(self, msg):
        self.log_box.insert(tk.END, msg + "\n")
        self.log_box.see(tk.END)
        self.root.update_idletasks()

    def run_worker(self):
        try:
            self.running = True
            self.root.after(0, lambda: self.start_btn.config(state="disabled"))

            self.log("🚀 Starting automation...\n")

            run_automation(self.file_path.get(), self.log)

            self.log("\n✅ COMPLETE — all records processed")

        except Exception as e:
            self.log(f"\n❌ ERROR: {str(e)}")
            messagebox.showerror("Error", str(e))

        finally:
            self.running = False
            self.root.after(0, lambda: self.start_btn.config(state="normal"))

    def start(self):
        if self.running:
            return

        if not self.file_path.get():
            messagebox.showwarning("Missing File", "Please select a file first.")
            return

        thread = threading.Thread(target=self.run_worker, daemon=True)
        thread.start()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()