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
        self.send_emails_var = tk.BooleanVar(value=False)
        self.running = False

        # FILE PICKER
        tk.Label(root, text="Input File (.xlsx or .tsv):").pack(pady=5)

        file_frame = tk.Frame(root)
        file_frame.pack(fill="x", padx=10)

        tk.Entry(
            file_frame,
            textvariable=self.file_path
        ).pack(side="left", fill="x", expand=True)

        tk.Button(
            file_frame,
            text="Browse",
            command=self.browse_file
        ).pack(side="left", padx=5)

        # OPTIONAL CERTIFICATE EMAIL CHECKBOX
        tk.Checkbutton(
            root,
            text="Email latest rabies certificate to owner after vaccine entry",
            variable=self.send_emails_var
        ).pack(anchor="w", padx=10, pady=5)

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
        # Schedule GUI updates on Tkinter's main thread.
        self.root.after(0, self._append_log, str(msg))

    def _append_log(self, msg):
        self.log_box.insert(tk.END, msg + "\n")
        self.log_box.see(tk.END)

    def run_worker(self, input_file, send_emails):
        try:
            self.log("🚀 Starting automation...\n")

            self.log(
                "📧 Certificate emailing: "
                + ("ENABLED" if send_emails else "DISABLED")
            )

            run_automation(
                input_file,
                log=self.log,
                send_certificate_emails=send_emails
            )

            self.log("\n✅ COMPLETE — all records processed")

        except Exception as e:
            self.log(f"\n❌ ERROR: {str(e)}")
            self.root.after(
                0,
                lambda error=str(e): messagebox.showerror("Error", error)
            )

        finally:
            self.running = False
            self.root.after(
                0,
                lambda: self.start_btn.config(state="normal")
            )

    def start(self):
        if self.running:
            return

        input_file = self.file_path.get().strip()

        if not input_file:
            messagebox.showwarning(
                "Missing File",
                "Please select a file first."
            )
            return

        # Read GUI settings on the main thread before starting the worker.
        send_emails = self.send_emails_var.get()

        self.running = True
        self.start_btn.config(state="disabled")

        thread = threading.Thread(
            target=self.run_worker,
            args=(input_file, send_emails),
            daemon=True
        )
        thread.start()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
