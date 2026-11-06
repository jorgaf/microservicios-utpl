package ec.utpl.libros;

/**
 * Modelo de datos. Un record de Java es inmutable y JSON-B lo convierte
 * a/desde JSON automáticamente.
 */
public record Libro(int id, String titulo, String autor, int anio, String genero) {
}
