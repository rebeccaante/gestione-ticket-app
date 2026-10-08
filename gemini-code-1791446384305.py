import os
import sqlite3
from datetime import datetime
import pandas as pd
import streamlit as st

# Configurazione Pagina
st.set_page_config(
    page_title="Gestione Ticket", layout="wide", page_icon="🎟️"
)

# Inizializzazione Database
DB_FILE = "gestione_ticket.db"
UPLOAD_DIR = "uploads_ricevute"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Tabella Richieste Dipendenti
    c.execute("""
        CREATE TABLE IF NOT EXISTS richieste (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            email TEXT,
            nome_cognome TEXT,
            anno INTEGER,
            mese TEXT,
            num_ticket INTEGER,
            file_path TEXT,
            stato TEXT DEFAULT 'In Lavorazione',
            ordine_id INTEGER
        )
    """)
    # Tabella Ordini / Fatture Ticket
    c.execute("""
        CREATE TABLE IF NOT EXISTS ordini_ticket (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_fattura TEXT,
            data_ordine TEXT,
            valore_unitario REAL,
            quantita_acquistata INTEGER,
            quantita_residua INTEGER
        )
    """)
    conn.commit()
    conn.close()


init_db()

# Sidebar Navigazione
st.sidebar.title("📌 Menu Navigazione")
ruolo = st.sidebar.radio(
    "Seleziona Ruolo",
    ["Dipendente - Nuova Richiesta", "HR - Gestione Richieste", "HR - Magazzino & Ordini"],
)

