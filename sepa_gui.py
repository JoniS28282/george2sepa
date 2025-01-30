# sepa_gui.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

import sepa_converter  # Our converter logic

def run_app():
    app = SepaApp()
    app.mainloop()

class SepaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SEPA Converter")
        self.geometry("600x400")

        # 1) Choose between Lastschrift / Überweisung
        self.mode_var = tk.StringVar(value="lastschrift")
        mode_frame = ttk.LabelFrame(self, text="SEPA Mode")
        mode_frame.pack(padx=10, pady=5, fill="x")
        ttk.Radiobutton(mode_frame, text="Lastschrift (pain.008)",
                        variable=self.mode_var, value="lastschrift").pack(side="left", padx=5)
        ttk.Radiobutton(mode_frame, text="Überweisung (pain.001)",
                        variable=self.mode_var, value="ueberweisung").pack(side="left", padx=5)

        # 2) Company Name
        company_frame = ttk.Frame(self)
        company_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(company_frame, text="Company Name:").pack(side="left")
        self.company_name_var = tk.StringVar(value="My Company")
        ttk.Entry(company_frame, textvariable=self.company_name_var, width=35).pack(side="left", padx=5)

        # 3) CSV input file
        csv_frame = ttk.Frame(self)
        csv_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(csv_frame, text="Input CSV:").pack(side="left")
        self.csv_path_var = tk.StringVar()
        csv_entry = ttk.Entry(csv_frame, textvariable=self.csv_path_var, width=40)
        csv_entry.pack(side="left", padx=5)
        ttk.Button(csv_frame, text="Browse...", command=self.browse_csv).pack(side="left")

        # 4) Output directory
        outdir_frame = ttk.Frame(self)
        outdir_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(outdir_frame, text="Output Folder:").pack(side="left")
        self.output_dir_var = tk.StringVar()
        outdir_entry = ttk.Entry(outdir_frame, textvariable=self.output_dir_var, width=35)
        outdir_entry.pack(side="left", padx=5)
        ttk.Button(outdir_frame, text="Browse...", command=self.browse_output_dir).pack(side="left")

        # 5) Additional SEPA fields (Sequence Type for Lastschrift, BatchBooking, etc.)
        settings_frame = ttk.LabelFrame(self, text="SEPA Settings")
        settings_frame.pack(padx=10, pady=5, fill="x")

        # Sequence Type
        ttk.Label(settings_frame, text="Sequence Type (Lastschrift):").grid(row=0, column=0, padx=5, pady=2, sticky="e")
        self.seqtype_var = tk.StringVar(value="RCUR")  # default
        seqtype_entry = ttk.Entry(settings_frame, textvariable=self.seqtype_var, width=6)
        seqtype_entry.grid(row=0, column=1, padx=5, pady=2, sticky="w")

        # Batch Booking
        self.batch_var = tk.BooleanVar(value=False)  # default is false
        ttk.Checkbutton(settings_frame, text="Batch Booking (BtchBookg=true)?",
                        variable=self.batch_var).grid(row=1, column=0, columnspan=2, padx=5, pady=2, sticky="w")

        # 6) Start button
        ttk.Button(self, text="Start Processing", command=self.start_processing).pack(pady=10)

        # 7) Text box for log messages
        self.log_text = tk.Text(self, height=6)
        self.log_text.pack(padx=10, pady=5, fill="both", expand=True)

    def browse_csv(self):
        file_path = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if file_path:
            self.csv_path_var.set(file_path)

    def browse_output_dir(self):
        dir_path = filedialog.askdirectory(title="Select Output Directory")
        if dir_path:
            self.output_dir_var.set(dir_path)

    def start_processing(self):
        csv_path = self.csv_path_var.get()
        out_dir = self.output_dir_var.get()

        if not os.path.isfile(csv_path):
            self.log("ERROR: Invalid CSV file path.")
            return
        if not os.path.isdir(out_dir):
            self.log("ERROR: Invalid output directory.")
            return

        mode = self.mode_var.get()  # "lastschrift" or "ueberweisung"
        seq_type = self.seqtype_var.get()
        batch_booking = self.batch_var.get()
        company_name = self.company_name_var.get().strip()

        try:
            # Output filename
            output_file = os.path.join(out_dir, "pain-output.xml")

            if mode == "lastschrift":
                # Generate pain.008 with your custom fields
                sepa_converter.generate_pain008(
                    input_csv=csv_path,
                    output_xml=output_file,
                    sequence_type=seq_type,
                    company_name=company_name,
                    batch_booking=batch_booking
                )
                self.log(f"Created pain.008 (Lastschrift) at: {output_file}.")
            else:
                # Generate pain.001
                sepa_converter.generate_pain001(
                    input_csv=csv_path,
                    output_xml=output_file,
                    company_name=company_name,
                    batch_booking=batch_booking
                )
                self.log(f"Created pain.001 (Überweisung) at: {output_file}.")

            messagebox.showinfo("Success", "SEPA file created successfully!")
        except Exception as e:
            self.log(f"ERROR: {e}")
            messagebox.showerror("Error", str(e))

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
