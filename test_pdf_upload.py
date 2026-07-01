import sys
sys.stdout.reconfigure(encoding='utf-8')

try:
    import firebase_admin
    from firebase_admin import credentials, firestore, storage
    from pathlib import Path
    import tempfile, os

    CRED_FILE      = "mf-agent-2b482-firebase-adminsdk-fbsvc-3eff30e990.json"
    STORAGE_BUCKET = "mf-agent-2b482.firebasestorage.app"

    cred_path = Path(CRED_FILE)
    print(f"Credencial: {cred_path.exists()}")

    app_name = "test_pdf"
    if app_name not in [a.name for a in firebase_admin._apps.values()]:
        app = firebase_admin.initialize_app(
            credentials.Certificate(str(cred_path)),
            name=app_name,
            options={"storageBucket": STORAGE_BUCKET}
        )
    else:
        app = firebase_admin.get_app(app_name)

    # Crear PDF de prueba
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(b"%PDF-1.4 test")
    tmp.close()
    print(f"PDF temporal: {tmp.name}")

    # Subir a Storage
    bucket = storage.bucket(app=app)
    print(f"Bucket: {bucket.name}")
    blob = bucket.blob("pdf/TEST-000001.pdf")
    blob.upload_from_filename(tmp.name, content_type="application/pdf")
    blob.make_public()
    url = blob.public_url
    print(f"URL publica: {url}")

    # Guardar en coleccion pdf
    db = firestore.client(app=app)
    db.collection("pdf").document("TEST-000001").set({
        "invoice_id": "TEST-000001",
        "profile_id": "test",
        "pdf_url": url,
        "filename": "TEST-000001.pdf",
    })
    print("Documento guardado en coleccion pdf")

    # Verificar
    doc = db.collection("pdf").document("TEST-000001").get()
    print(f"Verificacion: {doc.to_dict()}")

    os.unlink(tmp.name)
    print("EXITO")

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