# -----------------------------------------------------------------------------
# 1. PORTALE DIPENDENTE
# -----------------------------------------------------------------------------
if ruolo == "Dipendente - Nuova Richiesta":
    st.title("🎟️ Modulo Richiesta Ticket")
    st.markdown("Compila i campi sottostanti per inviare la richiesta di ticket.")

    with st.form("form_richiesta", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input("Indirizzo Email *")
            nome_cognome = st.text_input("Cognome e Nome *")
            anno = st.selectbox("Anno *", [2025, 2026, 2027])
        with col2:
            mesi = [
                "Gennaio",
                "Febbraio",
                "Marzo",
                "Aprile",
                "Maggio",
                "Giugno",
                "Luglio",
                "Agosto",
                "Settembre",
                "Ottobre",
                "Novembre",
                "Dicembre",
            ]
            mese = st.selectbox("Mese *", mesi)
            num_ticket = st.number_input(
                "N° totale Ticket richiesti *", min_value=1, step=1
            )

        allegato = st.file_uploader(
            "Carica foto o PDF del modulo firmato *",
            type=["pdf", "png", "jpg", "jpeg"],
        )

        submitted = st.form_submit_button("Invia Richiesta")

        if submitted:
            if not email or not nome_cognome or not allegato:
                st.error("Per favore compila tutti i campi obbligatori e carica l'allegato.")
            else:
                # Salva file
                file_ext = allegato.name.split(".")[-1]
                file_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{nome_cognome.replace(' ', '_')}.{file_ext}"
                file_path = os.path.join(UPLOAD_DIR, file_filename)
                with open(file_path, "wb") as f:
                    f.write(allegato.getbuffer())

                # Salva su DB
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute(
                    """
                    INSERT INTO richieste (timestamp, email, nome_cognome, anno, mese, num_ticket, file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        email,
                        nome_cognome,
                        anno,
                        mese,
                        num_ticket,
                        file_path,
                    ),
                )
                conn.commit()
                conn.close()

                st.success("Richiesta inviata con successo!")

# -----------------------------------------------------------------------------
# 2. HR - GESTIONE RICHIESTE
# -----------------------------------------------------------------------------
elif ruolo == "HR - Gestione Richieste":
    st.title("📋 Gestione Richieste Ticket (Risorse Umane)")

    conn = sqlite3.connect(DB_FILE)
    df_req = pd.read_sql_query("SELECT * FROM richieste ORDER BY id DESC", conn)
    df_ordini = pd.read_sql_query(
        "SELECT * FROM ordini_ticket WHERE quantita_residua > 0", conn
    )

    if df_req.empty:
        st.info("Nessuna richiesta presente a sistema.")
    else:
        # Filtro per Stato
        stato_filter = st.radio(
            "Filtra per Stato",
            ["Tutti", "In Lavorazione (Da Smaltire)", "Pronti"],
            horizontal=True,
        )

        if stato_filter == "In Lavorazione (Da Smaltire)":
            df_filtered = df_req[df_req["stato"] == "In Lavorazione"]
        elif stato_filter == "Pronti":
            df_filtered = df_req[df_req["stato"] == "Pronti"]
        else:
            df_filtered = df_req

        st.subheader("Elenco Richieste")

        for idx, row in df_filtered.iterrows():
            # Evidenziazione visiva dello stato
            color = "#FFF3CD" if row["stato"] == "In Lavorazione" else "#D4EDDA"
            label_stato = (
                "⏳ IN LAVORAZIONE"
                if row["stato"] == "In Lavorazione"
                else "✅ PRONTO"
            )

            with st.container():
                st.markdown(
                    f"""
                <div style="background-color: {color}; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #ccc;">
                    <h4>{row['nome_cognome']} ({row['email']}) - <strong>{label_stato}</strong></h4>
                    <p><strong>Periodo:</strong> {row['mese']} {row['anno']} | <strong>N° Ticket:</strong> {row['num_ticket']} | <strong>Data Richiesta:</strong> {row['timestamp']}</p>
                </div>
                """,
                    unsafe_allow_html=f"{color}",
                )

                col_actions1, col_actions2, col_actions3 = st.columns([2, 3, 2])

                # Download File Firmato
                with col_actions1:
                    if os.path.exists(row["file_path"]):
                        with open(row["file_path"], "rb") as f:
                            st.download_button(
                                label="📄 Scarica Modulo Firmato",
                                data=f,
                                file_name=os.path.basename(row["file_path"]),
                                key=f"dl_{row['id']}",
                            )

                # Cambio Stato / Scalo da Inventario
                with col_actions2:
                    if row["stato"] == "In Lavorazione":
                        if not df_ordini.empty:
                            ordine_sel = st.selectbox(
                                "Seleziona Ordine/Fattura da cui scalare:",
                                df_ordini["numero_fattura"].tolist(),
                                key=f"ord_{row['id']}",
                            )
                        else:
                            st.warning("⚠️ Nessun ordine con ticket disponibili!")
                            ordine_sel = None

                with col_actions3:
                    if row["stato"] == "In Lavorazione":
                        if st.button("Marcia come PRONTI 🚀", key=f"btn_{row['id']}"):
                            if ordine_sel:
                                c = conn.cursor()
                                # Prendi ID ordine e quantita residua
                                ord_row = df_ordini[
                                    df_ordini["numero_fattura"] == ordine_sel
                                ].iloc[0]
                                ord_id = ord_row["id"]
                                residuo = ord_row["quantita_residua"]
                                req_num = row["num_ticket"]

                                if residuo >= req_num:
                                    # Scalo ticket
                                    c.execute(
                                        "UPDATE ordini_ticket SET quantita_residua = quantita_residua - ? WHERE id = ?",
                                        (req_num, ord_id),
                                    )
                                    # Aggiorno richiesta
                                    c.execute(
                                        "UPDATE richieste SET stato = 'Pronti', ordine_id = ? WHERE id = ?",
                                        (ord_id, row["id"]),
                                    )
                                    conn.commit()
                                    st.success(
                                        f"Richiesta #{row['id']} contrassegnata come PRONTA e scaricata dall'ordine {ordine_sel}!"
                                    )
                                    st.rerun()
                                else:
                                    st.error(
                                        f"Ticket insufficienti nell'ordine {ordine_sel}! Disponibili: {residuo}, Richiesti: {req_num}"
                                    )

    conn.close()

# -----------------------------------------------------------------------------
# 3. HR - MAGAZZINO & ORDINI (INVENTARIO TICKET)
# -----------------------------------------------------------------------------
elif ruolo == "HR - Magazzino & Ordini":
    st.title("📦 Inventario e Ordini Fatture Ticket")

    # Inserimento Nuovo Ordine Acquistato
    with st.expander("➕ Registra Nuovo Ordine / Acquisto Ticket"):
        with st.form("form_nuovo_ordine"):
            c1, c2 = st.columns(2)
            with c1:
                num_fattura = st.text_input("Numero Fattura / Ordine *")
                valore_unitario = st.number_input(
                    "Valore Singolo Ticket (€) *", value=7.00, step=0.50
                )
            with c2:
                data_ord = st.date_input("Data Ordine *")
                qta_acquistata = st.number_input(
                    "Quantità Ticket Acquistati *", min_value=1, step=10
                )

            submit_ord = st.form_submit_button("Salva Ordine")
            if submit_ord:
                if not num_fattura or qta_acquistata <= 0:
                    st.error("Inserire tutti i dati dell'ordine.")
                else:
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute(
                        """
                        INSERT INTO ordini_ticket (numero_fattura, data_ordine, valore_unitario, quantita_acquistata, quantita_residua)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (
                            num_fattura,
                            str(data_ord),
                            valore_unitario,
                            qta_acquistata,
                            qta_acquistata,
                        ),
                    )
                    conn.commit()
                    conn.close()
                    st.success("Nuovo ordine salvato in magazzino!")
                    st.rerun()

    # Tabella Riepilogativa Giacenze
    st.subheader("📊 Stato Giacenze Ordini")
    conn = sqlite3.connect(DB_FILE)
    df_magazzino = pd.read_sql_query(
        "SELECT id, numero_fattura AS 'N° Fattura', data_ordine AS 'Data', valore_unitario AS 'Valore (€)', quantita_acquistata AS 'Tot. Acquistati', quantita_residua AS 'Rimanenti' FROM ordini_ticket ORDER BY id DESC",
        conn,
    )

    if not df_magazzino.empty:
        # Calcolo Valore Residuo Totale
        df_magazzino["Valore Residuo Totale (€)"] = (
            df_magazzino["Rimanenti"] * df_magazzino["Valore (€)"]
        )

        st.dataframe(df_magazzino, use_container_width=True)

        tot_rimanenti = df_magazzino["Rimanenti"].sum()
        tot_valore = df_magazzino["Valore Residuo Totale (€)"].sum()

        m1, m2 = st.columns(2)
        m1.metric("Totale Ticket Rimanenti in Magazzino", f"{tot_rimanenti} ticket")
        m2.metric("Valore Totale Giacenza", f"€ {tot_valore:.2f}")
    else:
        st.info("Nessun ordine registrato finora.")

    conn.close()