package com.mfagent.service;

import com.google.auth.oauth2.GoogleCredentials;
import com.google.cloud.firestore.*;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import com.google.firebase.cloud.FirestoreClient;

import java.io.FileInputStream;
import java.io.InputStream;
import java.net.URISyntaxException;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Inicializa y provee el cliente Firestore.
 * Equivalente a _get_data_app() en firestore_sync.py
 *
 * Usa DOS apps Firebase separadas (igual que Python):
 *   "data_sync"  → mf-agent-2b482-firebase-adminsdk-fbsvc-3eff30e990.json
 *   "lic_manager"→ mf-agent-2b482-firebase-adminsdk-fbsvc-937c5dc694.json
 */
public class FirebaseService {

    private static final String DATA_APP_NAME = "data_sync";
    private static final String LIC_APP_NAME  = "lic_manager";

    private static final String DATA_CRED = "mf-agent-2b482-firebase-adminsdk-fbsvc-3eff30e990.json";
    private static final String LIC_CRED  = "mf-agent-2b482-firebase-adminsdk-fbsvc-937c5dc694.json";
    private static final String STORAGE_BUCKET = "mf-agent-2b482.appspot.com";

    private static FirebaseApp dataApp;
    private static FirebaseApp licApp;

    public static synchronized FirebaseApp getDataApp() {
        if (dataApp != null) return dataApp;
        dataApp = initApp(DATA_APP_NAME, DATA_CRED, STORAGE_BUCKET);
        return dataApp;
    }

    public static synchronized FirebaseApp getLicApp() {
        if (licApp != null) return licApp;
        licApp = initApp(LIC_APP_NAME, LIC_CRED, null);
        return licApp;
    }

    public static Firestore getDataDb() {
        return FirestoreClient.getFirestore(getDataApp());
    }

    public static Firestore getLicDb() {
        return FirestoreClient.getFirestore(getLicApp());
    }

    private static FirebaseApp initApp(String name, String credFile, String bucket) {
        try {
            return FirebaseApp.getInstance(name);
        } catch (IllegalStateException ignored) {}

        try {
            // Buscar credencial relativa al JAR/exe primero, luego al working dir
            Path credPath = resolveCredPath(credFile);
            InputStream cred = new FileInputStream(credPath.toFile());

            FirebaseOptions.Builder builder = FirebaseOptions.builder()
                    .setCredentials(GoogleCredentials.fromStream(cred));
            if (bucket != null) builder.setStorageBucket(bucket);

            return FirebaseApp.initializeApp(builder.build(), name);
        } catch (Exception e) {
            throw new RuntimeException("[Firebase] Error inicializando '" + name + "': " + e.getMessage(), e);
        }
    }

    private static Path resolveCredPath(String credFile) {
        // 1. Relativo al directorio del JAR/exe
        try {
            Path jarDir = Path.of(
                    FirebaseService.class.getProtectionDomain()
                            .getCodeSource().getLocation().toURI()).getParent();
            Path candidate = jarDir.resolve(credFile);
            if (candidate.toFile().exists()) return candidate;
            // jpackage pone el JAR en app/, subir un nivel
            candidate = jarDir.getParent().resolve(credFile);
            if (candidate.toFile().exists()) return candidate;
        } catch (Exception ignored) {}
        // 2. Working directory
        return Paths.get(credFile);
    }
}
