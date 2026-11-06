package ec.utpl.libros;

import io.helidon.config.Config;
import io.helidon.logging.common.LogConfig;
import io.helidon.service.registry.Services;
import io.helidon.webserver.WebServer;
import io.helidon.webserver.http.HttpRouting;

/**
 * Punto de entrada del microservicio de libros.
 * Un microservicio Helidon es una aplicación Java normal con un main():
 * no hay servidor de aplicaciones ni WAR, solo un JAR que se ejecuta.
 */
public final class Main {

    private Main() {
    }

    public static void main(String[] args) {
        LogConfig.configureRuntime();

        // Lee application.yaml; las variables de entorno tienen prioridad
        // (p. ej. SERVER_PORT=9000 sobrescribe server.port)
        Config config = Config.create();
        // Helidon 27: la config global se registra en el ServiceRegistry
        Services.set(Config.class, config);

        WebServer server = WebServer.builder()
                .config(config.get("server"))
                .routing(Main::routing)
                .build()
                .start();

        System.out.println("libros-service listo en http://localhost:" + server.port() + "/libros");
    }

    /** Tabla de rutas: qué URL atiende quién. */
    static void routing(HttpRouting.Builder routing) {
        routing.register("/libros", new LibrosService())
               .get("/", (req, res) -> res.send("libros-service (Java + Helidon). Prueba /libros"));
    }
}
