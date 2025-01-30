# sepa_gui.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

# Import the converter logic
import sepa_converter

def run_app():
    app = SepaApp()
    app.mainloop()

class SepaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SEPA Converter")
        self.geometry("600x300")

        # 1) Choose between Lastschrift / Überweisung
        self.mode_var = tk.StringVar(value="lastschrift")
        mode_frame = ttk.LabelFrame(self, text="Mode")
        mode_frame.pack(padx=10, pady=5, fill="x")
        ttk.Radiobutton(mode_frame, text="Lastschrift (pain.008)", 
                        variable=self.mode_var, value="lastschrift").pack(side="left", padx=5)
        ttk.Radiobutton(mode_frame, text="Überweisung (pain.001)", 
                        variable=self.mode_var, value="ueberweisung").pack(side="left", padx=5)

        # 2) CSV input file
        self.csv_path_var = tk.StringVar()
        csv_frame = ttk.Frame(self)
        csv_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(csv_frame, text="Input CSV:").pack(side="left")
        csv_entry = ttk.Entry(csv_frame, textvariable=self.csv_path_var, width=40)
        csv_entry.pack(side="left", padx=5)
        ttk.Button(csv_frame, text="Browse...", command=self.browse_csv).pack(side="left")

        # 3) Output directory
        self.output_dir_var = tk.StringVar()
        outdir_frame = ttk.Frame(self)
        outdir_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(outdir_frame, text="Output Folder:").pack(side="left")
        outdir_entry = ttk.Entry(outdir_frame, textvariable=self.output_dir_var, width=35)
        outdir_entry.pack(side="left", padx=5)
        ttk.Button(outdir_frame, text="Browse...", command=self.browse_output_dir).pack(side="left")

        # 4) Additional SEPA fields (especially for Lastschrift)
        #    e.g. Sequence Type, Grouping, etc.
        settings_frame = ttk.LabelFrame(self, text="SEPA Settings")
        settings_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(settings_frame, text="Sequence Type (FRST, RCUR, OOFF, FNAL):").pack(side="left", padx=5)
        self.seqtype_var = tk.StringVar(value="RCUR")
        seqtype_entry = ttk.Entry(settings_frame, textvariable=self.seqtype_var, width=6)
        seqtype_entry.pack(side="left")

        # 5) Start button
        ttk.Button(self, text="Start Processing", command=self.start_processing).pack(pady=10)

        # 6) Text box (or label) for log feedback
        self.log_text = tk.Text(self, height=5)
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

        try:
            # Output filename: e.g. "pain-output.xml"
            # You could further customize naming
            output_file = os.path.join(out_dir, "pain-output.xml")

            if mode == "lastschrift":
                # Generate a pain.008
                sepa_converter.generate_pain008(
                    input_csv=csv_path,
                    output_xml=output_file,
                    sequence_type=seq_type
                )
                self.log(f"Created pain.008 at {output_file}.")
            else:
                # Generate a pain.001
                sepa_converter.generate_pain001(
                    input_csv=csv_path,
                    output_xml=output_file
                )
                self.log(f"Created pain.001 at {output_file}.")

            messagebox.showinfo("Success", "SEPA file created successfully!")
        except Exception as e:
            self.log(f"ERROR: {e}")
            messagebox.showerror("Error", str(e))

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
