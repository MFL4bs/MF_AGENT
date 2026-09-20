package com.mfagent.service;

import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Rutas de datos por perfil.
 * Equivalente a agent/profiles.py → get_profile_data_dir()
 *
 * Estructura: data/<profile_id>/inventory.json
 *                               sales.json
 *                               categories.json
 *                               manuales/
 *                               images/
 */
public class ProfilePaths {

    /** Directorio raíz del proyecto (donde está el .jar o el pom.xml) */
    private static final Path ROOT = Paths.get(
            System.getProperty("mfagent.root",
                    System.getProperty("user.dir"))
    );

    public static Path dataDir(String profileId) {
        return ROOT.resolve("data").resolve(profileId);
    }

    public static Path profilesFile() {
        return ROOT.resolve("data").resolve("profiles.json");
    }

    public static Path envFile() {
        return ROOT.resolve(".env");
    }

    public static Path licenseFile() {
        return ROOT.resolve(".license");
    }
}
