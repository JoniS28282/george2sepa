# sepa_converter.py
import csv
import xml.etree.ElementTree as ET
import datetime
import uuid

def generate_pain008(input_csv, output_xml, sequence_type="RCUR", company_name="My Company", batch_booking=False):
    """
    Generate a pain.008.003.02 XML (Lastschrift) from 'input_csv' -> 'output_xml'.
    sequence_type can be FRST, RCUR, OOFF, FNAL, etc.
    company_name is used in <InitgPty> and <Cdtr><Nm>.
    If batch_booking=True, we'll add <BtchBookg>true</BtchBookg> in <GrpHdr>.
    """
    rows = read_csv(input_csv)
    if not rows:
        raise ValueError("CSV contains no data")

    # 1) Create root <Document> with namespaces
    root = ET.Element('Document', {
        'xmlns': "urn:iso:std:iso:20022:tech:xsd:pain.008.003.02",
        'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance",
        'xsi:schemaLocation': "urn:iso:std:iso:20022:tech:xsd:pain.008.003.02 pain.008.003.02.xsd"
    })
    cstmrDrctDbtInitn = ET.SubElement(root, 'CstmrDrctDbtInitn')

    # 2) <GrpHdr> group header
    grpHdr = ET.SubElement(cstmrDrctDbtInitn, 'GrpHdr')
    ET.SubElement(grpHdr, 'MsgId').text = f"MSG-{uuid.uuid4()}"
    ET.SubElement(grpHdr, 'CreDtTm').text = datetime.datetime.now().isoformat()
    nbOfTxs_elm = ET.SubElement(grpHdr, 'NbOfTxs')
    ctrlSum_elm = ET.SubElement(grpHdr, 'CtrlSum')
    # Grouping
    ET.SubElement(grpHdr, 'Grpg').text = "GRPD"

    # Initiating Party
    initgPty = ET.SubElement(grpHdr, 'InitgPty')
    ET.SubElement(initgPty, 'Nm').text = company_name

    # Optional batch booking
    # Some banks allow <BtchBookg> in <GrpHdr>, others expect it in <PmtInf>
    if batch_booking:
        ET.SubElement(grpHdr, 'BtchBookg').text = "true"
    # If you prefer it at <PmtInf> level, place it later.

    # 3) <PmtInf> payment info block
    pmtInf = ET.SubElement(cstmrDrctDbtInitn, 'PmtInf')
    ET.SubElement(pmtInf, 'PmtInfId').text = f"PMT-{uuid.uuid4()}"
    ET.SubElement(pmtInf, 'PmtMtd').text = "DD"

    # Payment Info counters
    pmtInfNbOfTxs = ET.SubElement(pmtInf, 'NbOfTxs')
    pmtInfCtrlSum = ET.SubElement(pmtInf, 'CtrlSum')

    # <PmtTpInf> => <SvcLvl><Cd>SEPA</Cd>, <LclInstrm><Cd>CORE/B2B</Cd>, <SeqTp>...</SeqTp>
    pmtTpInf = ET.SubElement(pmtInf, 'PmtTpInf')
    svcLvl = ET.SubElement(pmtTpInf, 'SvcLvl')
    ET.SubElement(svcLvl, 'Cd').text = "SEPA"

    lclInstrm = ET.SubElement(pmtTpInf, 'LclInstrm')
    ET.SubElement(lclInstrm, 'Cd').text = "CORE"  # or row-based if you track B2B vs CORE

    ET.SubElement(pmtTpInf, 'SeqTp').text = sequence_type

    # <ReqdColltnDt>
    first_due_date = rows[0].get('Faelligkeitsdatum', '2025-01-01')
    ET.SubElement(pmtInf, 'ReqdColltnDt').text = convert_date(first_due_date)

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
    # If you have a BIC, e.g. rows[0]['BIC'] or something: ET.SubElement(finInstnId, 'BIC').text = "ABCDEFXXX"

    # <ChrgBr>SLEV</ChrgBr>
    ET.SubElement(pmtInf, 'ChrgBr').text = "SLEV"

    # <CdtrSchmeId> => from CSV "Creditor-ID", or a default
    cdtrSchmeId = ET.SubElement(pmtInf, 'CdtrSchmeId')
    csId = ET.SubElement(cdtrSchmeId, 'Id')
    prvtId = ET.SubElement(csId, 'PrvtId')
    othr = ET.SubElement(prvtId, 'Othr')
    ET.SubElement(othr, 'Id').text = rows[0].get('Creditor-ID', 'DE99ZZZ09999999999')
    schmeNm = ET.SubElement(othr, 'SchmeNm')
    ET.SubElement(schmeNm, 'Prtry').text = "SEPA"

    # Optional <BtchBookg> at PaymentInfo level
    # if batch_booking:
    #     ET.SubElement(pmtInf, 'BtchBookg').text = "true"

    total_count = 0
    total_amount = 0.0

    # 4) Build each transaction <DrctDbtTxInf>
    for row in rows:
        amount_str = row.get('Betrag', '0').replace(',', '.')
        try:
            amt_val = float(amount_str)
        except:
            amt_val = 0.0

        drctDbtTxInf = ET.SubElement(pmtInf, 'DrctDbtTxInf')

        # Payment Identification
        pmtId = ET.SubElement(drctDbtTxInf, 'PmtId')
        ET.SubElement(pmtId, 'EndToEndId').text = f"E2E-{uuid.uuid4()}"

        # Instructed Amount
        instdAmt = ET.SubElement(drctDbtTxInf, 'InstdAmt', {'Ccy': 'EUR'})
        instdAmt.text = f"{amt_val:.2f}"

        # <DrctDbtTx> => <MndtRltdInf>
        drctDbtTx = ET.SubElement(drctDbtTxInf, 'DrctDbtTx')
        mndtRltdInf = ET.SubElement(drctDbtTx, 'MndtRltdInf')
        ET.SubElement(mndtRltdInf, 'MndtId').text = row.get('Mandatsreferenz', 'Mandat001')
        dt_of_sgntr = row.get('Mandatsaustellungsdatum', '2025-01-01')
        ET.SubElement(mndtRltdInf, 'DtOfSgntr').text = convert_date(dt_of_sgntr)
        ET.SubElement(mndtRltdInf, 'AmdmntInd').text = "false"

        # Debtor Agent
        dbtrAgt = ET.SubElement(drctDbtTxInf, 'DbtrAgt')
        dbtrFinInstnId = ET.SubElement(dbtrAgt, 'FinInstnId')
        # If you have Debtor BIC: ET.SubElement(dbtrFinInstnId, 'BIC').text = row.get('ZahlerBIC','')

        # Debtor
        dbtr = ET.SubElement(drctDbtTxInf, 'Dbtr')
        ET.SubElement(dbtr, 'Nm').text = row.get('Zahlungspflichtiger-Name', '')

        # Debtor Account
        dbtrAcct = ET.SubElement(drctDbtTxInf, 'DbtrAcct')
        dbtrAcctId = ET.SubElement(dbtrAcct, 'Id')
        ET.SubElement(dbtrAcctId, 'IBAN').text = row.get('Zahlungspflichtiger-IBAN', '')

        # Remittance Info
        rmtInf = ET.SubElement(drctDbtTxInf, 'RmtInf')
        ET.SubElement(rmtInf, 'Ustrd').text = row.get('Verwendungszweck', '')

        total_count += 1
        total_amount += amt_val

    # Update counters
    nbOfTxs_elm.text = str(total_count)
    ctrlSum_elm.text = f"{total_amount:.2f}"

    pmtInfNbOfTxs.text = str(total_count)
    pmtInfCtrlSum.text = f"{total_amount:.2f}"

    # 5) Write out
    tree = ET.ElementTree(root)
    tree.write(output_xml, encoding='utf-8', xml_declaration=True)


