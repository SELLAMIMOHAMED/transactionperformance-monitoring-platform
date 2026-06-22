from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = "une_cle_secrete_tres_difficile"
global_df = None

USERNAME = "user"
PASSWORD = "user1234"

@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    session["logged_in"] = True

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == USERNAME and password == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("home"))
        else:
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
                
            global_df = df

            rows = df.shape[0]
            cols = df.shape[1]

            data = df.head(10).to_html(
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

    if "amount" in global_df.columns:
        negative_amounts = (global_df["amount"] < 0).sum()

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

            if "amount" in global_df.columns:

                before = len(global_df)

                global_df = global_df[global_df["amount"] >= 0]

                after = len(global_df)

                removed_rows += before - after

        message = f"Nettoyage terminé : {removed_rows} ligne(s) supprimée(s)."

    return render_template(
        "clean.html",
        message=message,
        total_rows=len(global_df)
    )

@app.route("/export-clean")
def export_clean():

    global global_df

    if global_df is None:
        return "Aucune donnée à exporter."

    output_file = "cleaned_transactions.xlsx"

    global_df.to_excel(
        output_file,
        index=False
    )

    return f"Fichier exporté avec succès : {output_file}"


if __name__ == "__main__":
    app.run(debug=True)

