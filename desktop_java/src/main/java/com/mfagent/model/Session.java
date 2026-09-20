package com.mfagent.model;

/**
 * Sesión activa del usuario (equivalente al session dict de Python).
 */
public class Session {
    private final String username;
    private final String role;        // "admin" | "vendedor"
    private final String profileId;
    private final String profileName;
    private final String key;

    public Session(String username, String role, String profileId, String profileName, String key) {
        this.username = username;
        this.role = role;
        this.profileId = profileId;
        this.profileName = profileName;
        this.key = key;
    }

    public String getUsername()     { return username; }
    public String getRole()         { return role; }
    public String getProfileId()    { return profileId; }
    public String getProfileName()  { return profileName; }
    public String getKey()          { return key; }

    public boolean isAdmin() {
        return "admin".equals(role);
    }
}
