from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import sqlite3
import os
from datetime import datetime
from database import create_database



app = Flask(__name__)
app.secret_key = "une_cle_secrete_tres_difficile"
global_df = None

USERS = {
    "admin": {
        "password": "admin123",
        "role": "admin"
    },
    "analyste": {
        "password": "analyste123",
        "role": "analyste"
    },
    "manager": {
        "password": "manager123",
        "role": "manager"
    }
}
def normaliser_colonnes(df):
    """
    Renomme automatiquement les colonnes du fichier importé
    vers des noms standards utilisés dans toute l'application.
    Fonctionne quel que soit le fichier Excel importé.
    """
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # Dictionnaire : nom standard → mots-clés possibles dans le fichier
    mapping = {
        "montant"     : ["montant", "amount", "total", "valeur", "value", "prix", "price"],
        "id_marchand" : ["marchand", "merchant", "commercant", "vendeur", "seller", "id_marc"],
        "fraude"      : ["fraude", "fraud", "fraude_detectee", "is_fraud", "fraudulent"],
        "statut"      : ["statut", "status", "etat", "state"],
        "date"        : ["date", "datetime", "date_transaction", "date_achat", "transaction_date"],
        "id_transaction": ["id_transaction", "transaction_id", "id", "reference", "ref"],
        "type"        : ["type", "type_transaction", "categorie", "category"],
        "revenue": ["revenue", "revenu", "profit", "gain", "benefice", "benefit"]
    }

    renommage = {}
    for nom_standard, mots_cles in mapping.items():
        for col in df.columns:
            if any(mot in col for mot in mots_cles):
                if nom_standard not in df.columns:  # évite d'écraser une colonne déjà bien nommée
                    renommage[col] = nom_standard
                    break

    df = df.rename(columns=renommage)

    print("Colonnes après normalisation :", df.columns.tolist())
    return df