def generate_pain001(input_csv, output_xml, company_name="My Company", batch_booking=False):
    """
    Generate a pain.001.003.03 XML (Überweisung) with a single PaymentInfo
    containing all transactions (bundle).
    company_name => used in <InitgPty> and <Dbtr><Nm>.
    If batch_booking=True, we add <BtchBookg>true</BtchBookg>.
    """
    rows = read_csv(input_csv)
    if not rows:
        raise ValueError("CSV contains no data for Überweisung.")

    # 1) Create root <Document> with namespaces
    root = ET.Element('Document', {
        'xmlns': "urn:iso:std:iso:20022:tech:xsd:pain.001.003.03",
        'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance",
        'xsi:schemaLocation': "urn:iso:std:iso:20022:tech:xsd:pain.001.003.03 pain.001.003.03.xsd"
    })
    cstmrCdtTrfInitn = ET.SubElement(root, 'CstmrCdtTrfInitn')

    # 2) <GrpHdr>
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

    # 3) <PmtInf>
    pmtInf = ET.SubElement(cstmrCdtTrfInitn, 'PmtInf')
    ET.SubElement(pmtInf, 'PmtInfId').text = f"PMT-{uuid.uuid4()}"
    ET.SubElement(pmtInf, 'PmtMtd').text = "TRF"
    pmtInfNbOfTxs = ET.SubElement(pmtInf, 'NbOfTxs')
    pmtInfCtrlSum = ET.SubElement(pmtInf, 'CtrlSum')

    # Payment Type Info
    pmtTpInf = ET.SubElement(pmtInf, 'PmtTpInf')
    svcLvl = ET.SubElement(pmtTpInf, 'SvcLvl')
    ET.SubElement(svcLvl, 'Cd').text = "SEPA"

    # <ReqdExctnDt> => from first row or "today + 1"
    first_date = rows[0].get('Durchfuehrungsdatum', '2025-01-01')
    ET.SubElement(pmtInf, 'ReqdExctnDt').text = convert_date(first_date)

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
    # If you have a Debtor BIC in the CSV:
    bic_val = rows[0].get('Auftraggeber-BIC', '')
    if bic_val:
        ET.SubElement(finInstnId, 'BIC').text = bic_val

    # <ChrgBr>SLEV</ChrgBr>
    ET.SubElement(pmtInf, 'ChrgBr').text = "SLEV"

    # 4) Transactions <CdtTrfTxInf>
    total_count = 0
    total_amount = 0.0

    for row in rows:
        amount_str = row.get('Betrag', '0').replace(',', '.')
        try:
            amt_val = float(amount_str)
        except:
            amt_val = 0.0

        cdtTrfTxInf = ET.SubElement(pmtInf, 'CdtTrfTxInf')

        # <PmtId> => <EndToEndId>
        pmtId = ET.SubElement(cdtTrfTxInf, 'PmtId')
        # If no reference is available, use "NOTPROVIDED"
        ET.SubElement(pmtId, 'EndToEndId').text = f"E2E-{uuid.uuid4()}"

        # <Amt> => <InstdAmt Ccy="EUR">
        amt_elem = ET.SubElement(cdtTrfTxInf, 'Amt')
        instdAmt = ET.SubElement(amt_elem, 'InstdAmt', {'Ccy': 'EUR'})
        instdAmt.text = f"{amt_val:.2f}"

        # <CdtrAgt> => <FinInstnId> => <BIC>
        cdtrAgt = ET.SubElement(cdtTrfTxInf, 'CdtrAgt')
        cdtrFinInstn = ET.SubElement(cdtrAgt, 'FinInstnId')
        emp_bic = row.get('Empfaenger-BIC', '')
        if emp_bic:
            ET.SubElement(cdtrFinInstn, 'BIC').text = emp_bic

        # <Cdtr> => <Nm>
        cdtrTag = ET.SubElement(cdtTrfTxInf, 'Cdtr')
        ET.SubElement(cdtrTag, 'Nm').text = row.get('Empfaenger-Name', '')

        # <CdtrAcct> => <Id> => <IBAN>
        cdtrAcctTag = ET.SubElement(cdtTrfTxInf, 'CdtrAcct')
        cdtrAcctId = ET.SubElement(cdtrAcctTag, 'Id')
        ET.SubElement(cdtrAcctId, 'IBAN').text = row.get('Empfaenger-IBAN', '')

        # <RmtInf> => <Ustrd>
        rmtInf = ET.SubElement(cdtTrfTxInf, 'RmtInf')
        ET.SubElement(rmtInf, 'Ustrd').text = row.get('Verwendungszweck', '')

        total_count += 1
        total_amount += amt_val

    # 5) Update counters
    nbOfTxs_elm.text = str(total_count)
    ctrlSum_elm.text = f"{total_amount:.2f}"
    pmtInfNbOfTxs.text = str(total_count)
    pmtInfCtrlSum.text = f"{total_amount:.2f}"

    # 6) Write out
    tree = ET.ElementTree(root)
    tree.write(output_xml, encoding='utf-8', xml_declaration=True)


def read_csv(path):
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')  # Or sniff or adapt delimiter
        return list(reader)

def convert_date(date_str):
    """
    Convert e.g. '31.01.2025' => '2025-01-31'.
    If fails, just return something default or the original.
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
    return date_str
