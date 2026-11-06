package ec.utpl.libros;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

import io.helidon.http.Status;
import io.helidon.metrics.api.Counter;
import io.helidon.metrics.api.MeterRegistry;
import io.helidon.metrics.api.MetricsFactory;
import io.helidon.service.registry.Services;
import io.helidon.webserver.http.HttpRules;
import io.helidon.webserver.http.HttpService;
import io.helidon.webserver.http.ServerRequest;
import io.helidon.webserver.http.ServerResponse;

/**
 * API REST del catálogo de libros.
 *
 * GET  /libros        lista todos
 * GET  /libros/{id}   un libro (404 si no existe)
 * POST /libros        crea uno (JSON en el cuerpo)
 */
public class LibrosService implements HttpService {

    // "Base de datos" en memoria: cada microservicio es dueño de sus propios datos
    private final Map<Integer, Libro> libros = new ConcurrentHashMap<>();
    private final AtomicInteger secuencia = new AtomicInteger(5);

    // Métrica de negocio propia: aparece en /observe/metrics como libros_consultados_total
    // Helidon 27: el registro global se obtiene del ServiceRegistry
    private final Counter consultados = Services.get(MeterRegistry.class)
            .getOrCreate(MetricsFactory.getInstance().counterBuilder("libros_consultados")
                                 .description("Veces que se consultó un libro por id"));

    LibrosService() {
        guardar(new Libro(1, "Huasipungo", "Jorge Icaza", 1934, "Novela indigenista"));
        guardar(new Libro(2, "Cien años de soledad", "Gabriel García Márquez", 1967, "Realismo mágico"));
        guardar(new Libro(3, "Pedro Páramo", "Juan Rulfo", 1955, "Novela"));
        guardar(new Libro(4, "A la Costa", "Luis A. Martínez", 1904, "Novela realista"));
    }

    @Override
    public void routing(HttpRules rules) {
        rules.get("/", this::listar)
             .get("/{id}", this::obtener)
             .post("/", this::crear);
    }

    private void listar(ServerRequest req, ServerResponse res) {
        List<Libro> todos = libros.values().stream()
                .sorted((a, b) -> Integer.compare(a.id(), b.id()))
                .toList();
        res.header("X-Service", "libros-service");
        res.send(todos);
    }

    private void obtener(ServerRequest req, ServerResponse res) {
        res.header("X-Service", "libros-service");
        int id;
        try {
            id = Integer.parseInt(req.path().pathParameters().get("id"));
        } catch (NumberFormatException e) {
            res.status(Status.BAD_REQUEST_400).send(Map.of("error", "El id debe ser numérico"));
            return;
        }
        Libro libro = libros.get(id);
        if (libro == null) {
            res.status(Status.NOT_FOUND_404).send(Map.of("error", "Libro " + id + " no existe"));
            return;
        }
        consultados.increment();
        res.send(libro);
    }

    private void crear(ServerRequest req, ServerResponse res) {
        Libro entrada = req.content().as(Libro.class);
        if (entrada.titulo() == null || entrada.titulo().isBlank()) {
            res.status(Status.BAD_REQUEST_400).send(Map.of("error", "El título es obligatorio"));
            return;
        }
        Libro nuevo = new Libro(secuencia.getAndIncrement(), entrada.titulo(), entrada.autor(),
                                entrada.anio(), entrada.genero());
        guardar(nuevo);
        res.header("X-Service", "libros-service");
        res.status(Status.CREATED_201).send(nuevo);
    }

    private void guardar(Libro libro) {
        libros.put(libro.id(), libro);
    }
}
