# sepa_converter.py
import csv
import xml.etree.ElementTree as ET
import datetime
import uuid

def generate_pain008(input_csv, output_xml, sequence_type="RCUR"):
    """
    Generate a pain.008.003.02 XML file (Lastschrift / Direct Debit)
    reading data from 'input_csv', writing to 'output_xml'.
    'sequence_type' can be FRST, RCUR, OOFF, FNAL, etc.
    """
    # 1) Parse the CSV
    rows = read_csv(input_csv)

    # 2) Create root <Document> element with official namespaces
    root = ET.Element('Document', {
        'xmlns': "urn:iso:std:iso:20022:tech:xsd:pain.008.003.02",
        'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance",
        'xsi:schemaLocation': "urn:iso:std:iso:20022:tech:xsd:pain.008.003.02 pain.008.003.02.xsd"
    })
    cstmrDrctDbtInitn = ET.SubElement(root, 'CstmrDrctDbtInitn')

    # 3) <GrpHdr> (Group Header)
    grpHdr = ET.SubElement(cstmrDrctDbtInitn, 'GrpHdr')
    ET.SubElement(grpHdr, 'MsgId').text = f"MSG-{uuid.uuid4()}"
    ET.SubElement(grpHdr, 'CreDtTm').text = datetime.datetime.now().isoformat()
    # We'll fill NbOfTxs and CtrlSum later
    nbOfTxs_elm = ET.SubElement(grpHdr, 'NbOfTxs')
    ctrlSum_elm = ET.SubElement(grpHdr, 'CtrlSum')
    ET.SubElement(grpHdr, 'Grpg').text = "GRPD"  # or "MIXD" / "SNGL"

    # The Initiating Party (e.g. your company)
    initgPty = ET.SubElement(grpHdr, 'InitgPty')
    ET.SubElement(initgPty, 'Nm').text = "My Company"

    # 4) <PmtInf> (Payment Information)
    pmtInf = ET.SubElement(cstmrDrctDbtInitn, 'PmtInf')
    ET.SubElement(pmtInf, 'PmtInfId').text = f"PMT-{uuid.uuid4()}"
    ET.SubElement(pmtInf, 'PmtMtd').text = "DD"

    # (Optional) <NbOfTxs> and <CtrlSum> for this PaymentInfo block
    pmtInfNbOfTxs = ET.SubElement(pmtInf, 'NbOfTxs')
    pmtInfCtrlSum = ET.SubElement(pmtInf, 'CtrlSum')

    # <PmtTpInf> => <SvcLvl><Cd>SEPA</Cd>, <LclInstrm><Cd>CORE/B2B</Cd>, <SeqTp>...
    pmtTpInf = ET.SubElement(pmtInf, 'PmtTpInf')
    svcLvl = ET.SubElement(pmtTpInf, 'SvcLvl')
    ET.SubElement(svcLvl, 'Cd').text = "SEPA"
    lclInstrm = ET.SubElement(pmtTpInf, 'LclInstrm')
    ET.SubElement(lclInstrm, 'Cd').text = "CORE"  # or row-based if each row has a Mandatstyp
    ET.SubElement(pmtTpInf, 'SeqTp').text = sequence_type  # FRST, RCUR, OOFF, FNAL

    # <ReqdColltnDt> => from the first row or use today's date
    first_due_date = rows[0].get('Faelligkeitsdatum', '2025-01-01')
    ET.SubElement(pmtInf, 'ReqdColltnDt').text = convert_date(first_due_date)

    # <Cdtr> => Name
    cdtr = ET.SubElement(pmtInf, 'Cdtr')
    cdtr_name = rows[0].get('Auftraggeber-Name', 'My Company')
    ET.SubElement(cdtr, 'Nm').text = cdtr_name

    # <CdtrAcct> => IBAN
    cdtrAcct = ET.SubElement(pmtInf, 'CdtrAcct')
    cdtrAcctId = ET.SubElement(cdtrAcct, 'Id')
    ET.SubElement(cdtrAcctId, 'IBAN').text = rows[0].get('Auftraggeber-IBAN', '')

    # <CdtrAgt> => BIC if you have it, else skip
    # For official structure
    cdtrAgt = ET.SubElement(pmtInf, 'CdtrAgt')
    finInstnId = ET.SubElement(cdtrAgt, 'FinInstnId')
    # ET.SubElement(finInstnId, 'BIC').text = "MYBANKBICXXX"  # If known

    # <ChrgBr> => typically "SLEV"
    ET.SubElement(pmtInf, 'ChrgBr').text = "SLEV"

    # <CdtrSchmeId>
    cdtrSchmeId = ET.SubElement(pmtInf, 'CdtrSchmeId')
    csId = ET.SubElement(cdtrSchmeId, 'Id')
    prvtId = ET.SubElement(csId, 'PrvtId')
    othr = ET.SubElement(prvtId, 'Othr')
    ET.SubElement(othr, 'Id').text = rows[0].get('Creditor-ID', 'DE99ZZZ09999999999')
    schmeNm = ET.SubElement(othr, 'SchmeNm')
    ET.SubElement(schmeNm, 'Prtry').text = "SEPA"

    # 5) DrctDbtTxInf blocks (one per CSV row)
    total_count = 0
    total_amount = 0.0

    for row in rows:
        amount_str = row.get('Betrag', '0').replace(',', '.')
        try:
            amt_val = float(amount_str)
        except ValueError:
            amt_val = 0.0

        drctDbtTxInf = ET.SubElement(pmtInf, 'DrctDbtTxInf')

        # <PmtId><EndToEndId>
        pmtId = ET.SubElement(drctDbtTxInf, 'PmtId')
        ET.SubElement(pmtId, 'EndToEndId').text = f"E2E-{uuid.uuid4()}"

        # <InstdAmt Ccy="EUR">
        instdAmt = ET.SubElement(drctDbtTxInf, 'InstdAmt', {'Ccy': "EUR"})
        instdAmt.text = f"{amt_val:.2f}"

        # Payment Type Info again if needed at Tx level <PmtTpInf> (often optional)
        # <ChrgBr> => SLEV if needed

        # <DrctDbtTx> => <MndtRltdInf>
        drctDbtTx = ET.SubElement(drctDbtTxInf, 'DrctDbtTx')
        mndtRltdInf = ET.SubElement(drctDbtTx, 'MndtRltdInf')
        ET.SubElement(mndtRltdInf, 'MndtId').text = row.get('Mandatsreferenz', 'Mandat001')
        sign_date = row.get('Mandatsaustellungsdatum', '2025-01-01')
        ET.SubElement(mndtRltdInf, 'DtOfSgntr').text = convert_date(sign_date)
        # <AmdmntInd> => false by default
        ET.SubElement(mndtRltdInf, 'AmdmntInd').text = "false"

        # <DbtrAgt> => optional BIC for debtor's bank
        dbtrAgt = ET.SubElement(drctDbtTxInf, 'DbtrAgt')
        dbtrFinInstn = ET.SubElement(dbtrAgt, 'FinInstnId')
        # ET.SubElement(dbtrFinInstn, 'BIC').text = row.get('Zahler-BIC', '')

        # <Dbtr> => Name
        dbtr = ET.SubElement(drctDbtTxInf, 'Dbtr')
        ET.SubElement(dbtr, 'Nm').text = row.get('Zahlungspflichtiger-Name', '')

        # <DbtrAcct> => IBAN
        dbtrAcct = ET.SubElement(drctDbtTxInf, 'DbtrAcct')
        dbtrAcctId = ET.SubElement(dbtrAcct, 'Id')
        ET.SubElement(dbtrAcctId, 'IBAN').text = row.get('Zahlungspflichtiger-IBAN', '')

        # <RmtInf> => <Ustrd> (Verwendungszweck)
        rmtInf = ET.SubElement(drctDbtTxInf, 'RmtInf')
        ET.SubElement(rmtInf, 'Ustrd').text = row.get('Verwendungszweck', '')

        total_count += 1
        total_amount += amt_val

    # Now update the counters in <GrpHdr> and <PmtInf>
    nbOfTxs_elm.text = str(total_count)
    ctrlSum_elm.text = f"{total_amount:.2f}"

    pmtInfNbOfTxs.text = str(total_count)
    pmtInfCtrlSum.text = f"{total_amount:.2f}"

    # 6) Write out final XML
    tree = ET.ElementTree(root)
    tree.write(output_xml, encoding='utf-8', xml_declaration=True)

def generate_pain001(input_csv, output_xml):
    """
    Minimal example for generating pain.001 (Überweisung).
    Similar steps, but different structure/tags.
    """
    rows = read_csv(input_csv)
    # ... Implement similarly or reuse from earlier examples ...
    # For brevity, not fully expanded here. The main difference:
    # Document root = urn:iso:std:iso:20022:tech:xsd:pain.001.003.03
    # Payment info block uses <PmtMtd>TRF</PmtMtd>, etc.
    pass

def read_csv(path):
    """
    Generic CSV reading with semicolon/ comma/ tab detection or forced delimiter.
    Returns a list of dicts (each row).
    """
    with open(path, 'r', encoding='utf-8') as f:
        # Could attempt a dialect sniff, or specify delimiter if you know it:
        # import csv
        # dialect = csv.Sniffer().sniff(f.read(2048))
        # f.seek(0)
        # reader = csv.DictReader(f, dialect=dialect)
        # OR:
        reader = csv.DictReader(f, delimiter=';')  # adapt if needed
        rows = list(reader)
    return rows

def convert_date(date_str):
    """
    Convert e.g. "31.01.2025" -> "2025-01-31" if possible,
    else fallback to the raw string or a default.
    """
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
    return date_str  # fallback