@app.route("/", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if username in USERS:

            if password == USERS[username]["password"]:

                session["logged_in"] = True
                session["username"] = username
                session["role"] = USERS[username]["role"]

                return redirect(url_for("home"))

        error = "Identifiants incorrects"

    return render_template("login.html", error=error)


@app.route("/home")
def home():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    return render_template("home.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/import", methods=["GET", "POST"])
def import_data():

    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return "Accès refusé"

    global global_df

    data = None
    file_name = None
    rows = 0
    cols = 0

    if request.method == "POST":
        file = request.files["file"]
        if file:
            file_name = file.filename
            upload_path = os.path.join("uploads", file.filename)
            file.save(upload_path)

            if file.filename.endswith(".xlsx"):
               df = pd.read_excel(upload_path)

            elif file.filename.endswith(".csv"):
                df = pd.read_csv(upload_path)

            df.columns = (
                df.columns
                  .str.strip()
                  .str.lower()
                  .str.replace(" ", "_")
            )

            for col in ["montant", "frais", "commission", "revenue"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            # ── Normalisation automatique des colonnes ──
            # ── Normalisation automatique des colonnes ──
            global_df = normaliser_colonnes(df)

# ===============================
# Sauvegarde des données dans SQLite
# ===============================
            conn = sqlite3.connect("monitoring.db")

            global_df.to_sql(
              "transactions",
              conn,
              if_exists="replace",
              index=False
       )

        conn.close()

        print("Les données ont été enregistrées dans SQLite.")

        rows = global_df.shape[0]
        cols = global_df.shape[1]
            # Conversion automatique des colonnes numériques
        for col in ["montant", "revenue", "fraude"]:

            if col in global_df.columns:

                global_df[col] = pd.to_numeric(
                    global_df[col],
                    errors="coerce"
        )

            rows = global_df.shape[0]
            cols = global_df.shape[1]
            data = global_df.head(10).to_html(
                classes="table table-striped",
                index=False
            )

    return render_template(
        "import.html",
        data=data,
        file_name=file_name,
        rows=rows,
        cols=cols
    )    
     

@app.route("/quality")
def quality():

    global global_df

    if global_df is None:
        return "Aucune donnée importée. Veuillez d'abord importer un fichier."

    total_rows = len(global_df)

    missing_values = global_df.isnull().sum().sum()

    duplicates = global_df.duplicated().sum()

    negative_amounts = 0

    if "montant" in global_df.columns:

     global_df["montant"] = pd.to_numeric(
        global_df["montant"],
        errors="coerce"
    )

    negative_amounts = (
        global_df["montant"] < 0
    ).sum()

    valid_rows = total_rows - duplicates

    return render_template(
        "quality.html",
        total_rows=total_rows,
        missing_values=missing_values,
        duplicates=duplicates,
        negative_amounts=negative_amounts,
        valid_rows=valid_rows
    )

@app.route("/clean", methods=["GET", "POST"])
def clean():

    global global_df

    if global_df is None:
        return "Aucune donnée importée."

    message = None

    if request.method == "POST":

        removed_rows = 0

        if request.form.get("remove_duplicates"):

            before = len(global_df)

            global_df = global_df.drop_duplicates()

            after = len(global_df)

            removed_rows += before - after

        if request.form.get("remove_missing"):

            before = len(global_df)

            global_df = global_df.dropna()

            after = len(global_df)

            removed_rows += before - after

        if request.form.get("remove_negative"):

            if "montant" in global_df.columns:

                before = len(global_df)

                global_df["montant"] = pd.to_numeric(
                global_df["montant"],
                errors="coerce"
)
                global_df = global_df[global_df["montant"] >= 0]
                after = len(global_df)

                removed_rows += before - after

        message = f"Nettoyage terminé : {removed_rows} ligne(s) supprimée(s)."

    return render_template(
        "clean.html",
        message=message,
        total_rows=len(global_df)
    )
@app.route("/view-clean")
def view_clean_data():

    global global_df

    if global_df is None:
        return "Aucune donnée disponible."

    table = global_df.to_html(
        classes="table table-striped table-hover",
        index=False
    )

    return render_template(
        "view_clean.html",
        table=table,
        total_rows=len(global_df)
    )

@app.route("/export-clean")
def export_clean():

    global global_df

    if global_df is None:
        return "Aucune donnée à exporter."

    filename = f"cleaned_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    output_file = os.path.join(
        "uploads",
        filename
   )

    global_df.to_excel(
        output_file,
        index=False
   )

    return f"Fichier exporté avec succès : {filename}"

@app.route("/kpi")
def kpi():

    global global_df

    if global_df is None:
        return "Aucune donnée importée."

    global_df = normaliser_colonnes(global_df)

    total_transactions = len(global_df)

    total_montant = 0
    total_revenue = 0
    total_merchants = 0
    fraud_rate = 0

    # Montant
    if "montant" in global_df.columns:

        global_df["montant"] = pd.to_numeric(
            global_df["montant"],
            errors="coerce"
        )

        total_montant = global_df["montant"].sum()

    # Revenue
    if "revenue" in global_df.columns:

        global_df["revenue"] = pd.to_numeric(
            global_df["revenue"],
            errors="coerce"
        )

        total_revenue = global_df["revenue"].sum()

    else:

        total_revenue = total_montant

    # Nombre de marchands
    if "id_marchand" in global_df.columns:

        total_merchants = global_df["id_marchand"].nunique()

    # Taux de fraude
    if "fraude" in global_df.columns:

        global_df["fraude"] = pd.to_numeric(
            global_df["fraude"],
            errors="coerce"
        ).fillna(0)

        fraud_rate = (
            global_df["fraude"].sum()
            / total_transactions
        ) * 100

    return render_template(
        "kpi.html",
        total_transactions=total_transactions,
        total_montant=round(total_montant, 2),
        total_revenue=round(total_revenue, 2),
        total_merchants=total_merchants,
        fraud_rate=round(fraud_rate, 2)
    )


if __name__ == "__main__":
    create_database()
    app.run(debug=True)

