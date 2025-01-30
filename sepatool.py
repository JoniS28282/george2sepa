#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import xml.etree.ElementTree as ET
import datetime
import uuid
import os

class SepaTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SEPA Converter")
        self.geometry("700x500")

        # --- Frame: SEPA Mode (Lastschrift vs. Überweisung) ---
        mode_frame = ttk.LabelFrame(self, text="SEPA Mode")
        mode_frame.pack(padx=10, pady=5, fill="x")
        self.mode_var = tk.StringVar(value="lastschrift")
        ttk.Radiobutton(mode_frame, text="Lastschrift (pain.008)",
                        variable=self.mode_var, value="lastschrift",
                        command=self.on_mode_change).pack(side="left", padx=5)
        ttk.Radiobutton(mode_frame, text="Überweisung (pain.001)",
                        variable=self.mode_var, value="ueberweisung",
                        command=self.on_mode_change).pack(side="left", padx=5)

        # --- Frame: Company Name ---
        company_frame = ttk.Frame(self)
        company_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(company_frame, text="Company Name:").pack(side="left")
        self.company_name_var = tk.StringVar(value="My Company")
        ttk.Entry(company_frame, textvariable=self.company_name_var, width=40).pack(side="left", padx=5)

        # --- Frame: CSV input ---
        csv_frame = ttk.Frame(self)
        csv_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(csv_frame, text="Input CSV:").pack(side="left")
        self.csv_var = tk.StringVar()
        ttk.Entry(csv_frame, textvariable=self.csv_var, width=40).pack(side="left", padx=5)
        ttk.Button(csv_frame, text="Browse...", command=self.browse_csv).pack(side="left")

        # --- Frame: Output XML file ---
        out_frame = ttk.Frame(self)
        out_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(out_frame, text="Output File:").pack(side="left")
        self.output_xml_var = tk.StringVar()
        ttk.Entry(out_frame, textvariable=self.output_xml_var, width=40).pack(side="left", padx=5)
        ttk.Button(out_frame, text="Save As...", command=self.browse_output).pack(side="left")

        # --- Frame: Additional Settings ---
        settings_frame = ttk.LabelFrame(self, text="Settings")
        settings_frame.pack(padx=10, pady=5, fill="x")

        # Sequence Type (only needed for Lastschrift)
        ttk.Label(settings_frame, text="Sequence Type (Lastschrift):").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.seqtype_var = tk.StringVar(value="RCUR")  # FRST, RCUR, OOFF, FNAL
        self.seqtype_entry = ttk.Entry(settings_frame, textvariable=self.seqtype_var, width=6)
        self.seqtype_entry.grid(row=0, column=1, sticky="w", padx=5, pady=2)

        # Batch Booking
        self.batch_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(settings_frame, text="Batch Booking (BtchBookg=true)?",
                        variable=self.batch_var).grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=2)

        # --- Processing Button ---
        ttk.Button(self, text="Start Processing", command=self.start_processing).pack(pady=10)

        # --- Frame: Log / Output table ---
        self.log_text = tk.Text(self, height=10)
        self.log_text.pack(padx=10, pady=5, fill="both", expand=True)

        self.on_mode_change()  # Hide sequence type if necessary

    def on_mode_change(self):
        """Hide or show the Sequence Type field depending on mode."""
        if self.mode_var.get() == "lastschrift":
            self.seqtype_entry.config(state="normal")
        else:
            self.seqtype_entry.config(state="disabled")

    def browse_csv(self):
        file_path = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if file_path:
            self.csv_var.set(file_path)

    def browse_output(self):
        file_path = filedialog.asksaveasfilename(
            title="Select Output File",
            defaultextension=".xml",
            filetypes=[("XML Files", "*.xml"), ("All Files", "*.*")]
        )
        if file_path:
            self.output_xml_var.set(file_path)

    def start_processing(self):
        csv_path = self.csv_var.get()
        output_path = self.output_xml_var.get()
        mode = self.mode_var.get()  # 'lastschrift' or 'ueberweisung'
        company_name = self.company_name_var.get().strip()
        batch_booking = self.batch_var.get()
        seq_type = self.seqtype_var.get()

        if not os.path.isfile(csv_path):
            self.log("ERROR: Invalid CSV file path.")
            return
        if not output_path:
            self.log("ERROR: No output file specified.")
            return
        if not company_name:
            self.log("ERROR: Company Name cannot be empty.")
            return

        try:
            # Parse the CSV first to build a summary table
            rows = self.read_csv(csv_path)
            if not rows:
                self.log("ERROR: CSV is empty.")
                return

            # Generate the XML
            if mode == "lastschrift":
                self.generate_pain008(rows, output_path, company_name, seq_type, batch_booking)
                self.log("Created pain.008 (Lastschrift).")
            else:
                self.generate_pain001(rows, output_path, company_name, batch_booking)
                self.log("Created pain.001 (Überweisung).")

            # Display a table of the data we used
            self.display_table(rows, mode)

            messagebox.showinfo("Success", f"SEPA file created:\n{output_path}")

        except Exception as e:
            self.log(f"ERROR: {e}")
            messagebox.showerror("Error", str(e))

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def display_table(self, rows, mode):
        """Show a small 'table' of relevant fields in the log box."""
        self.log("\n--- Transactions in the XML ---")

        if mode == "lastschrift":
            # We assume columns: 'Zahlungspflichtiger-Name', 'Zahlungspflichtiger-IBAN', 'Betrag', 'Verwendungszweck'
            header = "{:<5} | {:<25} | {:<22} | {:>8} | {:<25}".format(
                "Idx", "Name", "IBAN", "Amount", "Purpose"
            )
        else:
            # Überweisung: 'Empfaenger-Name', 'Empfaenger-IBAN', 'Betrag', 'Verwendungszweck'
            header = "{:<5} | {:<25} | {:<22} | {:>8} | {:<25}".format(
                "Idx", "Name", "IBAN", "Amount", "Purpose"
            )

        self.log_text.insert(tk.END, header + "\n")
        self.log_text.insert(tk.END, "-" * len(header) + "\n")

        for i, row in enumerate(rows, start=1):
            if mode == "lastschrift":
                name = row.get("Zahlungspflichtiger-Name", "")
                iban = row.get("Zahlungspflichtiger-IBAN", "")
            else:
                name = row.get("Empfaenger-Name", "")
                iban = row.get("Empfaenger-IBAN", "")

            betrag = row.get("Betrag", "0").replace(",", ".")
            zweck = row.get("Verwendungszweck", "")

            line = "{:<5} | {:<25} | {:<22} | {:>8} | {:<25}".format(
                str(i), name[:25], iban[:22], betrag, zweck[:25]
            )
            self.log_text.insert(tk.END, line + "\n")
        self.log_text.insert(tk.END, "\n")

    # ---------------------------------
    # CSV Parser
    # ---------------------------------
    def read_csv(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            # Adjust delimiter as needed (semicolon, tab, etc.)
            # For simplicity, we assume semicolon here:
            reader = csv.DictReader(f, delimiter=';')
            return list(reader)

    # ---------------------------------
    # SEPA Generation Methods
    # ---------------------------------
    def generate_pain008(self, rows, output_xml, company_name, sequence_type, batch_booking):
        """
        Lastschrift (pain.008.003.02) with grouping = GRPD, optional <BtchBookg>.
        """
        root = ET.Element('Document', {
            'xmlns': "urn:iso:std:iso:20022:tech:xsd:pain.008.003.02",
            'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance",
            'xsi:schemaLocation': "urn:iso:std:iso:20022:tech:xsd:pain.008.003.02 pain.008.003.02.xsd"
        })
        cstmrDrctDbtInitn = ET.SubElement(root, 'CstmrDrctDbtInitn')

        # <GrpHdr>
        grpHdr = ET.SubElement(cstmrDrctDbtInitn, 'GrpHdr')
        ET.SubElement(grpHdr, 'MsgId').text = f"MSG-{uuid.uuid4()}"
        ET.SubElement(grpHdr, 'CreDtTm').text = datetime.datetime.now().isoformat()
        nbOfTxs_elm = ET.SubElement(grpHdr, 'NbOfTxs')
        ctrlSum_elm = ET.SubElement(grpHdr, 'CtrlSum')
        ET.SubElement(grpHdr, 'Grpg').text = "GRPD"
        initgPty = ET.SubElement(grpHdr, 'InitgPty')
        ET.SubElement(initgPty, 'Nm').text = company_name
        if batch_booking:
            ET.SubElement(grpHdr, 'BtchBookg').text = "true"

        # <PmtInf>
        pmtInf = ET.SubElement(cstmrDrctDbtInitn, 'PmtInf')
        ET.SubElement(pmtInf, 'PmtInfId').text = f"PMT-{uuid.uuid4()}"
        ET.SubElement(pmtInf, 'PmtMtd').text = "DD"
        pmtInfNbOfTxs = ET.SubElement(pmtInf, 'NbOfTxs')
        pmtInfCtrlSum = ET.SubElement(pmtInf, 'CtrlSum')

        pmtTpInf = ET.SubElement(pmtInf, 'PmtTpInf')
        svcLvl = ET.SubElement(pmtTpInf, 'SvcLvl')
        ET.SubElement(svcLvl, 'Cd').text = "SEPA"
        lclInstrm = ET.SubElement(pmtTpInf, 'LclInstrm')
        ET.SubElement(lclInstrm, 'Cd').text = "CORE"  # or row-based if B2B
        ET.SubElement(pmtTpInf, 'SeqTp').text = sequence_type

        first_due_date = rows[0].get('Faelligkeitsdatum', '2025-01-01')
        ET.SubElement(pmtInf, 'ReqdColltnDt').text = self.convert_date(first_due_date)

        # Creditor
        cdtr = ET.SubElement(pmtInf, 'Cdtr')
        ET.SubElement(cdtr, 'Nm').text = company_name

        # Creditor Account
        cdtrAcct = ET.SubElement(pmtInf, 'CdtrAcct')
        cdtrAcctId = ET.SubElement(cdtrAcct, 'Id')
        ET.SubElement(cdtrAcctId, 'IBAN').text = rows[0].get('Auftraggeber-IBAN', '')

        # Creditor Agent
        cdtrAgt = ET.SubElement(pmtInf, 'CdtrAgt')
        finInstnId = ET.SubElement(cdtrAgt, 'FinInstnId')
        # if you have a BIC: ET.SubElement(finInstnId, 'BIC').text = "YOURBICXXX"

        ET.SubElement(pmtInf, 'ChrgBr').text = "SLEV"

        # <CdtrSchmeId>
        cdtrSchmeId = ET.SubElement(pmtInf, 'CdtrSchmeId')
        csId = ET.SubElement(cdtrSchmeId, 'Id')
        prvtId = ET.SubElement(csId, 'PrvtId')
        othr = ET.SubElement(prvtId, 'Othr')
        ET.SubElement(othr, 'Id').text = rows[0].get('Creditor-ID', 'DE99ZZZ09999999999')
        schmeNm = ET.SubElement(othr, 'SchmeNm')
        ET.SubElement(schmeNm, 'Prtry').text = "SEPA"

        total_count = 0
        total_amount = 0.0

        for row in rows:
            betrag = row.get('Betrag', '0').replace(',', '.')
            try:
                amt_val = float(betrag)
            except:
                amt_val = 0.0

            drctDbtTxInf = ET.SubElement(pmtInf, 'DrctDbtTxInf')
            pmtId = ET.SubElement(drctDbtTxInf, 'PmtId')
            ET.SubElement(pmtId, 'EndToEndId').text = f"E2E-{uuid.uuid4()}"

            instdAmt = ET.SubElement(drctDbtTxInf, 'InstdAmt', {'Ccy': 'EUR'})
            instdAmt.text = f"{amt_val:.2f}"

            drctDbtTx = ET.SubElement(drctDbtTxInf, 'DrctDbtTx')
            mndtRltdInf = ET.SubElement(drctDbtTx, 'MndtRltdInf')
            ET.SubElement(mndtRltdInf, 'MndtId').text = row.get('Mandatsreferenz', 'Mandat001')
            dtOfSgntr = row.get('Mandatsaustellungsdatum', '2025-01-01')
            ET.SubElement(mndtRltdInf, 'DtOfSgntr').text = self.convert_date(dtOfSgntr)
            ET.SubElement(mndtRltdInf, 'AmdmntInd').text = "false"

            dbtrAgt = ET.SubElement(drctDbtTxInf, 'DbtrAgt')
            dbtrFinInstnId = ET.SubElement(dbtrAgt, 'FinInstnId')
            # If you have Debtor BIC: ET.SubElement(dbtrFinInstnId, 'BIC').text = ...

            dbtr = ET.SubElement(drctDbtTxInf, 'Dbtr')
            ET.SubElement(dbtr, 'Nm').text = row.get('Zahlungspflichtiger-Name', '')

            dbtrAcct = ET.SubElement(drctDbtTxInf, 'DbtrAcct')
            dbtrAcctId = ET.SubElement(dbtrAcct, 'Id')
            ET.SubElement(dbtrAcctId, 'IBAN').text = row.get('Zahlungspflichtiger-IBAN', '')

            rmtInf = ET.SubElement(drctDbtTxInf, 'RmtInf')
            ET.SubElement(rmtInf, 'Ustrd').text = row.get('Verwendungszweck', '')

            total_count += 1
            total_amount += amt_val

        # Update counts
        nbOfTxs_elm.text = str(total_count)
        ctrlSum_elm.text = f"{total_amount:.2f}"
        pmtInfNbOfTxs.text = str(total_count)
        pmtInfCtrlSum.text = f"{total_amount:.2f}"

        # Write file
        tree = ET.ElementTree(root)
        tree.write(output_xml, encoding='utf-8', xml_declaration=True)

    def generate_pain001(self, rows, output_xml, company_name, batch_booking):
        """
        Überweisung (pain.001.003.03) - single PaymentInfo bundling all transactions.
        """
        root = ET.Element('Document', {
            'xmlns': "urn:iso:std:iso:20022:tech:xsd:pain.001.003.03",
            'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance",
            'xsi:schemaLocation': "urn:iso:std:iso:20022:tech:xsd:pain.001.003.03 pain.001.003.03.xsd"
        })
        cstmrCdtTrfInitn = ET.SubElement(root, 'CstmrCdtTrfInitn')

        grpHdr = ET.SubElement(cstmrCdtTrfInitn, 'GrpHdr')
        ET.SubElement(grpHdr, 'MsgId').text = f"MSG-{uuid.uuid4()}"
        ET.SubElement(grpHdr, 'CreDtTm').text = datetime.datetime.now().isoformat()
        nbOfTxs_elm = ET.SubElement(grpHdr, 'NbOfTxs')
        ctrlSum_elm = ET.SubElement(grpHdr, 'CtrlSum')
        ET.SubElement(grpHdr, 'Grpg').text = "GRPD"
        initgPty = ET.SubElement(grpHdr, 'InitgPty')
        ET.SubElement(initgPty, 'Nm').text = company_name
        if batch_booking:
            ET.SubElement(grpHdr, 'BtchBookg').text = "true"

        pmtInf = ET.SubElement(cstmrCdtTrfInitn, 'PmtInf')
        ET.SubElement(pmtInf, 'PmtInfId').text = f"PMT-{uuid.uuid4()}"
        ET.SubElement(pmtInf, 'PmtMtd').text = "TRF"
        pmtInfNbOfTxs = ET.SubElement(pmtInf, 'NbOfTxs')
        pmtInfCtrlSum = ET.SubElement(pmtInf, 'CtrlSum')

        pmtTpInf = ET.SubElement(pmtInf, 'PmtTpInf')
        svcLvl = ET.SubElement(pmtTpInf, 'SvcLvl')
        ET.SubElement(svcLvl, 'Cd').text = "SEPA"

        first_date = rows[0].get('Durchfuehrungsdatum', '2025-01-01')
        ET.SubElement(pmtInf, 'ReqdExctnDt').text = self.convert_date(first_date)

        # Debtor
        dbtr = ET.SubElement(pmtInf, 'Dbtr')
        ET.SubElement(dbtr, 'Nm').text = company_name

        # Debtor Account
        dbtrAcct = ET.SubElement(pmtInf, 'DbtrAcct')
        dbtrAcctId = ET.SubElement(dbtrAcct, 'Id')
        ET.SubElement(dbtrAcctId, 'IBAN').text = rows[0].get('Auftraggeber-IBAN', '')

        # Debtor Agent
        dbtrAgt = ET.SubElement(pmtInf, 'DbtrAgt')
        finInstnId = ET.SubElement(dbtrAgt, 'FinInstnId')
        bic_val = rows[0].get('Auftraggeber-BIC', '')
        if bic_val:
            ET.SubElement(finInstnId, 'BIC').text = bic_val

        ET.SubElement(pmtInf, 'ChrgBr').text = "SLEV"

        total_count = 0
        total_amount = 0.0

        for row in rows:
            betrag = row.get('Betrag', '0').replace(',', '.')
            try:
                amt_val = float(betrag)
            except:
                amt_val = 0.0

            cdtTrfTxInf = ET.SubElement(pmtInf, 'CdtTrfTxInf')

            pmtId = ET.SubElement(cdtTrfTxInf, 'PmtId')
            ET.SubElement(pmtId, 'EndToEndId').text = f"E2E-{uuid.uuid4()}"

            amt_el = ET.SubElement(cdtTrfTxInf, 'Amt')
            instdAmt = ET.SubElement(amt_el, 'InstdAmt', {'Ccy': 'EUR'})
            instdAmt.text = f"{amt_val:.2f}"

            cdtrAgt = ET.SubElement(cdtTrfTxInf, 'CdtrAgt')
            cdtrFin = ET.SubElement(cdtrAgt, 'FinInstnId')
            emp_bic = row.get('Empfaenger-BIC', '')
            if emp_bic:
                ET.SubElement(cdtrFin, 'BIC').text = emp_bic

            cdtrTag = ET.SubElement(cdtTrfTxInf, 'Cdtr')
            ET.SubElement(cdtrTag, 'Nm').text = row.get('Empfaenger-Name', '')

            cdtrAcctTag = ET.SubElement(cdtTrfTxInf, 'CdtrAcct')
            cdtrAcctId = ET.SubElement(cdtrAcctTag, 'Id')
            ET.SubElement(cdtrAcctId, 'IBAN').text = row.get('Empfaenger-IBAN', '')

            rmtInf = ET.SubElement(cdtTrfTxInf, 'RmtInf')
            ET.SubElement(rmtInf, 'Ustrd').text = row.get('Verwendungszweck', '')

            total_count += 1
            total_amount += amt_val

        # Update counts
        nbOfTxs_elm.text = str(total_count)
        ctrlSum_elm.text = f"{total_amount:.2f}"
        pmtInfNbOfTxs.text = str(total_count)
        pmtInfCtrlSum.text = f"{total_amount:.2f}"

        tree = ET.ElementTree(root)
        tree.write(output_xml, encoding='utf-8', xml_declaration=True)

    def convert_date(self, date_str):
        """ Convert e.g. '31.01.2025' => '2025-01-31'. If fails, fallback. """
        if not date_str:
            return "2025-01-01"
        for sep in ('.', '/', '-'):
            parts = date_str.split(sep)
            if len(parts) == 3:
                try:
                    dd = int(parts[0])
                    mm = int(parts[1])
                    yyyy = int(parts[2])
                    return f"{yyyy:04d}-{mm:02d}-{dd:02d}"
                except:
                    pass
        return date_str


if __name__ == "__main__":
    app = SepaTool()
    app.mainloop()
